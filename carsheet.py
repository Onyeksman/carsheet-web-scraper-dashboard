import requests
import pandas as pd
from bs4 import BeautifulSoup
from io import StringIO
import time
import random
from datetime import datetime

# -----------------------
# Configuration
# -----------------------
BASE_URL = "https://carsheet.io/aston-martin,audi,bentley,bmw,ferrari,ford,mercedes-benz/2024/2-door/"
OUTPUT_FILE = f"carsheet_data_{datetime.now():%Y%m%d_%H%M}.xlsx"

# -----------------------
# Scraper Function
# -----------------------
def scrape_all_pages():
    session = requests.Session()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }

    all_dfs = []
    page_num = 1

    while True:
        print(f"🔎 Scraping page {page_num} ...")

        try:
            resp = session.get(BASE_URL, params={"page": page_num}, headers=headers, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"❌ Error fetching page {page_num}: {e}")
            break

        soup = BeautifulSoup(resp.text, "html.parser")

        # ✅ Future-proof: wrap HTML string with StringIO
        tables = pd.read_html(StringIO(resp.text))

        if not tables or tables[0].empty:
            print("⚠️ No tables found, stopping.")
            break

        df = tables[0]
        df.columns = [str(c).strip() for c in df.columns]
        all_dfs.append(df)

        # Check pagination
        next_btn = soup.select_one("li.paginate_button.page-item.next")
        if not next_btn or "disabled" in next_btn.get("class", []):
            print("✅ Last page reached.")
            break

        page_num += 1
        time.sleep(random.uniform(1, 3))  # polite delay between pages

    if not all_dfs:
        print("❌ No data scraped.")
        return

    # Combine and clean data
    final_df = pd.concat(all_dfs, ignore_index=True)
    final_df.drop_duplicates(inplace=True)
    final_df.dropna(how="all", inplace=True)

    # Export to Excel
    final_df.to_excel(OUTPUT_FILE, index=False)
    print(f"\n🎉 Done! Scraped {len(final_df)} rows across {page_num} pages → saved to {OUTPUT_FILE}")

# -----------------------
# Entry Point
# -----------------------
if __name__ == "__main__":
    scrape_all_pages()
