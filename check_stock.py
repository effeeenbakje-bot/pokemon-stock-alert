import os
import json
import requests
from bs4 import BeautifulSoup

STATE_FILE = ".stock_state.json"

PRODUCTS = [
    {
        "name": "Dreamland - First Partner - Illustration Collection",
        "url": "https://www.dreamland.nl/producten/pokemon-first-partner-illustration-collection/02356136",
    },
    {
        "name": "Dreamland - Ascended Heroes - Elite Trainer Box UK",
        "url": "https://www.dreamland.nl/producten/pokemon-me-2-5-ascended-heroes-elite-trainer-box-uk/02344089",
    },
    {
        "name": "Dreamland - Ultra Premium Collection Box - Mega Charizard X ex",
        "url": "https://www.dreamland.nl/producten/pokemon-ultra-premium-collection-box-mega-charizard-x-ex/02321486",
    },
    {
        "name": "pokecardshop.be - Booster Bundle - Ascended Heroes",
        "url": "https://www.vikado.nl/product/17196463/sleutelkast-met-specht-wildlife-garden",
    },
]

IN_STOCK_HINTS = [
    "op voorraad",
    "in winkelwagen",
    "direct leverbaar",
    "Add to Cart",
]

OUT_OF_STOCK_HINTS = [
    "tijdelijk niet leverbaar",
    "niet leverbaar",
    "uitverkocht",
    "online tijdelijk uitverkocht",
    "Out of Stock",
]

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


def detect_stock(html: str) -> tuple[str, str | None]:
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True).lower()

    for hint in OUT_OF_STOCK_HINTS:
        if hint in text:
            return "out_of_stock", hint

    for hint in IN_STOCK_HINTS:
        if hint in text:
            return "in_stock", hint

    return "unknown", None


def load_previous_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        return data

    return {}


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def main() -> None:
    state = load_previous_state()

    for product in PRODUCTS:
        name = product["name"]
        url = product["url"]

        try:
            html = fetch_html(url)
            current, matched_hint = detect_stock(html)
            previous = state.get(url)

            print(
                f"{name}: previous={previous} current={current} matched_hint={matched_hint}"
            )

            if current == "in_stock" and previous != "in_stock":
                send_telegram(
                    f"Voorraad-alert: mogelijk op voorraad\n"
                    f"Product: {name}\n"
                    f"Match: {matched_hint}\n"
                    f"{url}"
                )

            state[url] = current

        except Exception as e:
            print(f"Fout bij {name}: {e}")
            state[url] = "error"

    save_state(state)


if __name__ == "__main__":
    main()
