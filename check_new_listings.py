import os
import json
import requests
from bs4 import BeautifulSoup

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


def fetch_html(url: str) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.pokemoncenter.com/",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.text


def scrape_items() -> dict:
    items = {}

    print("Fetching Pokemon Center category page via requests...")
    html = fetch_html(CATEGORY_URL)
    print(f"Downloaded {len(html)} characters of HTML")

    soup = BeautifulSoup(html, "html.parser")
    links = soup.find_all("a")
    print(f"Found {len(links)} links in HTML")

    for link in links:
        href = link.get("href")
        text = link.get_text(" ", strip=True)

        if not href or not text:
            continue

        text_l = text.lower()

        if "elite trainer box" not in text_l:
            continue

        if "/product/" not in href:
            continue

        if href.startswith("/"):
            href = f"https://www.pokemoncenter.com{href}"

        items[href] = text

    print(f"Collected {len(items)} matching product links")

    for url, name in items.items():
        print(f"MATCH: {name} | {url}")

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
