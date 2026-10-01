"""
send_lunch_sms.py

Sends a "good afternoon" + food/healthy-eating message as a real SMS,
on exactly 2 random weekdays each week (Mon-Fri), picked automatically.

HOW THE "2 RANDOM DAYS A WEEK" PART WORKS:
This workflow runs every weekday at lunchtime, but the script itself
decides whether TODAY is actually one of this week's 2 chosen days.
The 2 days are picked using the current ISO week number as a random seed,
so every run during the same week computes the SAME 2 days without
needing to remember anything between runs — and a different 2 days get
picked automatically next week.

SETUP:
  Same SMSGATEWAY_LOGIN / SMSGATEWAY_PASSWORD / RECIPIENT_PHONE_NUMBER
  secrets as send_daily_goodmorning_sms.py. No extra setup needed if
  you're already running that one.

Optional env vars for testing:
  TEST_WEEKDAY=0-4   pretend today is this weekday (0=Mon ... 4=Fri)
  FORCE_SEND=1       ignore the "is today a chosen day" check and send anyway
  DRY_RUN=1          print instead of sending
"""

import os
import random
from datetime import datetime, timedelta, timezone

import requests
from requests.auth import HTTPBasicAuth

SMSGATEWAY_LOGIN = os.environ.get("SMSGATEWAY_LOGIN")
SMSGATEWAY_PASSWORD = os.environ.get("SMSGATEWAY_PASSWORD")
RECIPIENT_PHONE_NUMBER = os.environ.get("RECIPIENT_PHONE_NUMBER")

SMSGATEWAY_URL = "https://api.sms-gate.app/3rdparty/v1/messages"

TEST_WEEKDAY = os.environ.get("TEST_WEEKDAY", "").strip()
FORCE_SEND = os.environ.get("FORCE_SEND", "").strip() == "1"
DRY_RUN = os.environ.get("DRY_RUN", "").strip() == "1"

DAYS_PER_WEEK = 2  # how many random weekdays get a lunch message

# ---- Good afternoon greetings: mix of Taglish, English, Filipino ----
GREETINGS = [
    "good afternoon hon!",
    "magandang hapon mahal!",
    "good afternoon na mama!",
    "kumain ka na ba, love?",
    "good afternoon love, lunch time na!",
    "magandang hapon, mahal! kumain ka na?",
    "hey hon, good afternoon! lunch na ba?",
    "magandang tanghali, mama!",
]

# ---- Food / healthy eating / recipe-ish messages ----
LUNCH_MESSAGES = [
    "kumain ka ha, wag mong laktawan lunch mo.",
    "sana may gulay sa plato mo today, para balanced.",
    "try ko yung sinigang recipe mo ulit minsan, miss ko na yung asim.",
    "protina, gulay, kanin, tapos tubig - simple lang pero sapat na.",
    "wag puro rice, dagdagan mo gulay konti ha.",
    "sana masarap lunch mo today, kumain ka ng tama.",
    "tip: ubusin mo tubig mo bago ka kumain, nakakatulong sa digestion.",
    "kung may oras, mag-ensalada ka konti, pampasigla.",
    "miss ko magluto para sa'yo, soon ulit.",
    "wag mo kalimutan prutas mo later, apple or banana okay lang.",
    "kumain ka ng tama ha, wag puro kape lang.",
    "sana hindi ka nag-skip ng lunch, importante 'yon.",
    "light lang lunch mo baka maantok ka sa work, pero sapat ha.",
    "try mo chicken at gulay today, simple pero healthy.",
    "tip: mas mabuti grilled kaysa fried, pero paminsan-minsan okay lang din fried.",
    "sana may protina ka sa lunch mo, para hindi ka mabilis magutom.",
    "kumain ka ng masarap, deserve mo today.",
    "wag mo rin kalimutan mag-stretch bago bumalik sa work pagkatapos kumain.",
    "sana masaya lunch mo, kahit mag-isa ka lang kumain.",
    "miss ko kumain kasama ka, next time ulit.",
    # ---- Workout / movement reminders (lunchtime-friendly) ----
    "after lunch, try mong maglakad kahit 5-10 minutes lang, nakakatulong sa digestion at energy.",
    "kung may oras, konting stretch after kumain, pampagaan ng pakiramdam.",
    "tip: short walk after lunch beats a nap pagdating sa energy later sa hapon.",
    "sana may time ka mag-workout mamaya, kahit bahagya lang, proud na proud ako sa consistency mo.",
    "wag kalimutan pre-workout meal mo ha kung may gym ka later, something light pero may protina.",
    "miss ko yung dating lakad natin after lunch, sana ulitin natin minsan.",
    "lunchtime reminder: tubig muna bago kape, araw-araw ganyan at makakatulong talaga.",
    "sana magaan pakiramdam mo after kumain, try mong iwasan matulog agad para di bloated.",
    "proud ako sa'yo sa workout mo this week, ingat lang sa diet pati, parehas 'yan importante.",
]

