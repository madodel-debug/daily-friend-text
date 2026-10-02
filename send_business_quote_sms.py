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

    # ---- More 48 Laws of Power, each with a short illustrative example ----
    "48 Laws - Conceal your intentions: a company quietly bought up a rival's key suppliers before anyone knew an acquisition was coming, so no one could outbid them.",
    "48 Laws - Win through actions, not argument: instead of debating a skeptical client, a founder just shipped a working prototype and let the result make the case.",
    "48 Laws - Crush your enemy totally: a business that only half-solved a competitor's weakness watched that competitor come back stronger within a year.",
    "48 Laws - Use absence to raise your value: a sought-after consultant deliberately limited his availability, and both demand and his rates kept climbing.",
    "48 Laws - Enter with boldness: a job candidate who directly asked for the role they wanted, instead of hedging, got taken far more seriously than the cautious applicants.",
    "48 Laws - Know what truly motivates each person: a manager who learned one team member wanted recognition and another wanted autonomy got buy-in without forcing anything.",
    "48 Laws - Think freely, behave conventionally: a reformer who kept bold ideas private while following normal office norms avoided getting pushed out before real change was possible.",
    "48 Laws - Stay adaptable, assume no fixed shape: a company that kept reinventing its business model survived three industry shifts that wiped out more rigid competitors.",

    # ---- A few more Art of War ideas ----
    "Sun Tzu: appear weaker than you are when you're strong, and stronger than you are when you're weak - perception shapes what rivals choose to risk.",
    "The Art of War's core bet: the ultimate skill is winning without ever having to fight - conflict itself is often a sign the planning failed earlier.",
    "Sun Tzu again: opportunities multiply as they're seized - waiting for the perfect moment often means missing every workable one.",

    # ---- Made to Stick ----
    "Made to Stick's point: ideas spread when they're simple and concrete - a nutrition label works better than a lecture on calories.",
    "From Made to Stick: a surprising fact gets remembered longer than one that just confirms what people already believed.",
    "Made to Stick's lesson: one specific customer story often persuades more than a spreadsheet full of satisfaction scores.",

    # ---- Blue Ocean Strategy ----
    "Blue Ocean Strategy's idea: stop competing on the same features as everyone else, and build a market space rivals aren't even looking at.",
    "Blue Ocean's favorite example: Cirque du Soleil dropped animal acts and ticket-price wars entirely, and built an entirely new audience instead of fighting over the old one.",
    "Blue Ocean Strategy: value innovation means cutting costs and raising value at the same time, not treating them as a trade-off.",

    # ---- The Toyota Way ----
    "The Toyota Way: stop the line the moment a defect appears, instead of letting small problems pile up downstream into big ones.",
    "Toyota's principle: small, constant improvements beat one big redesign that nobody keeps maintaining afterward.",
    "The Toyota Way treats respect for people and continuous improvement as the same discipline, just aimed at different problems.",

    # ---- The 4-Hour Work Week ----
    "Ferriss's line from The 4-Hour Work Week: being busy is often just a form of laziness - lazy thinking and indiscriminate action.",
    "The 4-Hour Work Week's point: outsourcing the predictable parts of your work frees up time for the parts only you can actually do.",
    "Ferriss again: define what 'enough' looks like before chasing more - most people grow without ever picking a finish line.",

    # ---- Zero to One ----
    "Zero to One's core idea: going from 0 to 1 means building something genuinely new, not copying what already works - that's where real value gets created.",
    "Thiel's question from Zero to One: a startup's biggest risk isn't poor execution, it's never asking what's true that nobody else agrees with yet.",
    "Zero to One: competition erodes profit - a small monopoly in an overlooked niche usually beats a crowded, competitive market.",

    # ---- Atomic Habits ----
    "Atomic Habits' line: you don't rise to the level of your goals, you fall to the level of your systems - the habit matters more than the ambition.",
    "Atomic Habits: make good habits obvious and bad habits invisible - environment design beats willpower on most days.",
    "Atomic Habits' math: getting just 1% better each day compounds into a completely different trajectory a year later.",

    # ---- The Obstacle Is the Way ----
    "The Obstacle Is the Way's core line: the obstacle in the path becomes the path - what blocks you can become the way through, once you change how you see it.",
    "Holiday's Stoic point: you don't control events, only your response to them - that's the only lever that actually works.",

    # ---- Good to Great ----
    "Good to Great's warning: good is the enemy of great - most companies never become great because they settle for merely good.",
    "Good to Great's advice: get the right people on the bus before deciding where the bus is even going.",
    "Collins's hedgehog concept: find the one thing you can be best in the world at, and ignore everything adjacent to it.",

    # ---- Ready, Fire, Aim ----
    "Ready, Fire, Aim's lesson: most failed businesses didn't fail from a bad idea, they failed from overplanning before ever actually selling anything.",
    "Masterson's point in Ready, Fire, Aim: sell first and perfect later - the market tells you what to build better than any business plan does.",

    # ---- Traction (EOS) ----
    "Traction's rule: a business without a clear, ranked set of priorities drifts, even when everyone's individually working hard.",
    "Traction's point: fewer priorities, clearly ranked, beat a long list that everyone quietly ignores.",

    # ---- Awaken the Giant Within ----
    "Tony Robbins's line: the quality of your life is the quality of your decisions, made in a split second, usually under pressure.",
    "Awaken the Giant Within's idea: real change happens when the pain of staying the same finally outweighs the pain of changing.",

    # ---- Extreme Ownership ----
    "Extreme Ownership's central claim: there are no bad teams, only bad leaders - leaders own every outcome, good or bad, no exceptions.",
    "Willink and Babin's point: decentralized command only works when every person understands the mission well enough to make the call themselves.",
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
