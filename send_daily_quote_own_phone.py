"""
send_daily_goodmorning_sms.py

Sends one random good-morning message per day at 5:30 AM (Manila time) as a real
SMS from YOUR OWN phone number, using the "SMS Gateway for Android" app.

FEATURES:
  - No-repeat memory (state file remembers what's been sent)
  - Day-of-week themes (Mon=workout, Tue=work, Wed=kids, Thu=health,
    Fri=mental health, Sat=inspiring, Sun=love)
  - Short & sweet only (all messages under ~160 chars)
  - Husband voice ("hon", "mama", no name needed)

SETUP:
  1. Install "SMS Gateway for Android" from the Play Store.
  2. Enable Cloud Server mode and sign in / register for API login + password.
  3. pip install requests
  4. Set the environment variables below.
  5. Schedule at 5:30 AM Manila time (cron: 30 21 * * * UTC).
"""

import json
import os
import random
from datetime import datetime, timedelta, timezone

import requests
from requests.auth import HTTPBasicAuth

# ---- Config ----
SMSGATEWAY_LOGIN = os.environ.get("SMSGATEWAY_LOGIN")
SMSGATEWAY_PASSWORD = os.environ.get("SMSGATEWAY_PASSWORD")
RECIPIENT_PHONE_NUMBER = os.environ.get("RECIPIENT_PHONE_NUMBER")

SMSGATEWAY_URL = "https://api.sms-gate.app/3rdparty/v1/messages"

# ---- Birthdays (optional) ----
BIRTHDAYS = os.environ.get("BIRTHDAYS", "")
TEST_DATE = os.environ.get("TEST_DATE", "").strip()
DRY_RUN = os.environ.get("DRY_RUN", "").strip() == "1"

# ---- No-repeat memory ----
# Tracks which messages have been sent already per category. Stored as JSON.
# In GitHub Actions, commit this file back or use actions/cache so it persists.
STATE_FILE = os.environ.get("STATE_FILE", "sent_state.json")

BIRTHDAY_MESSAGES = [
    "happy birthday mama!! swerte ko sa'yo, mahal na mahal kita",
    "uy hon, happy birthday! enjoy your day ha, deserve mo lahat",
    "happy birthday hon! isa na namang taon na kasama kita, thank you",
    "mama, happy birthday! sana ma-spoil kita today",
    "happy birthday hon, ikaw pa rin pinakamaganda para sa akin",
]

# ============================================================
# DAY-OF-WEEK THEMES
# ============================================================
# Monday    = workout / jog / healthy eating
# Tuesday   = work check-in
# Wednesday = kids / missing them
# Thursday  = health tips & healthy quotes
# Friday    = mental health check-in
# Saturday  = inspiring quotes
# Sunday    = love / romantic

MESSAGES_WORKOUT = [
    "good morning hon! ingat sa jog mo ha, miss na miss kita",
    "magandang umaga hon! proud ako sa'yo palagi, takbo ka lang diyan",
    "good morning hon! inom ka ng tubig ha, ayaw kong ma-dehydrate ka",
    "magandang umaga hon! sipag mo, sobrang proud ako sa'yo",
    "good morning hon! sabi mo magiging consistent ka, and look at you now",
    "magandang umaga hon! ingat sa takbo mo, mahal kita",
    "good morning hon! sarap siguro almusal mo ngayon, miss kita",
    "magandang umaga hon! kahit malayo ako, ramdam ko sipag mo",
    "good morning hon! para sa'yo yang workout mo, proud ako",
    "magandang umaga hon! hydrate ka ha, mahal kita",
]

