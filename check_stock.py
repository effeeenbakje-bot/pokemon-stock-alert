import os
import json
import requests
from bs4 import BeautifulSoup

URL = "https://www.dreamland.nl/producten/pokemon-first-partner-illustration-collection/02356136"
STATE_FILE = ".stock_state.json"

IN_STOCK_HINTS = [
    "op voorraad",
    "in winkelwagen",
    "morgen in huis",
    "direct leverbaar",
]

OUT_OF_STOCK_HINTS = [
    "tijdelijk niet leverbaar",
    "niet leverbaar",
    "uitverkocht",
    "online tijdelijk uitverkocht",
]

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


def send_telegram(text: str) -> None:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r = requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=20)
    r.raise_for_status()


def fetch_html(url: str) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0 Safari/537.36"
        )
    }
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.text


def detect_stock(html: str) -> str:
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True).lower()

    if any(h in text for h in IN_STOCK_HINTS):
        return "in_stock"
    if any(h in text for h in OUT_OF_STOCK_HINTS):
        return "out_of_stock"
    return "unknown"


def load_previous_state() -> str | None:
    if not os.path.exists(STATE_FILE):
        return None
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("status")


def save_state(status: str) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"status": status}, f)


def main() -> None:
    current = detect_stock(fetch_html(URL))
    previous = load_previous_state()

    print(f"previous={previous} current={current}")

    if current == "in_stock" and previous != "in_stock":
        send_telegram(f"Voorraad-alert: mogelijk op voorraad\n{URL}")

    save_state(current)


if __name__ == "__main__":
    main()
