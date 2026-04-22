import os
import sys
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BASE_URL = "https://secondhand.mk"
COLLECTION_URL = f"{BASE_URL}/collections/najnovi"
STATE_FILE = "last_shoe.txt"


def send_telegram(message):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("ERROR: TELEGRAM_TOKEN or TELEGRAM_CHAT_ID not set", file=sys.stderr)
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=10)
    resp.raise_for_status()


def load_last_state():
    try:
        with open(STATE_FILE, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""


def save_state(product_url):
    with open(STATE_FILE, "w") as f:
        f.write(product_url)


def scrape_first_product(page):
    page.goto(COLLECTION_URL, wait_until="domcontentloaded")
    page.wait_for_selector(".grid-product__title", timeout=15000)

    first_card = page.locator(".grid-product__link").first
    product_path = first_card.get_attribute("href")

    title = page.locator(".grid-product__title").first.inner_text().strip()

    try:
        price = page.locator(".grid-product__price").first.inner_text().strip()
        # Collapse whitespace / newlines that Shopify price blocks sometimes contain
        price = " ".join(price.split())
    except Exception:
        price = "N/A"

    return title, price, product_path


def main():
    last_url = load_last_state()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            title, price, product_path = scrape_first_product(page)
        except PlaywrightTimeoutError:
            print("ERROR: Timed out waiting for product grid", file=sys.stderr)
            browser.close()
            sys.exit(1)
        finally:
            browser.close()

    print(f"First product: {title} | {price} | {product_path}")

    if product_path != last_url:
        full_link = f"{BASE_URL}{product_path}"
        message = (
            f"New listing on secondhand.mk!\n\n"
            f"{title}\n"
            f"Price: {price}\n"
            f"Link: {full_link}"
        )
        send_telegram(message)
        save_state(product_path)
        print("Notification sent and state updated.")
    else:
        print("No new listing detected.")


if __name__ == "__main__":
    main()