MESSAGES_WORK = [
    "good morning hon! kamusta work mo lately? miss kita",
    "magandang umaga hon! sana hindi masyadong mabigat trabaho mo today",
    "good morning hon! kung stressed ka sa work, huminga ka lang ha",
    "magandang umaga hon! proud ako sa lahat ng ginagawa mo sa work",
    "good morning hon! wag mo pilitin sarili mo sa work ha, mahal kita",
    "magandang umaga hon! sana okay lang work mo today, nandito lang ako",
    "good morning hon! kung pagod ka sa work, magpahinga ka ha",
    "magandang umaga hon! hindi mo kailangang gawin lahat today, isa-isa lang",
    "good morning hon! kamusta ka na ba talaga? miss kita",
    "magandang umaga hon! proud ako sa'yo, kahit hindi mo naririnig madalas",
]

MESSAGES_KIDS = [
    "good morning hon! miss mo na sila no? ako rin miss ko kayong lahat",
    "magandang umaga hon! nandiyan lang sila sa puso mo palagi",
    "good morning hon! tawagan mo sila mamaya ha, gagaan pakiramdam mo",
    "magandang umaga hon! ang mga bata swerte sa'yo, ikaw pinakamagandang mama",
    "good morning hon! palapit nang palapit tayo sa pagsasama ulit, kapit lang",
    "magandang umaga hon! mahal na mahal ka nila, alam mo 'yon",
    "good morning hon! sabihin mo sa kanila mahal sila ni daddy",
    "magandang umaga hon! ikaw puso ng pamilya natin, miss kita",
    "good morning hon! mahirap maging mama, pero ginagawa mong madali",
    "magandang umaga hon! miss na miss ko kayong tatlo",
]

MESSAGES_HEALTH = [
    "good morning hon! 'take care of your body, it's the only place you have to live'",
    "magandang umaga hon! 'health is not about weight lost, but life gained'",
    "good morning hon! 'eating well is a form of self-respect', kaya go ka lang",
    "magandang umaga hon! 'the body achieves what the mind believes', kaya mo 'yan",
    "good morning hon! 'movement is medicine', kahit maliit na jog, gamot na",
    "magandang umaga hon! 'your body hears everything your mind says', positive today ha",
    "good morning hon! 'sleep is the best meditation', sana nakatulog ka maayos",
    "magandang umaga hon! 'water is the driving force of all nature', inom ka ha",
    "good morning hon! tip: mag-stretch bago mag-jog, ayaw kong ma-injure ka",
    "magandang umaga hon! tip: inom ng tubig bago at pagkatapos ng workout",
    "good morning hon! tip: huwag laktawan rest day, kailangan 'yon ng katawan mo",
    "magandang umaga hon! tip: focus sa form, hindi sa bilis, mas safe 'yon",
]

MESSAGES_MENTAL = [
    "good morning hon! kamusta puso mo today? seryoso ako, miss kita",
    "magandang umaga hon! okay lang na pagod ka, hindi 'yon kabiguan",
    "good morning hon! kung mabigat today, huminga ka lang, kaya mo 'yan",
    "magandang umaga hon! hindi mo kailangang maging okay palagi, totoo ka lang",
    "good morning hon! nandito lang ako, kahit ano'ng mangyari, kapit lang",
    "magandang umaga hon! kung kailangan mo ng kausap, nandito lang ako",
    "good morning hon! okay lang na hindi okay ngayon, mahal pa rin kita",
    "magandang umaga hon! ingat sa sarili mo ha, mahalaga ka sa akin",
    "good morning hon! kung overwhelmed ka, isa-isa lang, kaya mo 'yan",
    "magandang umaga hon! proud ako sa'yo, kahit mahirap ang araw",
]

MESSAGES_INSPIRING = [
    "good morning hon! 'the only bad workout is the one that didn't happen'",
    "magandang umaga hon! 'progress, not perfection', bawat hakbang counted",
    "good morning hon! 'you are stronger than you think', paalala lang today",
    "magandang umaga hon! 'small steps every day lead to big results', tuloy lang",
    "good morning hon! 'your only limit is you', pero kaya mo 'yan",
    "magandang umaga hon! 'fall in love with taking care of yourself', deserve mo",
    "good morning hon! 'be stronger than your excuses', kaya mo 'yan",
    "magandang umaga hon! 'you don't have to be great to start', go ka na",
    "good morning hon! 'discipline is choosing what you want most', ikaw 'yon",
    "magandang umaga hon! 'the struggle today builds strength for tomorrow', kapit lang",
]

