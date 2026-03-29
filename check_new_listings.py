import os
import json
import requests
from playwright.sync_api import sync_playwright

STATE_FILE = ".pokemoncenter_listings.json"
CATEGORY_URL = "https://www.pokemoncenter.com/category/elite-trainer-box?sort=launch_date%2Bdesc"

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


def send_telegram(text: str) -> None:
    telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r = requests.post(
        telegram_url,
        json={"chat_id": CHAT_ID, "text": text},
        timeout=20,
    )
    r.raise_for_status()


def load_previous_items() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data if isinstance(data, dict) else {}


def save_items(items: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def scrape_items() -> dict:
    items = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 2000},
        )

        page = context.new_page()

        print("Opening Pokemon Center category page...")
        page.goto(CATEGORY_URL, wait_until="domcontentloaded", timeout=60000)
        print("Page opened, waiting 5 seconds for extra content...")
        page.wait_for_timeout(5000)

        links = page.locator("a")
        count = links.count()
        print(f"Found {count} links on the page")

        for i in range(count):
            try:
                link = links.nth(i)
                href = link.get_attribute("href")
                text = (link.inner_text() or "").strip()

                if not href or not text:
                    continue

                print(f"DEBUG LINK: {href} | TEXT: {text}")

                if href.startswith("/"):
                    href = f"https://www.pokemoncenter.com{href}"

                if "elite trainer box" not in text.lower():
                    continue

                items[href] = text

            except Exception:
                continue

        print(f"Collected {len(items)} matching product links")

        context.close()
        browser.close()

    return items


def main() -> None:
    previous_items = load_previous_items()
    current_items = scrape_items()

    print(f"previous_count={len(previous_items)} current_count={len(current_items)}")

    new_items = {
        url: name
        for url, name in current_items.items()
        if url not in previous_items
    }

    print(f"new_items_count={len(new_items)}")

    if previous_items and new_items:
        for url, name in new_items.items():
            send_telegram(
                f"Nieuwe listing gevonden op Pokemon Center\n"
                f"Naam: {name}\n"
                f"{url}"
            )

    save_items(current_items)


if __name__ == "__main__":
    main()
