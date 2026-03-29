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


def extract_products_from_next_data(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")

    if not script or not script.string:
        print("Geen __NEXT_DATA__ script gevonden")
        return []

    try:
        data = json.loads(script.string)
    except Exception as e:
        print(f"Kon __NEXT_DATA__ niet parsen: {e}")
        return []

    products = (
        data.get("props", {})
        .get("initialState", {})
        .get("search", {})
        .get("results", {})
        .get("products", [])
    )

    if not isinstance(products, list):
        print("Products pad gevonden, maar het is geen lijst")
        return []

    return products


def build_product_url(product: dict) -> str:
    code = product.get("code", "").strip()
    seo_name = product.get("seoName", "").strip()
    url = product.get("url", "").strip()

    if url:
        if url.startswith("/"):
            return f"https://www.pokemoncenter.com{url}"
        return url

    if code and seo_name:
        return f"https://www.pokemoncenter.com/product/{code}/{seo_name}"

    if code:
        return f"https://www.pokemoncenter.com/product/{code}"

    return ""


def scrape_items() -> dict:
    print("Fetching Pokemon Center category page via requests...")
    html = fetch_html(CATEGORY_URL)
    print(f"Downloaded {len(html)} characters of HTML")

    products = extract_products_from_next_data(html)
    print(f"Found {len(products)} products in __NEXT_DATA__")

    items = {}

    for product in products:
        name = (product.get("name") or "").strip()
        code = (product.get("code") or "").strip()
        out_of_stock = product.get("outOfStock")
        url = build_product_url(product)

        if not name or not code:
            continue

        if "elite trainer box" not in name.lower():
            continue

        items[code] = {
            "name": name,
            "url": url,
            "code": code,
            "out_of_stock": out_of_stock,
        }

    print(f"Collected {len(items)} matching ETB products")

    for code, item in items.items():
        print(
            f"MATCH: code={code} | name={item['name']} | "
            f"out_of_stock={item['out_of_stock']} | url={item['url']}"
        )

    return items


def main() -> None:
    previous_items = load_previous_items()
    current_items = scrape_items()

    print(f"previous_count={len(previous_items)} current_count={len(current_items)}")

    new_items = {
        code: item
        for code, item in current_items.items()
        if code not in previous_items
    }

    print(f"new_items_count={len(new_items)}")

    if previous_items and new_items:
        for code, item in new_items.items():
            send_telegram(
                f"Nieuwe listing gevonden op Pokemon Center\n"
                f"Naam: {item['name']}\n"
                f"Code: {code}\n"
                f"Uitverkocht: {item['out_of_stock']}\n"
                f"{item['url']}"
            )

    save_items(current_items)


if __name__ == "__main__":
    main()
