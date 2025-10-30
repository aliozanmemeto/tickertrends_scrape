# Scraping & Saving TickerTrends Data (JSON only)
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import Playwright, sync_playwright

from mainpage_tickertrends import MainPage
from loginpage_tickertrends import LoginPage
from homepage_tickertrends import HomePage
from exploding_trends_page import ExplodingTrendsPage



# Use this code snippet in your app.
# If you need more information about configurations
# or implementing the sample code, visit the AWS docs:
# https://aws.amazon.com/developer/language/python/

import boto3
from botocore.exceptions import ClientError
import io

def get_secret():

    secret_name = "tickertrends_login"
    region_name = "eu-north-1"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e

    secret = get_secret_value_response['SecretString']
    return json.loads(secret)
    # Your code goes here.



CATEGORIES = [
    "Arts & Culture","Automotive & Mobility","Business & Finance","Consumer Products",
    "E-commerce & Retail","Education & Learning","Entertainment","Fashion & Beauty",
    "Food & Beverage","Gaming & Virtual Worlds","Health & Wellness","Home & Living",
    "Politics & Government","Real Estate & Housing","Science & Innovation",
    "Social Media & Influencers","Sports","Technology","Travel & Hospitality",
]

MAX_PAGES = 11  # cap per category because of a personal account!
GRANULARITY = "Daily"  # only daily


# ---------- SCRAPING ----------
def scrape_tickertrends_daily(playwright: Playwright):
    """Scrapes TickerTrends 'Daily' granularity for all categories and returns a list of dicts."""
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    scrape_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")

    # --- Login & navigation ---
    page.goto("https://tickertrends.io/", wait_until="domcontentloaded", timeout=30_000)
    MainPage(page).prepare_and_open_login()

    login_page = LoginPage(page)
    login_page.open_email_login()
    tickertrends_credentials = get_secret()
    login_page.fill_username(tickertrends_credentials["tickertrends_email"])
    login_page.fill_password(tickertrends_credentials["tickertrends_password"])
    login_page.submit_login()

    page.wait_for_timeout(5_000)
    HomePage(page).open_exploding_trends()

    et = ExplodingTrendsPage(page)
    et.open_type_menu()
    et.select_source("Tiktok")
    et.choose_list_view()
    et.choose_time_granularity(GRANULARITY)

    all_rows = []

    for cat in CATEGORIES:
        logging.info(f"Scraping category: {cat}")
        try:
            et.choose_category(cat)
            page.wait_for_timeout(300)
            trends = et.extract_all_trends(max_pages=MAX_PAGES)
            et.choose_category(cat)  # unselect

            for t in trends:
                all_rows.append({
                    "scrape_time": scrape_time,
                    "granularity": GRANULARITY,
                    "category": cat,
                    "name": t.get("name", ""),
                    "sign": t.get("sign", ""),
                    "value": t.get("value", ""),
                    "raw_growth": t.get("raw_growth", ""),
                    "ticker_symbol": t.get("ticker_symbol", ""),
                    "ticker_percent": t.get("ticker_percent", "")
                })
            logging.info(f"  → Collected {len(trends)} rows for {cat}")
        except Exception as e:
            logging.warning(f"  ⚠️ Skipped {cat} due to error: {e}")

    browser.close()
    return all_rows


# ---------- MAIN ----------
def main(bucket_name: str):
    """Runs the scrape and saves a JSON file."""
    logger = logging.getLogger(__name__)

    with sync_playwright() as pw:
        data = scrape_tickertrends_daily(pw)

    if not data:
        logger.warning("No data collected — nothing to save.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"tickertrends_daily_{timestamp}.json"

    s3_prefix = "data/"

    s3_client = boto3.client("s3", region_name="eu-north-1")

    # convert data to JSON bytes
    json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")

    # upload
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=f"{s3_prefix}{filename}",
            Body=json_bytes,
            ContentType="application/json"
        )
        logger.info(f"✅ Uploaded {len(data)} records to s3://{bucket_name}/{s3_prefix}{filename}")
    except Exception as e:
        logger.error(f"❌ Failed to upload to S3: {e}")


# ---------- ENTRY POINT ----------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    main(bucket_name="")