import os
import sys
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BASE_URL = "https://secondhand.mk"
COLLECTION_URL = f"{BASE_URL}/collections/najnovi"
STATE_FILE = "last_shoe.txt"

# Ordered list of selector strategies — tried in sequence until one matches
TITLE_SELECTORS = [
    ".grid-product__title",
    ".grid-view-item__title",
    ".product-card__title",
    ".card__heading a",
    ".card__heading",
    "h3.grid-product__title",
]
LINK_SELECTORS = [
    ".grid-product__link",
    ".grid-view-item__link",
    ".product-card__link",
    "a.card__heading",
    "a[href*='/products/']",
]
PRICE_SELECTORS = [
    ".grid-product__price",
    ".grid-product__price--current",
    ".price__regular .price-item",
    ".product-card__price",
    ".price",
]


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


def find_first_match(page, selectors):
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0:
                return sel, loc
        except Exception:
            continue
    return None, None


def scrape_first_product(page):
    page.goto(COLLECTION_URL, wait_until="networkidle", timeout=30000)

    print(f"Page title: {page.title()}")
    print(f"Page URL: {page.url}")

    # Detect Cloudflare challenge page
    if "just a moment" in page.title().lower() or "cloudflare" in page.title().lower():
        raise RuntimeError("Blocked by Cloudflare challenge page")

    # Wait a moment for JS-rendered content
    page.wait_for_timeout(3000)

    # Find working title selector
    title_sel, _ = find_first_match(page, TITLE_SELECTORS)
    link_sel, _ = find_first_match(page, LINK_SELECTORS)
    price_sel, _ = find_first_match(page, PRICE_SELECTORS)

    print(f"Selectors found — title: {title_sel} | link: {link_sel} | price: {price_sel}")

    if not title_sel or not link_sel:
        # Print a snippet of the page HTML to help diagnose selector mismatches
        body_snippet = page.locator("body").inner_html()[:2000]
        print("--- PAGE HTML SNIPPET ---")
        print(body_snippet)
        print("--- END SNIPPET ---")
        raise RuntimeError("Could not find product title/link selector on the page")

    title = page.locator(title_sel).first.inner_text().strip()
    product_path = page.locator(link_sel).first.get_attribute("href")

    price = "N/A"
    if price_sel:
        try:
            price = " ".join(page.locator(price_sel).first.inner_text().split()).strip()
        except Exception:
            pass

    return title, price, product_path


def main():
    last_url = load_last_state()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="en-US",
        )
        page = context.new_page()

        try:
            title, price, product_path = scrape_first_product(page)
        except PlaywrightTimeoutError:
            print("ERROR: Timed out loading the page", file=sys.stderr)
            browser.close()
            sys.exit(1)
        except RuntimeError as e:
            print(f"ERROR: {e}", file=sys.stderr)
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
