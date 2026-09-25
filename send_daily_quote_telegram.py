"""
send_daily_quote_telegram.py

Sends yourself one random "inspirational quote" per day, phrased like a
casual text from a friend, delivered via a Telegram bot.

SETUP (see SETUP_TELEGRAM.md for full walkthrough):
  1. pip install requests
  2. Create a bot via @BotFather on Telegram, get your bot token.
  3. Message your bot once, then get your chat ID (instructions in setup doc).
  4. Set the two environment variables below.
  5. Run once manually to test: python send_daily_quote_telegram.py
  6. Schedule it to run once a day (cron / Task Scheduler / GitHub Actions).
"""

import os
import random
import requests

# ---- Config: pull from environment variables ----
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# ---- The "messages" ----
# Written to sound like a friend texting, not a quote graphic.
# Feel free to add/remove/edit — make some sound like YOUR friends actually text.
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
    "you know that thing you're worried about? I think you're gonna handle it better than you expect",
    "just a heads up that you're doing better than the voice in your head is telling you",
    "sending you good energy today, no context needed",
    "you've survived every hard day so far, 100% track record, not bad honestly",
    "not to get sappy but I'm rooting for you, always have been",
]

def send_message():
    if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
        raise SystemExit(
            "Missing config. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID as "
            "environment variables. See SETUP_TELEGRAM.md."
        )

    body = random.choice(MESSAGES)
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    response = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": body})
    response.raise_for_status()
    print(f"Sent: {body}")


if __name__ == "__main__":
    send_message()
