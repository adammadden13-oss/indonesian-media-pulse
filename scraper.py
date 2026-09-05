import os
import re
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

# Daftar target website yang dipantau
TARGETS = [
    {"source": "Wolipop", "url": "https://wolipop.detik.com", "parser": "detik"},
    {"source": "DetikHot Celebs", "url": "https://hot.detik.com/celebs", "parser": "detik"},
    {"source": "Grid.ID", "url": "https://www.grid.id", "parser": "grid"},
    {"source": "Okezone Celebrity", "url": "https://celebrity.okezone.com", "parser": "okezone"},
    {"source": "TribunTrends Infotainment", "url": "https://trends.tribunnews.com/infotainment", "parser": "tribun"}
]

def get_session():
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session

def parse_detik(soup, source_name):
    articles = []
    for el in soup.find_all("a", attrs={"dtr-ttl": True}):
        title = el.get("dtr-ttl", "").strip()
        link = el.get("href", "").strip()
        section = el.get("dtr-evt", "").strip().lower()
        article_id = el.get("dtr-id", "").strip()

        # Filter header/footer dan pastikan ID berupa angka
        if "header" in section or "footer" in section:
            continue
        if not article_id.isdigit():
            m = re.search(r'/d-(\d+)/', link)
            if m:
                article_id = m.group(1)
            else:
                continue

        img_tag = el.find("img")
        img_url = (img_tag.get("data-src") or img_tag.get("src", "")) if img_tag else ""

        if title and link:
            articles.append({
                "source": source_name,
                "article_id": f"detik_{article_id}",
                "category": section,
                "title": title,
                "url": link,
                "image_url": img_url
            })
    return articles

def parse_grid(soup):
    articles = []
    for a in soup.find_all("a", href=True):
        href = a["href"].split("?")[0].strip()
        if "grid.id/read/" in href:
            m = re.search(r'/read/(\d+)', href)
            article_id = m.group(1) if m else href
            
            title = a.get("title", "").strip() or a.get_text(strip=True)
            if len(title) < 15:  # Menyaring teks pendek/tombol navigasi
                continue
            
            img_tag = a.find("img")
            img_url = (img_tag.get("data-src") or img_tag.get("src", "")) if img_tag else ""
            
            articles.append({
                "source": "Grid.ID",
                "article_id": f"grid_{article_id}",
                "category": "Celebrity",
                "title": title,
                "url": href,
                "image_url": img_url
            })
    return articles

def parse_okezone(soup):
    articles = []
    for a in soup.find_all("a", href=True):
        href = a["href"].split("?")[0].strip()
        if "celebrity.okezone.com/read/" in href:
            m = re.search(r'/read/\d+/\d+/\d+/\d+/(\d+)', href) or re.search(r'/read/.+/(\d+)', href)
            article_id = m.group(1) if m else href

            title = a.get("title", "").strip() or a.get_text(strip=True)
            if len(title) < 15:
                continue

            img_tag = a.find("img")
            img_url = (img_tag.get("data-src") or img_tag.get("src", "")) if img_tag else ""

            articles.append({
                "source": "Okezone Celebrity",
                "article_id": f"okz_{article_id}",
                "category": "Celebrity",
                "title": title,
                "url": href,
                "image_url": img_url
            })
    return articles

def parse_tribun(soup):
    articles = []
    for a in soup.find_all("a", href=True):
        href = a["href"].split("?")[0].strip()
        if "trends.tribunnews.com" in href and re.search(r'/\d{4}/\d{2}/\d{2}/', href):
            title = a.get("title", "").strip() or a.get_text(strip=True)
            if len(title) < 15 or "halaman selanjutnya" in title.lower():
                continue

            slug_match = re.search(r'trends\.tribunnews\.com/(?:[^/]+/)?(\d{4}/\d{2}/\d{2}/[^/?#]+)', href)
            article_id = slug_match.group(1).replace("/", "_") if slug_match else href

            img_tag = a.find("img")
            img_url = (img_tag.get("data-src") or img_tag.get("src", "")) if img_tag else ""

            articles.append({
                "source": "TribunTrends",
                "article_id": f"tribun_{article_id}",
                "category": "Infotainment",
                "title": title,
                "url": href,
                "image_url": img_url
            })
    return articles

def fetch_all_targets():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    session = get_session()
    all_articles = []
    scraped_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for target in TARGETS:
        source_name = target["source"]
        url = target["url"]
        parser_type = target["parser"]
        
        try:
            logging.info(f"Mengambil data dari: {source_name} ({url})")
            resp = session.get(url, headers=headers, timeout=20)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            if parser_type == "detik":
                parsed = parse_detik(soup, source_name)
            elif parser_type == "grid":
                parsed = parse_grid(soup)
            elif parser_type == "okezone":
                parsed = parse_okezone(soup)
            elif parser_type == "tribun":
                parsed = parse_tribun(soup)
            else:
                parsed = []

            for item in parsed:
                item["scraped_at"] = scraped_time

            all_articles.extend(parsed)
            logging.info(f"-> Ditemukan {len(parsed)} artikel dari {source_name}")

        except Exception as e:
            logging.error(f"Gagal memproses {source_name}: {e}")
            continue

    return all_articles

def run_job():
    logging.info("=== Memulai Siklus Penarikan Multi-Source ===")
    raw_articles = fetch_all_targets()

    if not raw_articles:
        logging.warning("Tidak ada data yang berhasil ditarik dari seluruh target.")
        return

    df_new = pd.DataFrame(raw_articles).drop_duplicates(subset=["url"])

    if os.path.exists(CSV_FILE):
        df_existing = pd.read_csv(CSV_FILE)
        existing_urls = set(df_existing["url"].dropna().astype(str))
        df_to_save = df_new[~df_new["url"].astype(str).isin(existing_urls)]

        if not df_to_save.empty:
            df_to_save.to_csv(CSV_FILE, mode="a", header=False, index=False)
            logging.info(f"Berhasil menyimpan {len(df_to_save)} berita baru ke CSV.")
        else:
            logging.info("Semua artikel sudah ada di database (tidak ada berita baru).")
    else:
        df_new.to_csv(CSV_FILE, index=False)
        logging.info(f"Inisialisasi file CSV dengan {len(df_new)} berita awal.")

if __name__ == "__main__":
    run_job()
