"""
send_daily_quote_own_phone.py

Sends one random casual message per day as a real SMS from YOUR OWN phone
number, using the "SMS Gateway for Android" app as the sending mechanism.
Your phone's SIM does the actual sending — this script just tells it to.

SETUP (see SETUP_OWN_PHONE.md for full walkthrough):
  1. Install "SMS Gateway for Android" from the Play Store on the phone
     whose number you want to send from.
  2. In the app, enable Cloud Server mode and sign in / register — this
     gives you an API login + password AND lets this script reach your
     phone from anywhere (not just your home wifi).
  3. pip install requests
  4. Set the environment variables below.
  5. Run once manually to test: python send_daily_quote_own_phone.py
  6. Schedule it (cron / Task Scheduler / GitHub Actions) — your phone
     just needs internet access (wifi or mobile data) at send time.
"""

import os
import random
from datetime import datetime, timedelta, timezone

import requests
from requests.auth import HTTPBasicAuth

# ---- Config: pull from environment variables ----
SMSGATEWAY_LOGIN = os.environ.get("SMSGATEWAY_LOGIN")
SMSGATEWAY_PASSWORD = os.environ.get("SMSGATEWAY_PASSWORD")
RECIPIENT_PHONE_NUMBER = os.environ.get("RECIPIENT_PHONE_NUMBER")  # one or more numbers, separated by commas, e.g. +639171234567,+639181234567

SMSGATEWAY_URL = "https://api.sms-gate.app/3rdparty/v1/messages"

# ---- Birthdays ----
# The list lives in a GitHub secret called BIRTHDAYS (your repo is public, so
# numbers must NOT be written in this file). Format, entries separated by ;
#   MM-DD|+63number|Name        e.g.  03-15|+639171234567|Ana;11-02|+639181234567|Ben
BIRTHDAYS = os.environ.get("BIRTHDAYS", "")
TEST_DATE = os.environ.get("TEST_DATE", "").strip()   # optional, MM-DD, pretend it's this date
DRY_RUN = os.environ.get("DRY_RUN", "").strip() == "1"  # optional, print instead of sending

# {name} is replaced with the person's name. Edit these freely.
BIRTHDAY_MESSAGES = [
    "happy birthday {name}!! hope your day is full of good things, you deserve all of it",
    "hey {name}, happy birthday! thinking of you today and hope it's a great one",
    "happy birthday {name}! another year of you being awesome, enjoy every bit of today",
    "{name}!! happy birthday, hope you get spoiled today and eat something really good",
    "happy birthday {name}, wishing you a day as great as you are",
]

