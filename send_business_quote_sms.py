"""
send_business_quote_sms.py

Sends one quote per day about business, leadership, management, or
classic strategy (Art of War, 48 Laws of Power) as a real SMS.

HOW IT PICKS A QUOTE:
  1. If API_NINJAS_KEY is set, it first tries to fetch a fresh quote from
     the API Ninjas Quotes API (api-ninjas.com) in a random category:
     business, leadership, success, or money.
  2. If that fails for any reason (no key, network error, rate limit,
     bad response), it falls back to a curated local pool covering
     business, leadership, management, Art of War, and 48 Laws of Power
     themes. These are paraphrased in plain language rather than quoted
     verbatim from the books.
  3. The local pool has no-repeat memory (shared sent_state.json), same
     as the other scripts. The live API doesn't need this since it
     returns something different essentially every call.

SETUP:
  1. (Optional but recommended) Sign up free at https://api-ninjas.com,
     get an API key, and set it as the API_NINJAS_KEY secret. Without it,
     this script just uses the local pool every day, which still works
     fine, just isn't "fresh from the web."
  2. Same SMSGATEWAY_LOGIN / SMSGATEWAY_PASSWORD secrets as the other
     scripts, plus its own DAILY_QUOTE_RECIPIENT_NUMBER secret (separate
     from RECIPIENT_PHONE_NUMBER, so this can go to a different number
     if you want).

Optional env vars for testing:
  FORCE_FALLBACK=1   skip the API call and use the local pool directly
  DRY_RUN=1          print instead of sending
"""

import json
import os
import random

import requests
from requests.auth import HTTPBasicAuth

SMSGATEWAY_LOGIN = os.environ.get("SMSGATEWAY_LOGIN")
SMSGATEWAY_PASSWORD = os.environ.get("SMSGATEWAY_PASSWORD")
DAILY_QUOTE_RECIPIENT_NUMBER = os.environ.get("DAILY_QUOTE_RECIPIENT_NUMBER")
API_NINJAS_KEY = os.environ.get("API_NINJAS_KEY", "").strip()

SMSGATEWAY_URL = "https://api.sms-gate.app/3rdparty/v1/messages"
API_NINJAS_URL = "https://api.api-ninjas.com/v1/quotes"
API_CATEGORIES = ["business", "leadership", "success", "money"]

DRY_RUN = os.environ.get("DRY_RUN", "").strip() == "1"
FORCE_FALLBACK = os.environ.get("FORCE_FALLBACK", "").strip() == "1"

STATE_FILE = os.environ.get("STATE_FILE", "sent_state.json")

# ---- Curated fallback pool: business, leadership, management, Art of
# War, and 48 Laws of Power themes, paraphrased in plain language. ----
FALLBACK_QUOTES = [
    "Know the terrain before you commit to the fight - Sun Tzu's point was that information beats effort every time.",
    "The Art of War's core idea: the best wins are the ones where the other side never saw a real fight coming.",
    "Greene's 48 Laws often repeat one theme - guard your reputation, because it's the only thing people act on before they know you.",
    "Good management isn't control, it's removing the obstacles between your team and good work.",
    "Sun Tzu argued every battle is won before it's fought, in the planning, not the execution.",
    "One of the 48 Laws: never outshine the master - read the room before you show everyone what you're capable of.",
    "Leadership is deciding what NOT to do as much as what to do - focus is a strategy, not a side effect.",
    "Drucker's old line still holds: management is doing things right, leadership is doing the right things.",
    "The Art of War's advice on timing: know when to attack, and know when waiting IS the strategy.",
    "48 Laws of Power logic: keep others dependent on you, not the other way around - leverage comes from being needed.",
    "Real leadership shows up most clearly in how a team handles a bad week, not a good one.",
    "Sun Tzu: all warfare is based on deception - in business, that often just means not showing your full hand too early.",
    "One Greene principle worth remembering: win through actions, never through argument - results speak louder.",
    "Good businesses solve a problem; great ones make the problem disappear before customers notice it existed.",
    "The Art of War again: supreme excellence is breaking resistance without a fight - the cleanest wins avoid conflict altogether.",
    "48 Laws: always say less than necessary - the less you reveal, the more power you keep in a negotiation.",
    "Management tip as old as business itself: hire for trust, train for skill - skill is teachable, trust mostly isn't.",
    "Sun Tzu's view on competition: if you know yourself and your rival, the outcome is rarely a surprise.",
    "A Greene favorite: court attention at all costs - visibility, used wisely, compounds like interest.",
    "Leadership lesson: people don't remember your title, they remember how you made decisions under pressure.",
    "The Art of War reminds us speed matters - a mediocre plan executed fast often beats a perfect plan executed late.",
    "48 Laws: keep your allies close, but never fully owe anyone a favor you can't repay.",
    "Strategy, at its core, is just resource allocation - where you spend time and money says more than any mission statement.",
    "Sun Tzu's quiet point: the general who wins makes many calculations before battle, the one who loses makes few.",
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
        print(f"All '{key}' quotes used. Resetting this pool.")
        available = pool[:]
        used = set()
    choice = random.choice(available)
    used.add(choice)
    state[key] = list(used)
    return choice


def fetch_api_quote():
    if not API_NINJAS_KEY or FORCE_FALLBACK:
        return None
    try:
        category = random.choice(API_CATEGORIES)
        response = requests.get(
            API_NINJAS_URL,
            headers={"X-Api-Key": API_NINJAS_KEY},
            params={"category": category},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        if not data:
            return None
        item = data[0]
        quote = item.get("quote", "").strip()
        author = item.get("author", "").strip()
        if not quote:
            return None
        return f'"{quote}" - {author}' if author else f'"{quote}"'
    except Exception as e:
        print(f"API quote fetch failed, falling back to local pool: {e}")
        return None


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
    if not DRY_RUN and not all([SMSGATEWAY_LOGIN, SMSGATEWAY_PASSWORD, DAILY_QUOTE_RECIPIENT_NUMBER]):
        raise SystemExit(
            "Missing config. Set SMSGATEWAY_LOGIN, SMSGATEWAY_PASSWORD, and "
            "DAILY_QUOTE_RECIPIENT_NUMBER as environment variables."
        )

    numbers = [n.strip() for n in (DAILY_QUOTE_RECIPIENT_NUMBER or "").split(",") if n.strip()]
    if not numbers:
        print("No recipients configured.")
        return

    state = load_state()

    text = fetch_api_quote()
    if text:
        print("Using a fresh quote from the API.")
    else:
        print("Using the local curated pool.")
        text = pick_unused("business_quote_fallback", FALLBACK_QUOTES, state)

    send(numbers, text)
    save_state(state)


if __name__ == "__main__":
    send_message()
