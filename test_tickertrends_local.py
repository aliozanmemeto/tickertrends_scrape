# Scraping & Saving TickerTrends Data (per-category JSON → S3)
import json
import logging
import re
import gc
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import Playwright, sync_playwright

from mainpage_tickertrends import MainPage
from loginpage_tickertrends import LoginPage
from homepage_tickertrends import HomePage
from exploding_trends_page import ExplodingTrendsPage

# ---------- Config ----------
CATEGORIES = [
    "Consumer Products", "Arts & Culture","Automotive & Mobility","Business & Finance",
    "E-commerce & Retail","Education & Learning","Entertainment","Fashion & Beauty",
    "Food & Beverage","Gaming & Virtual Worlds","Health & Wellness","Home & Living",
    "Politics & Government","Real Estate & Housing","Science & Innovation",
    "Social Media & Influencers","Sports","Technology","Travel & Hospitality",
]
MAX_PAGES = 11
GRANULARITY = "Daily"
S3_REGION = "eu-north-1"
S3_PREFIX = "data/"  # S3 folder prefix (= "directory")

def _slug(s: str) -> str:
    # keep hyphens between words, replace everything else with '-'
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

# ---------- Scrape ----------
def scrape_tickertrends_daily(playwright: Playwright, bucket_name: str):
    """Scrape each category and upload one JSON per category to S3."""
    if not bucket_name:
        raise ValueError("bucket_name must be provided")


    browser = playwright.chromium.launch(headless=False,
                                         args=[
                                             "--disable-dev-shm-usage",  # important on small Linux instances
                                         ],
                                         )
    context = browser.new_context()
    page = context.new_page()

    # one run timestamp used across all category files
    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    scrape_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")

    # --- Login & navigation ---
    page.goto("https://tickertrends.io/", wait_until="domcontentloaded", timeout=30_000)
    MainPage(page).prepare_and_open_login()

    login_page = LoginPage(page)
    login_page.open_email_login()
    login_page.fill_username("")
    login_page.fill_password("")
    login_page.submit_login()

    page.wait_for_timeout(6_000)
    HomePage(page).open_exploding_trends()

    et = ExplodingTrendsPage(page)
    et.choose_data_type("Tiktok")
    et.choose_view("List View")
    et.choose_time_granularity(GRANULARITY)

    for cat in CATEGORIES:
        logging.info(f"Scraping category: {cat}")
        try:
            page.wait_for_timeout(6_000)
            et.choose_category(cat)
            print(f"Cat chosen")
            page.wait_for_timeout(300)

            trends = et.extract_all_trends(max_pages=MAX_PAGES)
            et.choose_category(cat)
            # build per-category rows
            rows = [{
                "scrape_time": scrape_time,
                "granularity": GRANULARITY,
                "category": cat,
                "name": t.get("name", ""),
                "sign": t.get("sign", ""),
                "value": t.get("value", ""),
                "raw_growth": t.get("raw_growth", ""),
                "ticker_symbol": t.get("ticker_symbol", ""),
                "ticker_percent": t.get("ticker_percent", "")
            } for t in trends]

            # filename format: tickertrends_daily_<category>_<timestamp>.json
            key = f"{S3_PREFIX}tickertrends_daily_{_slug(cat)}_{run_ts}.json"


        except Exception as e:
            logging.warning(f"⚠️ Skipped '{cat}' due to error: {e}")
        finally:
            # free memory between categories
            try: del rows
            except Exception: pass
            try: del trends
            except Exception: pass
            gc.collect()

    browser.close()

# ---------- Main ----------
def main(bucket_name: str):
    with sync_playwright() as pw:
        scrape_tickertrends_daily(pw, bucket_name=bucket_name)

# ---------- Entry ----------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    # 👇 pass your bucket name here
    main(bucket_name="")
