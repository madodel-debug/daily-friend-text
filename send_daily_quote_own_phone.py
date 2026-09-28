"""
send_daily_goodmorning_sms.py

Sends one random message per day at 5:30 AM (Manila time) as a real SMS from
YOUR OWN phone number, using the "SMS Gateway for Android" app.

FEATURES:
  - Randomized greeting position: sometimes greeting first, sometimes at the end
  - No-repeat memory (state file remembers what's been sent)
  - Day-of-week themes (Mon=gym, Tue=work, Wed=kids, Thu=health,
    Fri=mental health, Sat=inspiring, Sun=love)
  - Short & sweet only (all messages under ~160 chars)
  - Husband voice, randomized endearments: hon / mama / mahal / love
  - Famous quotes paraphrased naturally, name often AFTER the quote

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
STATE_FILE = os.environ.get("STATE_FILE", "sent_state.json")

BIRTHDAY_MESSAGES = [
    "swerte ko sa'yo, mahal na mahal kita",
    "enjoy your day ha, deserve mo lahat",
    "isa na namang taon na kasama kita, thank you",
    "sana ma-spoil kita today",
    "ikaw pa rin pinakamaganda para sa akin",
]

# ============================================================
# DAY-OF-WEEK THEMES
# ============================================================
# Monday    = gym / lifting / workout
# Tuesday   = work check-in
# Wednesday = kids / missing them
# Thursday  = health tips & healthy quotes
# Friday    = mental health check-in
# Saturday  = inspiring quotes
# Sunday    = love / romantic

# ---- Greeting options (used at start OR end, randomly) ----
GREETINGS = [
    "good morning hon!",
    "magandang umaga mama!",
    "good morning mahal!",
    "magandang umaga love!",
    "good morning, hon!",
    "magandang umaga, mahal!",
    "good morning, love!",
    "magandang umaga, mama!",
]

BIRTHDAY_GREETINGS = [
    "happy birthday mama!!",
    "happy birthday hon!",
    "happy birthday love!",
    "happy birthday mahal!",
]

MESSAGES_WORKOUT = [
    "ingat sa gym mo ha, miss na miss kita.",
    "proud ako sa'yo palagi, lift ka lang diyan.",
    "inom ka ng tubig ha, ayaw kong ma-dehydrate ka sa gym.",
    "sipag mo sa weights, sobrang proud ako sa'yo.",
    "sabi mo magiging consistent ka sa gym, and look at you now.",
    "ingat sa lift mo ha, mahal kita.",
    "sarap siguro post-workout meal mo ngayon, miss kita.",
    "kahit malayo ako, ramdam ko sipag mo sa gym.",
    "para sa'yo yang workout mo, proud ako.",
    "hydrate ka ha, mahal kita.",
    "go ka lang diyan sa gym, nandito lang ako.",
    "miss ka ng mga bata, miss din kita.",
    "kaya mo 'yan, lift lang.",
    "proud na proud ako sa'yo.",
    "ingat ka sa gym ha, mahal kita.",
    "sipag mo grabe, miss kita.",
    "sana maganda leg day mo, kaya mo 'yan.",
    "PR today? alam kong kaya mo.",
    "ingat sa form ha, ayaw kong ma-injure ka.",
    "lakas mo, proud ako.",
    "rest day ka ba today? deserve mo 'yon.",
    "kain ka protina after gym ha.",
    "sana magaan workout mo today.",
    "gym na naman? ang galing mo.",
]

MESSAGES_WORK = [
    "kamusta work mo lately? miss kita.",
    "sana hindi masyadong mabigat trabaho mo today.",
    "kung stressed ka sa work, huminga ka lang ha.",
    "proud ako sa lahat ng ginagawa mo sa work.",
    "wag mo pilitin sarili mo sa work ha, mahal kita.",
    "sana okay lang work mo today, nandito lang ako.",
    "kung pagod ka sa work, magpahinga ka ha.",
    "hindi mo kailangang gawin lahat today, isa-isa lang.",
    "kamusta ka na ba talaga? miss kita.",
    "proud ako sa'yo, kahit hindi mo naririnig madalas.",
    "kaya mo 'yan, nandito lang ako.",
    "ingat ka sa work ha, mahal kita.",
    "miss kita, kamusta work?",
    "sana magaan araw mo sa work.",
    "laban lang, nandito ako.",
    "proud ako sa'yo, lagi.",
]

MESSAGES_KIDS = [
    "miss mo na sila no? ako rin miss ko kayong lahat.",
    "nandiyan lang sila sa puso mo palagi.",
    "videocall mo mga bata mamaya ha.",
    "ang mga bata swerte sa'yo, ikaw pinakamagandang mama.",
    "palapit nang palapit tayo sa pagsasama ulit, kapit lang.",
    "mahal na mahal ka ng mga bata, alam mo 'yon.",
    "sabihin mo sa mga bata mahal sila ni daddy.",
    "ikaw puso ng pamilya natin, miss kita.",
    "mahirap maging mama, pero ginagawa mong madali.",
    "miss na miss ko kayong tatlo.",
    "miss ka ng mga bata, miss din kita.",
    "mahal ka namin, lagi.",
    "nandito lang kami palagi.",
    "ikaw pinakamagaling na mama, promise.",
    "miss na miss ka namin, mahal kita.",
    "proud kami sa'yo, lagi.",
]

MESSAGES_HEALTH = [
    "'take care of your body, it's the only place you have to live.'",
    "'health is not about weight lost, but life gained.'",
    "'eating well is a form of self-respect', kaya go ka lang.",
    "'the body achieves what the mind believes', kaya mo 'yan.",
    "'movement is medicine', kahit maliit na workout, gamot na.",
    "'your body hears everything your mind says', positive today ha.",
    "'sleep is the best meditation', sana nakatulog ka maayos.",
    "'water is the driving force of all nature', inom ka ha.",
    "tip: mag-warm up muna bago mag-lift, ayaw kong ma-injure ka.",
    "tip: inom ng tubig bago at pagkatapos ng gym.",
    "tip: huwag laktawan rest day, kailangan 'yon ng muscles mo.",
    "tip: focus sa form, hindi sa bigat, mas safe 'yon.",
    "'an apple a day keeps the doctor away', kain ka prutas ha.",
    "tip: mag-stretch after gym, iwas sakit ng katawan.",
    "inom ka tubig ha, mahal kita.",
    "kain ka maayos today, ha.",
    "tip: dagdagan mo protina, para tumibay muscles mo.",
    "tip: mag-squat ka today, lakas ng legs, lakas ng puso.",
]

MESSAGES_MENTAL = [
    "kamusta puso mo today? seryoso ako, miss kita.",
    "okay lang na pagod ka, hindi 'yon kabiguan.",
    "kung mabigat today, huminga ka lang, kaya mo 'yan.",
    "hindi mo kailangang maging okay palagi, totoo ka lang.",
    "nandito lang ako, kahit ano'ng mangyari, kapit lang.",
    "kung kailangan mo ng kausap, nandito lang ako.",
    "okay lang na hindi okay ngayon, mahal pa rin kita.",
    "ingat sa sarili mo ha, mahalaga ka sa akin.",
    "kung overwhelmed ka, isa-isa lang, kaya mo 'yan.",
    "proud ako sa'yo, kahit mahirap ang araw.",
    "okay lang magpahinga, hindi 'yon pagsuko.",
    "mahal kita, kahit anong mood mo today.",
    "huminga ka lang, nandito ako.",
    "kaya mo 'yan, mahal kita.",
    "nandito lang ako, lagi.",
    "mahal kita, alagaan mo sarili mo.",
]

MESSAGES_INSPIRING = [
    # Short everyday
    "'progress, not perfection', bawat hakbang counted.",
    "'you are stronger than you think', paalala lang.",
    "'small steps every day lead to big results', tuloy lang.",
    "'your only limit is you', pero kaya mo 'yan.",
    "'fall in love with taking care of yourself', deserve mo.",
    "'be stronger than your excuses', kaya mo 'yan.",
    "'you don't have to be great to start', go ka na.",
    "'discipline is choosing what you want most', ikaw 'yon.",
    "'the struggle today builds strength for tomorrow', kapit lang.",
    "'the only bad workout is the one that didn't happen'.",
    "'strength doesn't come from what you can do, but overcoming what you couldn't'.",

    # --- Famous quotes: quote-first, name-after or unsure, natural voice ---
    "people forget what you said but never how you made them feel. parang si Maya Angelou yata 'yon.",
    "sa sugat mo raw pumapasok ang liwanag. si Rumi yata nagsabi, ang ganda 'no.",
    "parang imposible lagi hanggang sa matapos. hindi ako sure kung si Mandela 'yon.",
    "hindi mahalaga kung gaano kabagal basta hindi huminto. si Confucius yata 'yon.",
    "ang libong milya raw nagsisimula sa isang hakbang. nagsimula ka na, parang si Lao Tzu 'yon.",
    "walang makakapagpaliit sa'yo nang hindi mo pinapayagan. si Eleanor Roosevelt yata 'yon.",
    "tagumpay raw ang paulit-ulit na pagkabigo nang hindi nawawalan ng ningas. si Churchill yata.",
    "walang imposible, 'i'm possible' nga ang salita mismo. si Audrey Hepburn yata 'yon.",
    "lakad raw nang may kumpiyansa sa direksyon ng pangarap mo. parang si Thoreau 'yon.",
    "kahanga-hanga raw na hindi pa sumuko ang tao sa pag-asa. si Anne Frank yata.",
    "ang buhay raw ay daring adventure o wala. hindi ako sure kung si Helen Keller 'yon.",
    "maging parang tubig raw, umaangkop sa kahit anong hugis. parang si Bruce Lee 'yon.",
    "lahat raw makukuha sa'yo maliban sa pagpili mo ng tugon. si Viktor Frankl yata.",
    "limitado raw oras mo, wag sayangin sa buhay ng iba. si Steve Jobs yata 'yon.",
    "gawin raw karunungan ang sugat, 'yon ang punto. parang si Oprah 'yon.",
    "ang hadlang raw ay ang daan pasulong. si Marcus Aurelius yata.",
    "magtanim ka raw ng sarili mong hardin, wag maghintay ng bulaklak. si Frida Kahlo yata 'yon.",
    "hindi ka pa raw matanda para sa bagong pangarap. hindi ako sure kung si C.S. Lewis 'yon.",
    "hindi raw tungkol sa pagiging henyo kundi sa hindi pagsuko. si Einstein yata.",
    "best time raw magtanim ng puno ay 20 taon nakalipas, pangalawa ay ngayon. hindi ko maalala kung sino nagsabi.",
    "ang huling 3-4 reps raw ang nagpapalaki ng muscles. parang si Arnold 'yon.",
    "hindi raw niya binibilang ang sit-ups hanggang sumakit. si Muhammad Ali yata 'yon.",

    # Short closers
    "kaya mo 'yan, mahal kita.",
    "laban lang, nandito ako.",
    "proud ako sa'yo, lagi.",
]

MESSAGES_LOVE = [
    "ikaw agad naisip ko pagkagising, araw-araw ganito.",
    "miss na miss kita, sana nandiyan ka lang.",
    "mahal na mahal kita, walang dahilan kailangan.",
    "kahit malayo ka, ramdam ko yakap mo.",
    "ikaw pa rin pinakamaganda para sa akin.",
    "araw-araw kitang pipiliin, walang duda.",
    "nandito lang ako palagi, kapit lang.",
    "sana maramdaman mo kung gaano kita kamahal.",
    "mahirap magmahal ng malayo, pero sa'yo madali lang.",
    "mahal kita, sobra, lagi, palagi.",
    "miss kita, mahal kita.",
    "ikaw lang, lagi.",
    "mahal na mahal kita.",
    "miss na miss kita.",
    "ikaw ang lahat sa akin.",
    "mahal kita.",
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
    """Pick a random unused message. Reset that pool when all are used."""
    used = set(state.get(theme_key, []))
    available = [m for m in pool if m not in used]
    if not available:
        print(f"All '{theme_key}' messages used. Resetting this category.")
        available = pool[:]
        used = set()
    choice = random.choice(available)
    used.add(choice)
    state[theme_key] = list(used)
    return choice


def decorate(body, greeting):
    """Randomly place the greeting at the start OR end of the body."""
    if random.random() < 0.5:
        return f"{greeting} {body}"
    return f"{body} {greeting}"


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
        body = pick_unused("birthday", BIRTHDAY_MESSAGES, state)
        greeting = random.choice(BIRTHDAY_GREETINGS)
        send([number], decorate(body, greeting))

    # 2) Daily themed message to everyone else.
    birthday_numbers = {number for number, _ in celebrating}
    daily_numbers = [n for n in daily_numbers if n not in birthday_numbers]

    if daily_numbers:
        weekday = today_in_manila().weekday()
        pool = THEMES[weekday]
        theme_key = THEME_NAMES[weekday]
        body = pick_unused(theme_key, pool, state)
        greeting = random.choice(GREETINGS)
        full_message = decorate(body, greeting)
        print(f"Today's theme: {theme_key}")
        send(daily_numbers, full_message)
    else:
        print("No one left for the regular good morning message today.")

    save_state(state)


if __name__ == "__main__":
    send_message()
