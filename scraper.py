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

CSV_FILE = "berita_terkini.csv"

# Daftar target portal berita
TARGETS = [
    {"sumber": "Wolipop", "url": "https://wolipop.detik.com", "tipe": "detik"},
    {"sumber": "DetikHot Celebs", "url": "https://hot.detik.com/celebs", "tipe": "detik"},
    {"sumber": "Grid.ID", "url": "https://www.grid.id", "tipe": "grid"},
    {"sumber": "Okezone Celebrity", "url": "https://celebrity.okezone.com", "tipe": "okezone"},
    {"sumber": "TribunTrends", "url": "https://trends.tribunnews.com/infotainment", "tipe": "tribun"}
]

def get_session():
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session

def clean_text(text):
    if not text:
        return ""
    # Hapus spasi ganda, enter, dan karakter whitespace berlebih
    return " ".join(text.split())

def parse_detik(soup, sumber):
    articles = []
    for el in soup.find_all("a", attrs={"dtr-ttl": True}):
        title = clean_text(el.get("dtr-ttl", ""))
        link = el.get("href", "").strip()
        section = clean_text(el.get("dtr-evt", "")).title()
        article_id = el.get("dtr-id", "").strip()

        # Filter ketat: buang header, footer, dan pastikan ID berupa angka artikel
        if any(x in section.lower() for x in ["header", "footer", "menu", "logo", "login", "register"]):
            continue
        if not article_id.isdigit():
            m = re.search(r'/d-(\d+)/', link)
            if not m:
                continue

        if len(title) >= 20 and link.startswith("http"):
            articles.append({
                "Sumber": sumber,
                "Kategori": section or "Berita Utama",
                "Judul": title,
                "URL": link
            })
    return articles

def parse_grid(soup):
    articles = []
    for a in soup.find_all("a", href=True):
        link = a["href"].split("?")[0].strip()
        if "grid.id/read/" in link:
            title = clean_text(a.get("title") or a.get_text())
            if len(title) >= 20 and "halaman" not in title.lower():
                articles.append({
                    "Sumber": "Grid.ID",
                    "Kategori": "Celebrity",
                    "Judul": title,
                    "URL": link
                })
    return articles

def parse_okezone(soup):
    articles = []
    for a in soup.find_all("a", href=True):
        link = a["href"].split("?")[0].strip()
        if "celebrity.okezone.com/read/" in link:
            title = clean_text(a.get("title") or a.get_text())
            if len(title) >= 20:
                articles.append({
                    "Sumber": "Okezone Celebrity",
                    "Kategori": "Celebrity",
                    "Judul": title,
                    "URL": link
                })
    return articles

def parse_tribun(soup):
    articles = []
    for a in soup.find_all("a", href=True):
        link = a["href"].split("?")[0].strip()
        if "trends.tribunnews.com" in link and re.search(r'/\d{4}/\d{2}/\d{2}/', link):
            title = clean_text(a.get("title") or a.get_text())
            if len(title) >= 20 and not any(x in title.lower() for x in ["halaman selanjutnya", "lihat foto", "baca juga"]):
                articles.append({
                    "Sumber": "TribunTrends",
                    "Kategori": "Infotainment",
                    "Judul": title,
                    "URL": link
                })
    return articles

def fetch_all():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    session = get_session()
    all_data = []
    scraped_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for target in TARGETS:
        try:
            resp = session.get(target["url"], headers=headers, timeout=20)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            if target["tipe"] == "detik":
                items = parse_detik(soup, target["sumber"])
            elif target["tipe"] == "grid":
                items = parse_grid(soup)
            elif target["tipe"] == "okezone":
                items = parse_okezone(soup)
            elif target["tipe"] == "tribun":
                items = parse_tribun(soup)
            else:
                items = []

            for item in items:
                item["Waktu Tarik"] = scraped_time

            all_data.extend(items)
        except Exception as e:
            logging.error(f"Error pada {target['sumber']}: {e}")
            continue

    return all_data

def run_job():
    data = fetch_all()
    if not data:
        logging.warning("Tidak ada data ditemukan.")
        return

    df_new = pd.DataFrame(data).drop_duplicates(subset=["URL"])

    if os.path.exists(CSV_FILE):
        df_existing = pd.read_csv(CSV_FILE)
        existing_urls = set(df_existing["URL"].dropna().astype(str))
        df_to_save = df_new[~df_new["URL"].astype(str).isin(existing_urls)]

        if not df_to_save.empty:
            df_to_save.to_csv(CSV_FILE, mode="a", header=False, index=False)
            logging.info(f"Menambahkan {len(df_to_save)} berita baru.")
    else:
        df_new.to_csv(CSV_FILE, index=False)
        logging.info(f"Membuat file CSV baru dengan {len(df_new)} berita.")

if __name__ == "__main__":
    run_job()
