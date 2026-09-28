"""
send_daily_goodmorning_sms.py

Sends one random good-morning message per day at 8AM (Manila time) as a real
SMS from YOUR OWN phone number, using the "SMS Gateway for Android" app.

SETUP:
  1. Install "SMS Gateway for Android" from the Play Store.
  2. Enable Cloud Server mode and sign in / register for API login + password.
  3. pip install requests
  4. Set the environment variables below.
  5. Schedule it to run at 8AM Manila time (cron: 0 0 * * * UTC = 8AM PHT).
"""

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

BIRTHDAY_MESSAGES = [
    "happy birthday mahal!! sobrang swerte ko sa'yo, I hope today is as beautiful as you are",
    "uy hon, happy birthday! mahal na mahal kita, enjoy your day ha",
    "happy birthday babe! isa na namang taon na kasama kita, thank you for everything",
    "mahal, happy birthday! sana ma-spoil kita today, deserve mo lahat",
    "happy birthday hon, ikaw pa rin ang pinakamagandang nanay at asawa para sa akin",
]

# ---- 8AM Good morning messages (as a husband to his wife) ----

# --- Category 1: Workout / jogging / eating healthy ---
MESSAGES_WORKOUT = [
    "good morning mahal! ingat sa jog mo ha, miss na miss na kita",
    "magandang umaga hon! sana maganda ang takbo mo ngayon, proud na proud ako sa'yo palagi",
    "good morning babe! nakapag-workout ka na? kahit hindi pa, gwapa ka pa rin sa akin",
    "magandang umaga mahal! inom ka ng tubig ha, ayaw kong ma-dehydrate ka",
    "good morning hon! alam kong sinusunod mo yang healthy living mo, sobrang proud ako sa'yo",
    "magandang umaga babe! sabi mo dati magiging consistent ka, and look at you now, grabe ka",
    "good morning mahal! sana hindi masakit katawan mo, ingat ka diyan sa takbo mo",
    "magandang umaga hon! sarap siguro ng almusal mo ngayon, inggit ako haha miss kita",
    "good morning babe! kahit ang layo ko, ramdam ko yang sipag mo, sobrang proud ako",
    "magandang umaga mahal! para sa'yo yang workout mo, hindi lang sa katawan, para rin sa isip mo",
]

# --- Category 2: Missing the kids ---
MESSAGES_KIDS = [
    "good morning mahal! alam kong miss mo na ang mga bata, ako rin miss ko na kayong lahat",
    "magandang umaga hon! nandiyan lang sila sa puso mo palagi, kahit malayo",
    "good morning babe! miss na miss mo sila no? ako rin, mahal na mahal ko kayong tatlo",
    "magandang umaga mahal! tawagan mo sila mamaya ha, gagaan pakiramdam mo, promise",
    "good morning hon! ang mga bata, swerte sa'yo. ikaw ang pinakamagandang nanay sa mundo",
    "magandang umaga babe! bawat araw, palapit nang palapit tayo sa pagsasama ulit, kapit lang",
    "good morning mahal! kahit hindi mo sila kasama ngayon, alam nila kung gaano mo sila kamahal",
    "magandang umaga hon! sabihin mo sa mga bata mamaya mahal na mahal sila ni daddy",
    "good morning babe! ikaw ang puso ng pamilya natin, kahit malayo ka, ikaw pa rin ang sentro",
    "magandang umaga mahal! sabi nila mahirap maging nanay, pero ikaw, ginagawa mong madali ang lahat",
]

