"""
send_tech_news_sms.py

Sends a daily tech-news SMS built around a rotating theme - renewable
energy, BESS/energy storage, thermal, mechanical, electrical,
construction, data centers, disaster management, new tech - cycling
through all 9 automatically, one theme per day. For each day's theme it
pulls a couple of Philippines-specific headlines and a couple of global
headlines.

SOURCE: GNews (gnews.io) - a free news search API. Needs a free API key.

SETUP:
  1. Sign up free at https://gnews.io, get your API key from the
     dashboard, set it as the TECH_NEWS_API_KEY secret. Free tier gives
     100 requests/day, which is far more than this needs (a handful of
     calls once a day).
  2. Same SMSGATEWAY_LOGIN / SMSGATEWAY_PASSWORD secrets as the other
     scripts, plus its own TECH_NEWS_RECIPIENT_NUMBER secret.

Optional env vars for testing:
  TEST_DAY_INDEX=0-8   force a specific theme instead of the day-based one
  DRY_RUN=1            print instead of sending
"""

import os
from datetime import datetime, timedelta, timezone

import requests
from requests.auth import HTTPBasicAuth

SMSGATEWAY_LOGIN = os.environ.get("SMSGATEWAY_LOGIN")
SMSGATEWAY_PASSWORD = os.environ.get("SMSGATEWAY_PASSWORD")
TECH_NEWS_RECIPIENT_NUMBER = os.environ.get("TECH_NEWS_RECIPIENT_NUMBER")
TECH_NEWS_API_KEY = os.environ.get("TECH_NEWS_API_KEY", "").strip()

SMSGATEWAY_URL = "https://api.sms-gate.app/3rdparty/v1/messages"
GNEWS_SEARCH_URL = "https://gnews.io/api/v4/search"

DRY_RUN = os.environ.get("DRY_RUN", "").strip() == "1"
TEST_DAY_INDEX = os.environ.get("TEST_DAY_INDEX", "").strip()

# ---- The 9 rotating themes: (display name, search keywords) ----
THEMES = [
    ("Renewable Energy", "renewable energy"),
    ("BESS / Energy Storage", "battery energy storage system"),
    ("Thermal", "thermal power plant technology"),
    ("Mechanical", "mechanical engineering technology"),
    ("Electrical", "electrical engineering technology"),
    ("Construction", "construction technology infrastructure"),
    ("Data Centers", "data center technology"),
    ("Disaster Management", "disaster management technology"),
    ("New Tech", "new technology innovation"),
]


def today_in_manila():
    return datetime.now(timezone(timedelta(hours=8)))


def todays_theme():
    if TEST_DAY_INDEX:
        idx = int(TEST_DAY_INDEX) % len(THEMES)
    else:
        # Day-of-year cycles through all 9 themes continuously, repeating
        # roughly every 9 days, covering all topics evenly over time.
        idx = today_in_manila().timetuple().tm_yday % len(THEMES)
    return THEMES[idx]


def fetch_news(query, max_results=2):
    if not TECH_NEWS_API_KEY:
        return []
    try:
        response = requests.get(
            GNEWS_SEARCH_URL,
            params={
                "q": query,
                "lang": "en",
                "max": max_results,
                "sortby": "publishedAt",
                "token": TECH_NEWS_API_KEY,
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        articles = data.get("articles", [])
        return [(a.get("title", "").strip(), a.get("url", "").strip()) for a in articles if a.get("title")]
    except Exception as e:
        print(f"News fetch failed for query '{query}': {e}")
        return []


def build_message(theme_name, ph_articles, global_articles):
    lines = [f"Today's Tech Theme: {theme_name}"]
    for title, url in ph_articles:
        lines.append(f"(PH) {title} - {url}")
    for title, url in global_articles:
        lines.append(f"(Global) {title} - {url}")
    return "\n".join(lines)


def send(numbers, text):
    if DRY_RUN:
        print(f"[dry run] would send to {numbers}:\n{text}")
        return
    response = requests.post(
        SMSGATEWAY_URL,
        json={"textMessage": {"text": text}, "phoneNumbers": numbers},
        auth=HTTPBasicAuth(SMSGATEWAY_LOGIN, SMSGATEWAY_PASSWORD),
    )
    response.raise_for_status()
    print(f"Sent to {numbers}:\n{text}")


def send_message():
    if not DRY_RUN and not all([SMSGATEWAY_LOGIN, SMSGATEWAY_PASSWORD, TECH_NEWS_RECIPIENT_NUMBER]):
        raise SystemExit(
            "Missing config. Set SMSGATEWAY_LOGIN, SMSGATEWAY_PASSWORD, and "
            "TECH_NEWS_RECIPIENT_NUMBER as environment variables."
        )
    if not TECH_NEWS_API_KEY:
        print("No TECH_NEWS_API_KEY set, can't fetch live news. Skipping today. "
              "Sign up free at gnews.io to enable this.")
        return

    numbers = [n.strip() for n in (TECH_NEWS_RECIPIENT_NUMBER or "").split(",") if n.strip()]
    if not numbers:
        print("No recipients configured.")
        return

    theme_name, query = todays_theme()
    print(f"Today's theme: {theme_name} (query: '{query}')")

    ph_articles = fetch_news(f"{query} Philippines", max_results=2)
    global_articles = fetch_news(query, max_results=2)

    if not ph_articles and not global_articles:
        print("No articles found for today's theme. Skipping today.")
        return

    text = build_message(theme_name, ph_articles, global_articles)
    send(numbers, text)


if __name__ == "__main__":
    send_message()
