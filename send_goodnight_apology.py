"""
send_goodnight_apology.py

Runs every morning at 9:00-9:30 AM (Manila time) - deliberately a
different window from the 5:30-8:00 AM good-morning message and the
11:30 AM-1:00 PM lunch message, so it never overlaps either.

It checks whether last night's goodnight message was skipped (set by
send_goodnight_sms.py's random MISS_CHANCE). If so, it sends a short
"sorry, forgot to say goodnight" message and clears the flag. If nothing
was missed, it does nothing and sends no text at all - most mornings,
this script quietly does nothing.

SETUP:
  Same SMSGATEWAY_LOGIN / SMSGATEWAY_PASSWORD / RECIPIENT_PHONE_NUMBER
  secrets as the other scripts. No extra setup needed.

Optional env vars for testing:
  FORCE_PENDING=1   pretend last night was missed, even if it wasn't
  DRY_RUN=1         print instead of sending
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
FORCE_PENDING = os.environ.get("FORCE_PENDING", "").strip() == "1"

# Same state file every other script uses.
STATE_FILE = os.environ.get("STATE_FILE", "sent_state.json")

# ---- Apology for missing last night's goodnight. Framed as waking up
# early specifically to say sorry - no "good morning" greeting here, since
# this now runs well before the actual good-morning message. ----
APOLOGY_MESSAGES = [
    "gising na gising ako ngayon, guilty kasi ako, nakalimutan kong mag-goodnight kagabi. sorry, antok na antok ata ako kagabi. miss kita.",
    "ang aga ko nagising, sorry talaga, di ko na-send yung goodnight ko kagabi, nakatulog agad ako. mahal kita.",
    "bumangon ako maaga para lang sabihin sorry, di kita na-greet ng goodnight kagabi, busy lang masyado. ingat ka lagi.",
    "sorry, gising agad ako, naalala ko kasi nalimutan ko goodnight mo kagabi. nandito pa rin ako lagi, promise.",
    "aga ko gumising dahil hindi mapakali, sorry hon, di ko na-send yung goodnight kagabi, pagod na pagod ako eh. miss na miss kita.",
]


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
    state = load_state()
    pending = state.get("missed_pending", False) or FORCE_PENDING

    if not pending:
        print("Nothing to apologize for, last night's goodnight went out fine. Skipping.")
        return

    if not DRY_RUN and not all([SMSGATEWAY_LOGIN, SMSGATEWAY_PASSWORD, RECIPIENT_PHONE_NUMBER]):
        raise SystemExit(
            "Missing config. Set SMSGATEWAY_LOGIN, SMSGATEWAY_PASSWORD, and "
            "RECIPIENT_PHONE_NUMBER as environment variables."
        )

    numbers = [n.strip() for n in (RECIPIENT_PHONE_NUMBER or "").split(",") if n.strip()]
    if not numbers:
        print("No recipients configured.")
        return

    body = pick_unused("goodnight_apology", APOLOGY_MESSAGES, state)
    text = humanize(body)
    send(numbers, text)

    state["missed_pending"] = False
    save_state(state)


if __name__ == "__main__":
    send_message()