# ---- Cheat day / reward messages. Sent rarely, not every lunch day. ----
CHEAT_DAY_MESSAGES = [
    "okay lang mag-cheat day minsan ha, deserve mo rin mag-enjoy sa kinakain mo.",
    "sige, bahala ka na sa lunch mo today, kumain ka ng gusto mo, ikaw bahala magdesisyon.",
    "reward mo sarili mo today, kumain ka ng paborito mo, wag kang maramdam guilty.",
    "hindi lahat ng araw kailangan strict, minsan okay lang mag-indulge, balance lang.",
    "you've been consistent lately, treat mo sarili mo ng masarap today, deserve mo.",
    "cheat meal time? go lang, kaya mo namang balansehin bukas.",
    "paminsan-minsan okay lang yung burger or pizza, wag ka masyadong mahigpit sa sarili mo.",
    "sige, free pass ka today sa diet, enjoy ka lang, bukas ulit tayo balik sa healthy.",
]


def today_in_manila():
    return datetime.now(timezone(timedelta(hours=8)))


def iso_week_seed(now):
    year, week, _ = now.isocalendar()
    return f"{year}-W{week}"


def this_weeks_chosen_days(now):
    """Deterministically pick which 2 weekdays (0=Mon..4=Fri) get a lunch
    message this week, based on the ISO week number. Same result every
    time it's computed during the same week; different next week."""
    rng = random.Random(iso_week_seed(now))
    return set(rng.sample(range(5), DAYS_PER_WEEK))


def humanize(text):
    """About 1-3% of the time, introduce a small natural-looking slip -
    either two adjacent letters swapped inside one word, or two adjacent
    words swapped - so it reads a bit more like a real person typing fast
    instead of a flawless script. Most of the time this does nothing."""
    TYPO_CHANCE = 0.02  # 2%, within the requested 1-3% range
    if random.random() >= TYPO_CHANCE:
        return text

    if random.random() < 0.5:
        # Swap two adjacent letters inside a random word of 4+ letters.
        words = text.split(" ")
        candidates = [i for i, w in enumerate(words) if len(w) >= 4]
        if candidates:
            i = random.choice(candidates)
            w = words[i]
            pos = random.randint(1, len(w) - 3)  # avoid first/last letter and punctuation edges
            w = w[:pos] + w[pos + 1] + w[pos] + w[pos + 2:]
            words[i] = w
            return " ".join(words)
    else:
        # Swap two adjacent words.
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

    now = today_in_manila()
    weekday = int(TEST_WEEKDAY) if TEST_WEEKDAY else now.weekday()
    chosen_days = this_weeks_chosen_days(now)

    print(f"This week's chosen lunch days (0=Mon..4=Fri): {sorted(chosen_days)}")
    print(f"Today is weekday {weekday}")

    if weekday > 4:
        print("Weekend, no lunch message script runs on weekends.")
        return

    if weekday not in chosen_days and not FORCE_SEND:
        print("Today is not one of this week's chosen lunch days. Skipping.")
        return

    numbers = [n.strip() for n in (RECIPIENT_PHONE_NUMBER or "").split(",") if n.strip()]
    if not numbers:
        print("No recipients configured.")
        return

    greeting = random.choice(GREETINGS)
    # Cheat day messages show up occasionally, not as the default.
    CHEAT_DAY_CHANCE = 0.15  # roughly 1 in 7 lunch messages
    if random.random() < CHEAT_DAY_CHANCE:
        print("Picked a cheat-day message today.")
        body = random.choice(CHEAT_DAY_MESSAGES)
    else:
        body = random.choice(LUNCH_MESSAGES)
    text = f"{greeting} {body}" if random.random() < 0.5 else f"{body} {greeting}"
    text = humanize(text)
    send(numbers, text)


if __name__ == "__main__":
    send_message()
