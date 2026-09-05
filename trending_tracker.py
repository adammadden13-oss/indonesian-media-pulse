import os
import re
import logging
from datetime import datetime, timezone, timedelta
import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup
import pandas as pd

logging.basicConfig(
    filename="scraper.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

CSV_TRENDING = "berita_trending.csv"
WIB = timezone(timedelta(hours=7))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def clean_text(text):
    if not text:
        return ""
    return " ".join(text.split())

def fetch_google_trends_id():
    """Mengambil 20 topik pencarian paling trending di Indonesia dari Google Trends RSS."""
    url = "https://trends.google.com/trending/rss?geo=ID"
    articles = []
    scraped_time = datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)

        for item in root.findall('./channel/item'):
            keyword = clean_text(item.find('title').text) if item.find('title') is not None else "-"
            
            traffic_el = item.find('{https://trends.google.com/trending/rss}approx_traffic')
            traffic = clean_text(traffic_el.text) if traffic_el is not None else "-"
            
            news_item = item.find('{https://trends.google.com/trending/rss}news_item')
            if news_item is not None:
                title_el = news_item.find('{https://trends.google.com/trending/rss}news_item_title')
                url_el = news_item.find('{https://trends.google.com/trending/rss}news_item_url')
                source_el = news_item.find('{https://trends.google.com/trending/rss}news_item_source')

                news_title = clean_text(title_el.text) if title_el is not None else "-"
                news_url = url_el.text.strip() if url_el is not None else "-"
                source_name = clean_text(source_el.text) if source_el is not None else "Google Trends"
            else:
                news_title, news_url, source_name = "-", "-", "Google Trends"

            articles.append({
                "Waktu Tarik": scraped_time,
                "Sumber": f"Google Trends ({source_name})",
                "Topik / Kata Kunci": keyword,
                "Volume Pencarian": traffic,
                "Judul Berita": news_title,
                "URL": news_url
            })
    except Exception as e:
        logging.error(f"Gagal mengambil Google Trends: {e}")

    return articles

def fetch_detik_terpopuler():
    """Mengambil berita terpopuler dari DetikHot Celebs."""
    url = "https://hot.detik.com/terpopuler"
    articles = []
    scraped_time = datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for el in soup.find_all("a", attrs={"dtr-ttl": True}):
            title = clean_text(el.get("dtr-ttl", ""))
            link = el.get("href", "").strip()
            section = clean_text(el.get("dtr-evt", "")).lower()

            if "header" in section or "footer" in section or len(title) < 20:
                continue

            articles.append({
                "Waktu Tarik": scraped_time,
                "Sumber": "DetikHot Terpopuler",
                "Topik / Kata Kunci": "Most Read / Trending",
                "Volume Pencarian": "Top Traffic",
                "Judul Berita": title,
                "URL": link
            })
    except Exception as e:
        logging.error(f"Gagal mengambil Detik Terpopuler: {e}")

    return articles

def run_trending():
    logging.info("Memulai penarikan berita trending...")
    data = []
    data.extend(fetch_google_trends_id())
    data.extend(fetch_detik_terpopuler())

    if not data:
        logging.warning("Data trending kosong.")
        return

    df_trending = pd.DataFrame(data).drop_duplicates(subset=["URL"])
    
    # Simpan/tulis ulang agar selalu memuat daftar trending terkini yang segar
    df_trending.to_csv(CSV_TRENDING, index=False)
    logging.info(f"Berhasil menyimpan {len(df_trending)} topik trending ke {CSV_TRENDING}.")

if __name__ == "__main__":
    run_trending()
