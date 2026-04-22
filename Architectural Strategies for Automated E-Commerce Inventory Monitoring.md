# Architectural Strategies for Automated E-Commerce Inventory Monitoring

## Overview

To monitor https://secondhand.mk/collections/najnovi for new sneaker listings without incurring any monthly server costs, you need a streamlined, serverless architecture. Because the site utilizes Cloudflare to block standard automated requests, basic web scraping tools will be blocked.1

The most reliable, 100% free solution involves combining three technologies: **Telegram** (for instant push notifications), **Python with Playwright** (to bypass security checks), and **GitHub Actions** (for continuous cloud automation).

## 1. The Notification Pipeline (Telegram)

Telegram provides a highly developer-friendly API for push notifications straight to your mobile device, completely free of charge.

**Create a Bot:** Open the Telegram app, search for the official @BotFather account, and send the /newbot command.2 Follow the prompts to name your bot. You will receive an **API Token**.

**Get Your Chat ID:** Start a conversation with your new bot and send it a simple text message. Then, visit https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates in your browser to locate your specific numeric chat_id.2

## 2. The Extraction Engine (Python & Playwright)

Playwright is a browser automation framework. Instead of sending a simple code request (which Cloudflare blocks), Playwright opens a hidden ("headless") Chromium browser. This simulates a real human visiting the newest products page.4

The following Python script navigates to the target URL, extracts the title of the very first product on the page 5, compares it to the last item it saw, and sends a Telegram message if it is a new addition:

```python
import os
import requests
from playwright.sync_api import sync_playwright

def send_telegram(message):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": message})

with sync_playwright() as p:
    # Launch a headless browser to bypass basic bot protection
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://secondhand.mk/collections/najnovi")
    
    # Wait for the product grid to load
    page.wait_for_selector('.grid-product__title', timeout=10000)

    # Extract the title of the newest product
    first_product = page.locator('.grid-product__title').first.inner_text()

    # Load the state of the last seen product
    try:
        with open("last_shoe.txt", "r") as f:
            last_shoe = f.read().strip()
    except FileNotFoundError:
        last_shoe = ""

    # If the product is new, trigger notification and update state
    if first_product!= last_shoe:
        send_telegram(f"New item detected: {first_product}\nLink: https://secondhand.mk/collections/najnovi")
        
        with open("last_shoe.txt", "w") as f:
            f.write(first_product)

    browser.close()
```

## 3. Serverless Automation (GitHub Actions)

To run this script automatically without paying for a server, you can use GitHub Actions, which provides free virtual machines for public repositories.6

**Secure Your Credentials:** Never put your Telegram API keys directly in the code. Instead, store them securely in your GitHub repository by navigating to **Settings > Secrets and variables > Actions** and adding TELEGRAM_TOKEN and TELEGRAM_CHAT_ID as Repository Secrets.8

**Create the Workflow:** Inside your repository, create a folder structure .github/workflows/ and add a file named monitor.yml.

This YAML configuration tells GitHub's servers to run your Python script exactly every 10 minutes using a cron schedule 6:

```yaml
name: Sneaker Monitor
on:
  schedule:
    - cron: '*/10 * * * *'
  workflow_dispatch:

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
          
      - name: Install dependencies
        run: |
          pip install playwright requests
          playwright install chromium
          
      - name: Run Scraper
        env:
          TELEGRAM_TOKEN: ${{ secrets.TELEGRAM_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python scraper.py
        
      - name: Save State via Git Scraping
        run: |
          git config user.name "GitHub Action Bot"
          git config user.email "bot@example.com"
          git add last_shoe.txt
          git commit -m "Update last seen shoe" |

| exit 0
          git push
```

## 4. State Persistence (Git Scraping)

Because GitHub Actions provides a brand-new virtual machine every time the script runs, it will normally forget what the "last shoe" was. To solve this without needing a database, the workflow utilizes a technique called "Git Scraping".9

The final step in the YAML file instructs the bot to save the last_shoe.txt file and commit it directly back to your GitHub repository.10 When the script runs 10 minutes later, it downloads this file, remembering the last product it saw, and preventing you from receiving duplicate notifications.

#### Works cited

How to Bypass Cloudflare in 2026: Top Methods & Scripts - Bright Data, accessed April 15, 2026, 

How to send notifications to Telegram with Python | by Andrei Kushniarou - Medium, accessed April 15, 2026, 

Telegram Notify · Actions · GitHub Marketplace, accessed April 15, 2026, 

Bypass Cloudflare with Puppeteer (2025 Guide) – Scrape Protected Sites - Browserless, accessed April 15, 2026, 

НАЈНОВИ – Secondhand MK, accessed April 22, 2026, 

Run Python Scripts for Free with GitHub Actions: A Complete Guide - David Muraya, accessed April 15, 2026, 

Web Scraping Automation: How to Run Scrapers on a Schedule - Firecrawl, accessed April 15, 2026, 

Storing your secrets safely - GitHub Docs, accessed April 15, 2026, 

Flat Data GitHub Action - Marketplace, accessed April 15, 2026, 

Running scrapers on GitHub to simplify your workflow - Features - Source: An OpenNews project, accessed April 15, 2026,
