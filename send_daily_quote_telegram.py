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
    # Love & relationships
    "hey, just a reminder that you deserve love that feels easy, not love that feels like a test",
    "thinking about you today and hoping whoever you love knows how lucky they are",
    "you know loving yourself counts too right? not just everyone else",
    "hope you're being as kind to yourself as you are to the people you love",
    "reminder: the right people won't make you question if you're too much",
    "sending love your way today, no occasion needed",
    "you're allowed to want a love that's calm. that's not asking too much",
    "just wanted to say I love how much you care about people, even when it's hard",

    # Check-ins
    "hey, how are you actually doing today? not the fine version, the real one",
    "checking in on you. no pressure to respond, just thinking of you",
    "how's your heart today?",
    "hope you drank some water and stepped outside today, just a little",
    "you've been on my mind, everything good?",
    "not gonna lie I just wanted to check you're doing okay this week",
    "how are you holding up? genuinely asking",
    "hey, are you resting enough or are you doing the thing where you don't",

    # Famous quotes, paraphrased casually
    "reminded of that Einstein line today — it's less about being smart and more about not giving up when it's hard",
    "you know that Eleanor Roosevelt thing about how no one can make you feel small without your permission? been thinking about that",
    "there's a quote from Maya Angelou about how people forget what you said but never how you made them feel — that's so true about you",
    "Churchill supposedly said success is just going from failure to failure without losing enthusiasm. felt like you needed that today",
    "there's this Rumi idea that your wound is where the light gets in — kind of beautiful when you think about it",
    "Mandela had that line about how it always seems impossible until it's done. thought of you today",
    "there's a quote — I think it's Confucius — about how it doesn't matter how slow you go as long as you
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