# --- Category 3: Husband's appreciation of his wife ---
MESSAGES_MOM = [
    "good morning mahal! sobrang proud ako sa'yo, mom of 2, nagwoworkout, nag-aalaga pa. superhero ka",
    "magandang umaga hon! hindi ko alam paano mo nagagawa lahat, pero ginagawa mo. amazing ka",
    "good morning babe! alam kong pagod ka, pero hindi mo ipinapakita. mahal na mahal kita",
    "magandang umaga mahal! ikaw ang pinakamalakas na taong kilala ko, at asawa kita, swerte ko",
    "good morning hon! kahit sobrang busy mo, lagi mo pa rin akong naaalala. thank you mahal",
    "magandang umaga babe! sana may oras ka rin para sa sarili mo ngayon, deserve mo 'yon",
    "good morning mahal! ikaw ang dahilan kung bakit okay ako palagi, alam mo ba 'yon",
    "magandang umaga hon! proud ako sa lahat ng ginagawa mo, kahit hindi ko sinasabi madalas",
    "good morning babe! ang tibay mo, ang galing mo, ang sarap mo mahalin. good morning mahal",
    "magandang umaga mahal! kahit magkalayo tayo ngayon, ikaw pa rin ang unang iniisip ko pagkagising",
]

# --- Category 4: Sweet & romantic ---
MESSAGES_LOVE = [
    "good morning mahal! ikaw agad ang naisip ko pagkagising ko, araw-araw ganito",
    "magandang umaga hon! miss na miss na kita, sana nandiyan ka lang",
    "good morning babe! sana maganda gising mo, mahal na mahal kita",
    "magandang umaga mahal! paalala lang, mahal kita, sobra, walang dahilan kailangan",
    "good morning hon! kahit malayo ka, ramdam ko pa rin ang yakap mo",
    "magandang umaga babe! ikaw pa rin ang pinakamagandang babae para sa akin, walang kupas",
    "good morning mahal! sana ngayon, maramdaman mo kung gaano kita kamahal",
    "magandang umaga hon! nandito lang ako palagi, kahit ano'ng mangyari, kapit lang",
    "good morning babe! sabi nila mahirap magmahal ng malayo, pero sa'yo, madali lang pala",
    "magandang umaga mahal! araw-araw kitang pipiliin, walang sawa, walang duda",
]

# --- Category 5: Healthy quotes (husband voice) ---
MESSAGES_HEALTHY_QUOTES = [
    "good morning mahal! sabi nila, 'take care of your body, it's the only place you have to live.' kaya alagaan mo sarili mo ha, para sa akin at sa mga bata",
    "magandang umaga hon! 'health is not about the weight you lose, but the life you gain.' proud ako sa journey mo",
    "good morning babe! 'eating well is a form of self-respect.' kaya go ka lang sa healthy food mo, suporta ako palagi",
    "magandang umaga mahal! 'the body achieves what the mind believes.' alam kong kaya mo 'yan, ikaw pa",
    "good morning hon! 'movement is medicine.' kaya kahit maliit na jog lang, gamot na 'yon, sabi nila",
    "magandang umaga babe! 'your body hears everything your mind says.' kaya positive thoughts today ha, mahal",
    "good morning mahal! 'a healthy outside starts from the inside.' alagaan mo puso mo today, at ako naman ang bahala sa pagmamahal",
    "magandang umaga hon! 'sleep is the best meditation.' sana nakatulog ka nang maayos kagabi, mahal",
    "good morning babe! 'water is the driving force of all nature.' inom ka ng tubig ha, ayaw kong mauhaw ka",
    "magandang umaga mahal! 'the food you eat can be the safest form of medicine.' kaya proud ako sa healthy choices mo",
]