MESSAGES_LOVE = [
    "good morning hon! ikaw agad naisip ko pagkagising, araw-araw ganito",
    "magandang umaga hon! miss na miss kita, sana nandiyan ka lang",
    "good morning hon! mahal na mahal kita, walang dahilan kailangan",
    "magandang umaga hon! kahit malayo ka, ramdam ko yakap mo",
    "good morning hon! ikaw pa rin pinakamaganda para sa akin",
    "magandang umaga hon! araw-araw kitang pipiliin, walang duda",
    "good morning hon! nandito lang ako palagi, kapit lang mahal",
    "magandang umaga hon! sana maramdaman mo kung gaano kita kamahal",
    "good morning hon! mahirap magmahal ng malayo, pero sa'yo madali lang",
    "magandang umaga hon! mahal kita, sobra, lagi, palagi",
]

# ---- Day-of-week theme map (Monday=0 ... Sunday=6) ----
THEMES = {
    0: MESSAGES_WORKOUT,      # Monday
    1: MESSAGES_WORK,         # Tuesday
    2: MESSAGES_KIDS,         # Wednesday
    3: MESSAGES_HEALTH,       # Thursday
    4: MESSAGES_MENTAL,       # Friday
    5: MESSAGES_INSPIRING,    # Saturday
    6: MESSAGES_LOVE,         # Sunday
}

THEME_NAMES = {
    0: "workout", 1: "work", 2: "kids", 3: "health",
    4: "mental", 5: "inspiring", 6: "love",
}


def today_in_manila():
    return datetime.now(timezone(timedelta(hours=8)))


def is_leap(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def parse_birthdays(raw):
    entries = []
    for chunk in raw.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = [p.strip() for p in chunk.split("|")]
        if len(parts) != 3:
            print(f"Skipping badly formatted birthday entry: {chunk!r}")
            continue
        entries.append(tuple(parts))
    return entries


def birthdays_today():
    now = today_in_manila()
    key = TEST_DATE or now.strftime("%m-%d")
    found = []
    for date, number, name in parse_birthdays(BIRTHDAYS):
        leap_case = date == "02-29" and key == "02-28" and not is_leap(now.year)
        if date == key or leap_case:
            found.append((number, name))
    return found


# ---- No-repeat memory helpers ----
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


def pick_unused(theme_key, pool, state):
    """Pick a random unused message from the pool. Reset that pool if all used."""
    used = set(state.get(theme_key, []))
    available = [m for m in pool if m not in used]
    if not available:
        # Everything sent — reset this category's memory
        print(f"All '{theme_key}' messages used. Resetting this category.")
        available = pool[:]
        used = set()
    choice = random.choice(available)
    used.add(choice)
    state[theme_key] = list(used)
    return choice


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

    daily_numbers = [n.strip() for n in (RECIPIENT_PHONE_NUMBER or "").split(",") if n.strip()]
    state = load_state()

    # 1) Birthday greetings first.
    celebrating = birthdays_today()
    for number, name in celebrating:
        msg = pick_unused("birthday", BIRTHDAY_MESSAGES, state)
        send([number], msg)

    # 2) Daily themed message to everyone else.
    birthday_numbers = {number for number, _ in celebrating}
    daily_numbers = [n for n in daily_numbers if n not in birthday_numbers]

    if daily_numbers:
        weekday = today_in_manila().weekday()          # 0=Mon ... 6=Sun
        pool = THEMES[weekday]
        theme_key = THEME_NAMES[weekday]
        msg = pick_unused(theme_key, pool, state)
        print(f"Today's theme: {theme_key}")
        send(daily_numbers, msg)
    else:
        print("No one left for the regular good morning message today.")

    save_state(state)


if __name__ == "__main__":
    send_message()
