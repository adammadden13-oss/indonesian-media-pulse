import os
import logging
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import pandas as pd
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logging.basicConfig(
    filename="scraper.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

CSV_FILE = "wolipop_news_feed.csv"
TARGET_URL = "https://wolipop.detik.com"

def get_session():
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session

def fetch_latest_articles():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    session = get_session()
    
    try:
        response = session.get(TARGET_URL, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        logging.error(f"Gagal mengambil data web: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    articles = []
    scraped_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    elements = soup.find_all("a", attrs={"dtr-ttl": True})
    for el in elements:
        title = el.get("dtr-ttl", "").strip()
        link = el.get("href", "").strip()
        section = el.get("dtr-evt", "").strip()
        article_id = el.get("dtr-id", "").strip()

        img_tag = el.find("img")
        img_url = ""
        if img_tag:
            img_url = img_tag.get("data-src") or img_tag.get("src", "")

        if title and link:
            articles.append({
                "article_id": article_id,
                "section": section,
                "title": title,
                "url": link,
                "image_url": img_url,
                "scraped_at": scraped_time
            })

    return articles

def run_job():
    logging.info("Proses scraping dimulai...")
    new_data = fetch_latest_articles()
    
    if not new_data:
        logging.warning("Tidak ada berita yang ditemukan.")
        return

    df_new = pd.DataFrame(new_data).drop_duplicates(subset=["url"])

    if os.path.exists(CSV_FILE):
        df_existing = pd.read_csv(CSV_FILE)
        existing_ids = set(df_existing["article_id"].dropna().astype(str))
        df_to_save = df_new[~df_new["article_id"].astype(str).isin(existing_ids)]
        
        if not df_to_save.empty:
            df_to_save.to_csv(CSV_FILE, mode="a", header=False, index=False)
            logging.info(f"Menambahkan {len(df_to_save)} berita baru.")
        else:
            logging.info("Tidak ada berita baru.")
    else:
        df_new.to_csv(CSV_FILE, index=False)
        logging.info(f"File CSV dibuat dengan {len(df_new)} berita.")

if __name__ == "__main__":
    run_job()