# --- Category 6: Exercise tips (husband voice) ---
MESSAGES_EXERCISE_TIPS = [
    "good morning mahal! tip ko sa'yo today: mag-stretch ka muna bago mag-jog, ayaw kong ma-injure ka",
    "magandang umaga hon! inom ka ng tubig bago, habang, at pagkatapos ng workout ha, mahal",
    "good morning babe! kung masakit tuhod mo sa jog, maglakad ka muna, huwag mo pilitin",
    "magandang umaga mahal! 10 minutong stretching bago matulog, gagaan katawan mo bukas, promise",
    "good morning hon! huwag mong laktawan ang rest day ha, kailangan 'yon ng katawan mo",
    "magandang umaga babe! kapag pagod ka, 20 minutong brisk walk lang, sapat na 'yon, mahal",
    "good morning mahal! focus ka sa form, hindi sa bilis, mas safe at effective 'yon",
    "magandang umaga hon! dagdagan mo ng protina almusal mo, para may energy ka sa workout",
    "good morning babe! pagkatapos ng workout, mag-stretch at mag-hydrate, recovery is key, mahal",
    "magandang umaga mahal! kung tinatamad ka, sabihin mo '5 minutes lang', tapos tuloy-tuloy na 'yan",
    "good morning hon! suotin mo ang tamang sapatos sa jog ha, para sa safety mo",
    "magandang umaga babe! mag-jog ka sa umaga kung kaya, mas fresh hangin at mas magaan pakiramdam",
]

# --- Category 7: Inspiring quotes (husband voice) ---
MESSAGES_INSPIRING = [
    "good morning mahal! 'the only bad workout is the one that didn't happen.' kaya kahit maliit lang, go ka lang, suporta ako",
    "magandang umaga hon! 'you don't have to be extreme, just consistent.' totoo 'yan para sa'yo, mahal",
    "good morning babe! 'progress, not perfection.' bawat hakbang mo, counted 'yon sa akin",
    "magandang umaga mahal! 'the body achieves what the mind believes.' kaya mo 'yan today, alam ko",
    "good morning hon! 'discipline is choosing between what you want now and what you want most.' ikaw 'yon, mahal",
    "magandang umaga babe! 'you are stronger than you think.' paalala lang 'yan today, mahal ko",
    "good morning mahal! 'small steps every day lead to big results.' kaya tuloy lang, nandito ako",
    "magandang umaga hon! 'your only limit is you.' pero alam kong kayang-kaya mo, mahal",
    "good morning babe! 'fall in love with taking care of yourself.' deserve mo 'yon, at mahal kita",
    "magandang umaga mahal! 'the struggle you're in today is developing the strength you need for tomorrow.' kapit lang ha",
    "good morning hon! 'you don't have to be great to start, but you have to start to be great.' go ka na, mahal",
    "magandang umaga babe! 'be stronger than your excuses.' kaya mo 'yan, mom of 2 pa, asawa ko pa",
]

# --- Category 8: Short & everyday (husband voice) ---
MESSAGES_SHORT = [
    "good morning mahal! kamusta ka na? miss na miss kita",
    "magandang umaga hon! ingat ka lagi ha, mahal kita",
    "good morning babe! sana masarap kape mo ngayon, mahal",
    "magandang umaga mahal! kaya mo 'yan today, nandito lang ako",
    "good morning hon! laban lang, mahal na mahal kita",
]

# Combine all categories so any one can be picked.
MESSAGES = (
    MESSAGES_WORKOUT
    + MESSAGES_KIDS
    + MESSAGES_MOM
    + MESSAGES_LOVE
    + MESSAGES_HEALTHY_QUOTES
    + MESSAGES_EXERCISE_TIPS
    + MESSAGES_INSPIRING
    + MESSAGES_SHORT
)


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
            print(f"Skipping badly formatted birthday entry (expected MM-DD|number|Name): {chunk!r}")
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

    # 1) Birthday greetings first.
    celebrating = birthdays_today()
    for number, name in celebrating:
        send([number], random.choice(BIRTHDAY_MESSAGES).format(name=name))

    # 2) 8AM good morning message to everyone else.
    birthday_numbers = {number for number, _ in celebrating}
    daily_numbers = [n for n in daily_numbers if n not in birthday_numbers]
    if daily_numbers:
        send(daily_numbers, random.choice(MESSAGES))
    else:
        print("No one left for the regular good morning message today.")


if __name__ == "__main__":
    send_message()