# ---- The messages ----
MESSAGES = [
    # --- Love & relationships (casual) ---
    "ok but have i told you today that you're doing great at this whole loving-people thing",
    "not to be soft but i hope you know you're worth choosing, every time, not just when it's convenient",
    "reminder that you don't have to earn love by being easy to deal with 24/7",
    "hope whoever you love knows how lucky they got fr",
    "you ever think about how you deserve the same patience you give everyone else? just a thought",
    "psa: loving yourself counts as loving someone too, don't skip that one",
    "sending you love today, unprompted, no occasion, just felt like it",
    "the right person is gonna think your weird little quirks are the best part ngl",
    "you deserve a love that doesn't feel like homework",
    "hope you're letting yourself be loved and not just doing all the loving lol",
    "you're allowed to want calm, boring, easy love. that's not too much to ask",
    "just remembered how good you are at making people feel safe. wanted to say that",
    "someone out there is lucky to have you and if it's not obvious to them yet, it will be",
    "not everyone gets it right but i think you love pretty well, just saying",
    "you know you're allowed to protect your peace even in relationships you love right",
    "hope today you feel a little more loved than yesterday",
    "reminder that your love language probably deserves to be spoken back to you too",
    "you give really good love honestly. hope it comes back around",
    "it's ok to miss someone and still be fine. both things can be true",
    "you don't have to perform being fine for people who actually love you",

    # --- Check-ins (casual) ---
    "hey be real with me for a sec, how are you actually doing",
    "not the fine version, the real version, how's it going today",
    "just checking in bc you crossed my mind, no pressure to reply",
    "how's your heart today. weird question ik but i mean it",
    "hope you drank water today and stepped outside for like 5 minutes minimum",
    "you've been on my mind lately, everything good over there",
    "not gonna lie just wanted to make sure you're doing ok this week",
    "how are you holding up fr fr",
    "are you resting or are you doing the thing where you say you're resting but you're not",
    "hey lowkey just wanted to say hi and see how you're feeling today",
    "you good? and i mean actually good not just 'i'm fine' good",
    "what's something good that happened today, even small counts",
    "hope today wasn't too much for you. if it was, that's ok too",
    "checking in bc i care, that's it, that's the whole text",
    "hey no big reason just wanted you to know someone's thinking about you rn",
    "how's the week treating you so far",
    "are you eating enough today, real talk",
    "you don't have to have a good answer, i just want to know how you are",
    "hope you're not being too hard on yourself today",
    "just a random hi, hope your day's going easy on you",

    # --- Motivational / encouragement (casual voice) ---
    "you've got this, whatever 'this' is today",
    "ngl you're handling more than people realize and doing it well",
    "small steps still count as steps, don't let anyone tell you otherwise",
    "you don't have to have it all figured out today, one thing at a time",
    "proud of you for showing up even on the annoying days",
    "you're doing better than the voice in your head is telling you",
    "not to be dramatic but you're built different fr",
    "reminder you're allowed to be proud of the small wins too",
    "you're not behind, you're just on your own timeline and that's fine",
    "hope today goes easy on you, and if it doesn't, tomorrow's a reset",
    "you've survived every hard day so far, 100% track record ngl",
    "sending good energy your way today no context needed",
    "you're allowed to rest, it's not the same as giving up",
    "whatever you're worried about, i think you'll handle it better than you expect",
    "you keep showing up and that says a lot about you honestly",
    "it's ok to not be productive every single day, you're still worth something",
    "you're doing the best you can with what you've got and that's enough",
    "just a heads up you're more capable than you give yourself credit for",
    "today doesn't have to be perfect to count",
    "you're allowed to be a work in progress, most of us are",

    # --- Famous quotes, paraphrased casually (never word-for-word) ---
    "reminded of that einstein thing today, how it's less about being a genius and more about not quitting when it's hard",
    "you know that eleanor roosevelt idea, how no one can make you feel small without you letting them? been thinking about that",
    "there's a maya angelou line about how people forget what you said but never how you made them feel. thought of you",
    "churchill supposedly said success is just failing a bunch without losing your spark. felt like you needed that",
    "rumi had this idea that your wounds are kind of where the light gets in. kinda beautiful ngl",
    "mandela said something like it always seems impossible until it's done. thought of you today",
    "there's a confucius quote about how it doesn't matter how slow you go as long as you don't stop",
    "someone once said the best way out of something hard is straight through it",
    "there's that line about missing 100% of the shots you don't take, cheesy but kinda true",
    "frida kahlo talked about planting your own garden instead of waiting for someone to bring you flowers. love that one",
    "lao tzu said a journey of a thousand miles starts with one step. you've already started, you know",
    "someone smart once said worrying is like paying a debt you don't even owe yet",
    "there's a quote about how the only way to do great work is to love what you're doing. do you love what you're doing lately",
    "marcus aurelius had this whole thing about the obstacle being the way forward, not something blocking you",
    "audrey hepburn said something about how nothing is impossible, the word itself says 'i'm possible'. corny but i like it",
    "there's a thoreau line about going confidently in the direction of your dreams. felt like you needed that today",
    "steve jobs said your time is limited so don't waste it living someone else's life. hits different sometimes",
    "there's a quote from anne frank about how it's a wonder people haven't given up hope, given everything. resilience is wild",
    "oprah has this idea that turning wounds into wisdom is the whole point. thought that fit today",
    "there's a line from c.s. lewis about how you're never too old to set a new goal or dream a new dream",
    "helen keller said life is either a daring adventure or nothing at all. bit intense but kinda motivating",
    "there's a quote about how the best time to plant a tree was 20 years ago, second best time is now",
    "bruce lee had this idea about being like water, adapting to whatever shape life needs you to be",
    "there's a line from viktor frankl about how everything can be taken from you except how you choose to respond to what happens",
    "someone once said be yourself bc everyone else is already taken. simple but true",
]

def today_in_manila():
    # Philippines is UTC+8 year-round; a fixed offset needs no timezone data.
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
            print(f"Skipping badly formatted birthday entry (expected MM-DD|number|Name): {chunk!r}")
            continue
        entries.append(tuple(parts))
    return entries


def birthdays_today():
    """Return [(number, name), ...] for anyone whose birthday is today (Manila time)."""
    now = today_in_manila()
    key = TEST_DATE or now.strftime("%m-%d")
    found = []
    for date, number, name in parse_birthdays(BIRTHDAYS):
        # Feb 29 birthdays get their greeting on Feb 28 in non-leap years.
        leap_case = date == "02-29" and key == "02-28" and not is_leap(now.year)
        if date == key or leap_case:
            found.append((number, name))
    return found


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
            "RECIPIENT_PHONE_NUMBER as environment variables. See SETUP_OWN_PHONE.md."
        )

    daily_numbers = [n.strip() for n in (RECIPIENT_PHONE_NUMBER or "").split(",") if n.strip()]

    # 1) Birthday greetings first.
    celebrating = birthdays_today()
    for number, name in celebrating:
        send([number], random.choice(BIRTHDAY_MESSAGES).format(name=name))

    # 2) Daily message to everyone else. Anyone getting a birthday text today
    #    skips the regular message so they only get the birthday one.
    birthday_numbers = {number for number, _ in celebrating}
    daily_numbers = [n for n in daily_numbers if n not in birthday_numbers]
    if daily_numbers:
        send(daily_numbers, random.choice(MESSAGES))
    else:
        print("No one left for the regular daily message today.")


if __name__ == "__main__":
    send_message()
