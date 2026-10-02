"""
send_goodnight_sms.py

Sends a "good night" message as a real SMS every day, sometime between
10:00 and 11:00 PM (Manila time). Same design as send_lunch_sms.py:
Taglish/English/Filipino greeting + a message, no-repeat memory shared
with the other scripts' sent_state.json, and a small (1-3%) humanizing
typo/word-swap once in a while.

SETUP:
  Same SMSGATEWAY_LOGIN / SMSGATEWAY_PASSWORD / RECIPIENT_PHONE_NUMBER
  secrets as the other scripts. No extra setup needed if you're already
  running those.

Optional env vars for testing:
  FORCE_SEND=1   (kept for consistency with the other scripts; this script
                  always sends when run, so this has no effect here)
  DRY_RUN=1      print instead of sending
"""

import json
import os
import random

import requests
from requests.auth import HTTPBasicAuth

SMSGATEWAY_LOGIN = os.environ.get("SMSGATEWAY_LOGIN")
SMSGATEWAY_PASSWORD = os.environ.get("SMSGATEWAY_PASSWORD")
RECIPIENT_PHONE_NUMBER = os.environ.get("RECIPIENT_PHONE_NUMBER")

SMSGATEWAY_URL = "https://api.sms-gate.app/3rdparty/v1/messages"

DRY_RUN = os.environ.get("DRY_RUN", "").strip() == "1"

# Same state file the other scripts use, so one file tracks every
# category's history (different keys, no overlap).
STATE_FILE = os.environ.get("STATE_FILE", "sent_state.json")

# ---- Good night greetings: mix of Taglish, English, Filipino ----
GREETINGS = [
    "good night hon!",
    "magandang gabi mahal!",
    "good night na mama!",
    "matulog ka na, love.",
    "good night love, rest ka na.",
    "magandang gabi, mahal! matulog ka na ha.",
    "hey hon, good night! sweet dreams.",
    "magandang gabi, mama!",
]

# ---- Good night / rest / love messages ----
NIGHT_MESSAGES = [
    "matulog ka na ha, mahal kita.",
    "ingat sa pagtulog, sana magandang panaginip ka.",
    "miss na miss kita, sana makita na kita sa panaginip.",
    "busy araw natin today, rest ka na ng maayos.",
    "wag ka na mag-phone ng matagal, para makatulog ka agad.",
    "proud ako sa'yo sa buong araw, ngayon tulog na.",
    "kahit malayo ka, ramdam mo sana yakap ko papuntang tulog ka.",
    "sana magaan pakiramdam mo bukas, magpahinga ka muna.",
    "araw-araw kitang iniisip bago ako matulog, ikaw rin siguro.",
    "goodnight na, kailangan mo ng rest para sa bukas.",
    "sana mapanaginipan mo ako, mahal kita.",
    "tulog ka na, maaga pa tayo bukas.",
    "ingat, matulog ka ng maayos ha, mahal kita.",
    "last message ko for today, goodnight mahal, ingat lagi.",
    "sana comfortable ka matulog tonight, mahal kita.",
    "miss na kita.",
    "proud ako sa'yo today, rest ka na ha.",
    "huminga ka lang, tapos na araw na 'to, tulog na.",
    "goodnight, see you sa panaginip.",
    "mahal kita, matulog ka na, lagi kang nasa isip ko.",
]

# ---- Chance of silently skipping a goodnight (feels human, not robotic) ----
MISS_CHANCE = 0.08  # roughly 1 in 12 nights



def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def pick_unused(key, pool, state):
    """Pick a random unused message for this key. Reset that pool once
    everything in it has been used."""
    used = set(state.get(key, []))
    available = [m for m in pool if m not in used]
    if not available:
        print(f"All '{key}' messages used. Resetting this category.")
        available = pool[:]
        used = set()
    choice = random.choice(available)
    used.add(choice)
    state[key] = list(used)
    return choice


def humanize(text):
    """About 1-3% of the time, introduce a small natural-looking slip -
    either two adjacent letters swapped inside one word, or two adjacent
    words swapped - so it reads a bit more like a real person typing fast
    instead of a flawless script. Most of the time this does nothing."""
    TYPO_CHANCE = 0.02  # 2%, within the requested 1-3% range
    if random.random() >= TYPO_CHANCE:
        return text

    if random.random() < 0.5:
        words = text.split(" ")
        candidates = [i for i, w in enumerate(words) if len(w) >= 4]
        if candidates:
            i = random.choice(candidates)
            w = words[i]
            pos = random.randint(1, len(w) - 3)
            w = w[:pos] + w[pos + 1] + w[pos] + w[pos + 2:]
            words[i] = w
            return " ".join(words)
    else:
        words = text.split(" ")
        if len(words) >= 3:
            i = random.randint(0, len(words) - 2)
            words[i], words[i + 1] = words[i + 1], words[i]
            return " ".join(words)

    return text


def send(numbers, text):
    if DRY_RUN:
        print(f"[dry run] would send to {numbers}: {text}")
        return
    response = requests.post(
        SMSGATEWAY_URL,
        json={"textMessage": {"text": text}, "phoneNumbers": numbers},
        auth=HTTPBasicAuth(SMSGATEWAY_LOGIN, SMSGATEWAY_PASSWORD),
    )
    response.raise_for_status()
    print(f"Sent to {numbers}: {text}")


def send_message():
    if not DRY_RUN and not all([SMSGATEWAY_LOGIN, SMSGATEWAY_PASSWORD, RECIPIENT_PHONE_NUMBER]):
        raise SystemExit(
            "Missing config. Set SMSGATEWAY_LOGIN, SMSGATEWAY_PASSWORD, and "
            "RECIPIENT_PHONE_NUMBER as environment variables."
        )

    numbers = [n.strip() for n in (RECIPIENT_PHONE_NUMBER or "").split(",") if n.strip()]
    if not numbers:
        print("No recipients configured.")
        return

    state = load_state()

    # Randomly skip tonight altogether, like a person who just forgot.
    # A separate morning script (send_goodnight_apology.py) checks for
    # this flag and sends a catch-up apology the next morning, timed to
    # not overlap with the regular good-morning message.
    if random.random() < MISS_CHANCE:
        print("Skipping tonight's goodnight message (simulated miss).")
        state["missed_pending"] = True
        save_state(state)
        return

    greeting = random.choice(GREETINGS)
    body = pick_unused("goodnight", NIGHT_MESSAGES, state)
    text = f"{greeting} {body}" if random.random() < 0.5 else f"{body} {greeting}"
    text = humanize(text)
    send(numbers, text)
    save_state(state)


if __name__ == "__main__":
    send_message()
