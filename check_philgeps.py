"""
check_philgeps.py

Checks PhilGEPS (the Philippine government procurement portal) for NEW
bid notices related to renewable energy, disaster management/DRRM, and
data centers/data storage, and sends a Telegram digest of anything new.

HOW IT WORKS:
PhilGEPS has no official public search API, so this uses the "PhilGEPS
Bid Notice Scraper" actor on Apify (a scraping-as-a-service platform) -
a maintained third-party tool that scrapes the public Bulletin Board and
returns clean JSON, including keyword filtering.

IMPORTANT - THIS NEEDS A LIVE TEST BEFORE TRUSTING IT:
Apify actor field names can change, and I can't call this API from where
I'm building this (no live internet access in my build environment), so
I could not verify the exact JSON field names in this actor's output.
Run this once manually with DRY_RUN=1 first, read the printed raw output
of the first item, and tell me if the field names need adjusting - the
code below tries several common field name variants defensively, but a
real test run is the only way to confirm it's reading the right fields.

SETUP:
  1. Sign up free at https://apify.com, go to Settings -> Integrations,
     copy your API token, set it as the APIFY_API_TOKEN secret.
  2. Apify's free tier includes monthly platform credits; a small daily
     scrape like this should comfortably fit within it, but keep an eye
     on usage in your Apify dashboard the first week.
  3. Same TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID secrets as your existing
     Telegram bot - this reuses it rather than needing a new bot.

Optional env vars for testing:
  DRY_RUN=1   print instead of sending, and print the FIRST raw item
              from each category so field names can be verified
"""

import json
import os
import requests

APIFY_API_TOKEN = os.environ.get("APIFY_API_TOKEN", "").strip()
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

DRY_RUN = os.environ.get("DRY_RUN", "").strip() == "1"

STATE_FILE = os.environ.get("STATE_FILE", "sent_state.json")
SEEN_KEY = "philgeps_seen"
MAX_SEEN_STORED = 500  # cap how many old reference numbers we remember

# The Apify actor that does the actual scraping of philgeps.gov.ph.
APIFY_ACTOR = "keyless_gardener~philgeps-bid-scraper"
APIFY_RUN_URL = f"https://api.apify.com/v2/acts/{APIFY_ACTOR}/run-sync-get-dataset-items"

# One Apify call per category, so results stay organized and each call
# stays small (cheaper, faster, easier to debug).
CATEGORIES = {
    "Renewable Energy": "renewable energy, solar power, battery energy storage, BESS, wind power",
    "Disaster Management": "disaster risk reduction, disaster management, flood control, emergency response, DRRM",
    "Data Centers / Storage": "data center, data storage, ICT infrastructure, cloud infrastructure",
}

MAX_ITEMS_PER_CATEGORY = 20


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


def fetch_category(keywords):
    if not APIFY_API_TOKEN:
        return []
    try:
        response = requests.post(
            APIFY_RUN_URL,
            params={"token": APIFY_API_TOKEN},
            json={
                "keywords": keywords,
                "maxItems": MAX_ITEMS_PER_CATEGORY,
            },
            timeout=120,  # scraping can take a while
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Apify fetch failed for keywords '{keywords}': {e}")
        return []


def extract_fields(item):
    """Try several likely field name variants, since the exact schema
    wasn't verified live. Adjust these fallbacks once you've seen a real
    response (run with DRY_RUN=1 and read the printed raw item)."""
    title = item.get("title") or item.get("name") or item.get("tenderTitle") or "(no title)"
    agency = item.get("agency") or item.get("organization") or item.get("procuringEntity") or ""
    budget = item.get("budget") or item.get("approvedBudget") or item.get("abc") or ""
    deadline = item.get("deadline") or item.get("closingDate") or item.get("closingDateTime") or ""
    url = item.get("url") or item.get("sourceUrl") or item.get("link") or ""
    reference = item.get("referenceNumber") or item.get("reference") or item.get("id") or url or title
    return {
        "title": title,
        "agency": agency,
        "budget": budget,
        "deadline": deadline,
        "url": url,
        "reference": str(reference),
    }


def send_telegram(text):
    if DRY_RUN:
        print(f"[dry run] would send to Telegram:\n{text}\n")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    response = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text})
    response.raise_for_status()
    print("Sent Telegram digest.")


def main():
    if not DRY_RUN and not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
        raise SystemExit("Missing config. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.")
    if not APIFY_API_TOKEN:
        print("No APIFY_API_TOKEN set. Sign up free at apify.com to enable this. Skipping.")
        return

    state = load_state()
    seen = set(state.get(SEEN_KEY, []))

    any_new = False
    message_parts = []

    for category_name, keywords in CATEGORIES.items():
        raw_items = fetch_category(keywords)
        if DRY_RUN and raw_items:
            print(f"--- Raw first item for '{category_name}' (for field-name verification) ---")
            print(json.dumps(raw_items[0], indent=2)[:1500])
            print("---")

        new_items = []
        for raw in raw_items:
            parsed = extract_fields(raw)
            if parsed["reference"] not in seen:
                new_items.append(parsed)
                seen.add(parsed["reference"])

        if new_items:
            any_new = True
            message_parts.append(f"\n{category_name} ({len(new_items)} new):")
            for it in new_items:
                line = f"- {it['title']}"
                if it["agency"]:
                    line += f" | {it['agency']}"
                if it["budget"]:
                    line += f" | Budget: {it['budget']}"
                if it["deadline"]:
                    line += f" | Deadline: {it['deadline']}"
                if it["url"]:
                    line += f"\n  {it['url']}"
                message_parts.append(line)
        else:
            print(f"No new items for '{category_name}'.")

    # Keep the seen-list from growing forever
    seen_list = list(seen)[-MAX_SEEN_STORED:]
    state[SEEN_KEY] = seen_list
    save_state(state)

    if not any_new:
        print("No new PhilGEPS notices across any category today.")
        return

    text = "PhilGEPS - New Bid Notices Today:" + "".join(message_parts)
    send_telegram(text)


if __name__ == "__main__":
    main()
