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
import requests
from requests.auth import HTTPBasicAuth

# ---- Config: pull from environment variables ----
SMSGATEWAY_LOGIN = os.environ.get("SMSGATEWAY_LOGIN")
SMSGATEWAY_PASSWORD = os.environ.get("SMSGATEWAY_PASSWORD")
RECIPIENT_PHONE_NUMBER = os.environ.get("RECIPIENT_PHONE_NUMBER")  # who receives it, e.g. +639171234567

SMSGATEWAY_URL = "https://api.sms-gate.app/3rdparty/v1/message"

# ---- The messages ----
MESSAGES = [
    "hey, random thought but you've got this. whatever's stressing you out today, it's not gonna last forever",
    "yo just thinking about you, hope today's treating you decent. proud of you for keeping at it",
    "not to be dramatic but I really think you're doing better than you give yourself credit for",
    "reminder that you don't have to have it all figured out today. one thing at a time",
    "hey!! just wanted to say I believe in you, even on the annoying days",
    "thinking about how far you've come tbh. like genuinely",
    "small thing but — you showing up even when it's hard? that counts for a lot",
    "you're allowed to be proud of yourself for the small wins too, not just the big ones",
    "no big reason for this text, just wanted to remind you you're not behind, you're on your own timeline",
    "hope today goes easy on you. and if it doesn't, tomorrow's a reset",
]

def send_message():
    if not all([SMSGATEWAY_LOGIN, SMSGATEWAY_PASSWORD, RECIPIENT_PHONE_NUMBER]):
        raise SystemExit(
            "Missing config. Set SMSGATEWAY_LOGIN, SMSGATEWAY_PASSWORD, and "
            "RECIPIENT_PHONE_NUMBER as environment variables. See SETUP_OWN_PHONE.md."
        )

    body = random.choice(MESSAGES)

    response = requests.post(
        SMSGATEWAY_URL,
        json={
            "message": body,
            "phoneNumbers": [RECIPIENT_PHONE_NUMBER],
        },
        auth=HTTPBasicAuth(SMSGATEWAY_LOGIN, SMSGATEWAY_PASSWORD),
    )
    response.raise_for_status()
    print(f"Sent: {body}")
    print(f"Response: {response.json()}")


if __name__ == "__main__":
    send_message()
