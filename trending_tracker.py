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

def parse_google_trends_rss(url, wilayah, default_source, scraped_time):
    """Fungsi fleksibel untuk menarik Google Trends berdasarkan kode negara."""
    articles = []
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
                source_name = clean_text(source_el.text) if source_el is not None else default_source
            else:
                news_title, news_url, source_name = "-", "-", default_source

            articles.append({
                "Waktu Tarik": scraped_time,
                "Wilayah": wilayah,
                "Sumber": f"Google Trends ({source_name})",
                "Topik / Kata Kunci": keyword,
                "Volume Pencarian": traffic,
                "Judul Berita": news_title,
                "URL": news_url
            })
    except Exception as e:
        logging.error(f"Gagal mengambil Google Trends {wilayah}: {e}")

    return articles

def fetch_national_terpopuler(scraped_time):
    """Menarik berita terpopuler nasional (Kompas & Detik)."""
    articles = []
    
    # 1. Kompas Terpopuler
    try:
        resp = requests.get("https://indeks.kompas.com/terpopuler", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"].split("?")[0].strip()
            if "kompas.com/read/" in href:
                title = clean_text(a.get("title") or a.get_text())
                if len(title) >= 25 and not any(x in title.lower() for x in ["lihat foto", "baca juga", "artikel"]):
                    articles.append({
                        "Waktu Tarik": scraped_time,
                        "Wilayah": "Indonesia",
                        "Sumber": "Kompas.com Terpopuler",
                        "Topik / Kata Kunci": "Trending Nasional",
                        "Volume Pencarian": "Top Traffic",
                        "Judul Berita": title,
                        "URL": href
                    })
    except Exception as e:
        logging.error(f"Gagal Kompas: {e}")

    # 2. DetikHot Terpopuler
    try:
        resp = requests.get("https://hot.detik.com/terpopuler", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        for el in soup.find_all("a", attrs={"dtr-ttl": True}):
            title = clean_text(el.get("dtr-ttl", ""))
            link = el.get("href", "").strip()
            section = clean_text(el.get("dtr-evt", "")).lower()
            if "header" in section or "footer" in section or len(title) < 20:
                continue
            articles.append({
                "Waktu Tarik": scraped_time,
                "Wilayah": "Indonesia",
                "Sumber": "DetikHot Terpopuler",
                "Topik / Kata Kunci": "Trending Seleb",
                "Volume Pencarian": "Top Traffic",
                "Judul Berita": title,
                "URL": link
            })
    except Exception as e:
        logging.error(f"Gagal DetikHot: {e}")

    return articles

def run_trending():
    scraped_time = datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S")
    logging.info("Memulai penarikan berita trending...")
    
    all_data = []

    # 1. Tarik Data Indonesia (Google Trends ID + Portal Nasional)
    all_data.extend(parse_google_trends_rss("https://trends.google.com/trending/rss?geo=ID", "Indonesia", "Trends ID", scraped_time))
    all_data.extend(fetch_national_terpopuler(scraped_time))

    # 2. Tarik Data Internasional (Google Trends Global/US)
    all_data.extend(parse_google_trends_rss("https://trends.google.com/trending/rss?geo=US", "Internasional", "Trends Global", scraped_time))

    if not all_data:
        logging.warning("Data trending kosong.")
        return

    df_trending = pd.DataFrame(all_data).drop_duplicates(subset=["URL"])
    
    # Susunan kolom rapi
    kolom = ["Waktu Tarik", "Wilayah", "Sumber", "Topik / Kata Kunci", "Volume Pencarian", "Judul Berita", "URL"]
    df_trending = df_trending[kolom]
    
    df_trending.to_csv(CSV_TRENDING, index=False)
    logging.info(f"Berhasil memperbarui {len(df_trending)} data trending ke {CSV_TRENDING}.")

if __name__ == "__main__":
    run_trending()
