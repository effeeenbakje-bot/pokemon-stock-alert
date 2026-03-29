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


def build_product_url(product: dict) -> str:
    code = (product.get("code") or "").strip()
    seo_name = (product.get("seoName") or "").strip()
    url = (product.get("url") or "").strip()

    if url:
        if url.startswith("/"):
            return f"https://www.pokemoncenter.com{url}"
        return url

    if code and seo_name:
        return f"https://www.pokemoncenter.com/product/{code}/{seo_name}"

    if code:
        return f"https://www.pokemoncenter.com/product/{code}"

    return ""


def fetch_next_data_with_playwright() -> dict:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 2000},
            locale="en-US",
        )

        page = context.new_page()

        print("Opening Pokemon Center category page with Playwright...")
        page.goto(CATEGORY_URL, wait_until="domcontentloaded", timeout=60000)

        print("Waiting for __NEXT_DATA__...")
        page.wait_for_selector("#__NEXT_DATA__", state="attached", timeout=15000)

        next_data_text = page.locator("#__NEXT_DATA__").inner_text()
        print(f"Read __NEXT_DATA__ with {len(next_data_text)} characters")

        context.close()
        browser.close()

    return json.loads(next_data_text)


def extract_products_from_next_data(data: dict) -> list[dict]:
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


def scrape_items() -> dict:
    data = fetch_next_data_with_playwright()
    products = extract_products_from_next_data(data)

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
