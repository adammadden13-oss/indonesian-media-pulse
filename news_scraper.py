import os
import re
import logging
from datetime import datetime, timezone, timedelta
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

CSV_FILE = "berita_news.csv"
WIB = timezone(timedelta(hours=7))

# 7 Portal Berita Terbesar di Indonesia
TARGETS = [
    {"sumber": "detikNews", "url": "https://news.detik.com/berita", "tipe": "detik"},
    {"sumber": "Kompas.com Nasional", "url": "https://nasional.kompas.com", "tipe": "kompas"},
    {"sumber": "CNN Indonesia", "url": "https://www.cnnindonesia.com/nasional", "tipe": "cnn"},
    {"sumber": "Tribunnews Nasional", "url": "https://www.tribunnews.com/nasional", "tipe": "tribun"},
    {"sumber": "SINDOnews Nasional", "url": "https://nasional.sindonews.com", "tipe": "sindo"},
    {"sumber": "iNews Nasional", "url": "https://www.inews.id/news/nasional", "tipe": "inews"},
    {"sumber": "Liputan6 News", "url": "https://www.liputan6.com/news", "tipe": "liputan6"}
]

def get_session():
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session

def clean_text(text):
    if not text:
        return ""
    return " ".join(text.split())

# 1. PARSER DETIKNEWS
def parse_detik(soup, sumber):
    articles = []
    for el in soup.find_all("a", attrs={"dtr-ttl": True}):
        title = clean_text(el.get("dtr-ttl", ""))
        link = el.get("href", "").strip()
        section = clean_text(el.get("dtr-evt", "")).title()
        article_id = el.get("dtr-id", "").strip()

        if any(x in section.lower() for x in ["header", "footer", "menu", "logo", "login"]):
            continue
        if not article_id.isdigit():
            m = re.search(r'/d-(\d+)/', link)
            if not m:
                continue

        if len(title) >= 20 and link.startswith("http"):
            articles.append({
                "Sumber": sumber,
                "Kategori": "Berita & Peristiwa",
                "Judul": title,
                "URL": link
            })
    return articles

# 2. PARSER KOMPAS NASIONAL
def parse_kompas(soup, sumber):
    articles = []
    for a in soup.find_all("a", href=True):
        link = a["href"].split("?")[0].strip()
        if "kompas.com/read/" in link:
            title = clean_text(a.get("title") or a.get_text())
            if len(title) >= 25 and not any(x in title.lower() for x in ["lihat foto", "baca juga", "artikel kompas"]):
                articles.append({
                    "Sumber": sumber,
                    "Kategori": "Nasional & Kebijakan",
                    "Judul": title,
                    "URL": link
                })
    return articles

# 3. PARSER CNN INDONESIA
def parse_cnn(soup, sumber):
    articles = []
    for a in soup.find_all("a", href=True):
        link = a["href"].split("?")[0].strip()
        if "cnnindonesia.com/nasional/" in link:
            title = clean_text(a.get("title") or a.get_text())
            if len(title) >= 25 and not any(x in title.lower() for x in ["lihat foto", "video", "baca juga", "fokus"]):
                articles.append({
                    "Sumber": sumber,
                    "Kategori": "Nasional & Politik",
                    "Judul": title,
                    "URL": link
                })
    return articles

# 4. PARSER TRIBUNNEWS NASIONAL
def parse_tribun(soup, sumber):
    articles = []
    for a in soup.find_all("a", href=True):
        link = a["href"].split("?")[0].strip()
        if "tribunnews.com/nasional/" in link and re.search(r'/\d{4}/\d{2}/\d{2}/', link):
            title = clean_text(a.get("title") or a.get_text())
            if len(title) >= 25 and not any(x in title.lower() for x in ["halaman selanjutnya", "lihat foto", "arsip"]):
                articles.append({
                    "Sumber": sumber,
                    "Kategori": "Peristiwa Nasional",
                    "Judul": title,
                    "URL": link
                })
    return articles

# 5. PARSER SINDONEWS NASIONAL (MNC Group)
def parse_sindo(soup, sumber):
    articles = []
    for a in soup.find_all("a", href=True):
        link = a["href"].split("?")[0].strip()
        if "sindonews.com/read/" in link:
            title = clean_text(a.get("title") or a.get_text())
            if len(title) >= 25 and not any(x in title.lower() for x in ["lihat foto", "halaman", "baca juga"]):
                articles.append({
                    "Sumber": sumber,
                    "Kategori": "Nasional & Politik",
                    "Judul": title,
                    "URL": link
                })
    return articles

# 6. PARSER INEWS NASIONAL (MNC Group)
def parse_inews(soup, sumber):
    articles = []
    for a in soup.find_all("a", href=True):
        link = a["href"].split("?")[0].strip()
        if "inews.id/news/" in link:
            title = clean_text(a.get("title") or a.get_text())
            if len(title) >= 25 and not any(x in title.lower() for x in ["lihat foto", "video", "baca juga"]):
                articles.append({
                    "Sumber": sumber,
                    "Kategori": "Peristiwa & Hukum",
                    "Judul": title,
                    "URL": link
                })
    return articles

# 7. PARSER LIPUTAN6 NEWS
def parse_liputan6(soup, sumber):
    articles = []
    for a in soup.find_all("a", href=True):
        link = a["href"].split("?")[0].strip()
        if "liputan6.com/news/read/" in link:
            title = clean_text(a.get("title") or a.get_text())
            if len(title) >= 25:
                articles.append({
                    "Sumber": sumber,
                    "Kategori": "Hukum & Politik",
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
    scraped_time = datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S")

    for target in TARGETS:
        try:
            resp = session.get(target["url"], headers=headers, timeout=20)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            if target["tipe"] == "detik":
                items = parse_detik(soup, target["sumber"])
            elif target["tipe"] == "kompas":
                items = parse_kompas(soup, target["sumber"])
            elif target["tipe"] == "cnn":
                items = parse_cnn(soup, target["sumber"])
            elif target["tipe"] == "tribun":
                items = parse_tribun(soup, target["sumber"])
            elif target["tipe"] == "sindo":
                items = parse_sindo(soup, target["sumber"])
            elif target["tipe"] == "inews":
                items = parse_inews(soup, target["sumber"])
            elif target["tipe"] == "liputan6":
                items = parse_liputan6(soup, target["sumber"])
            else:
                items = []

            for item in items:
                item["Waktu Tarik"] = scraped_time

            all_data.extend(items)
        except Exception as e:
            logging.error(f"Gagal mengambil {target['sumber']}: {e}")
            continue

    return all_data

def run_job():
    data = fetch_all()
    if not data:
        logging.warning("Data berita general kosong.")
        return

    df_new = pd.DataFrame(data).drop_duplicates(subset=["URL"])
    kolom_urut = ["Waktu Tarik", "Sumber", "Kategori", "Judul", "URL"]
    df_new = df_new[kolom_urut]

    if os.path.exists(CSV_FILE):
        df_existing = pd.read_csv(CSV_FILE)
        existing_urls = set(df_existing["URL"].dropna().astype(str))
        df_to_save = df_new[~df_new["URL"].astype(str).isin(existing_urls)]

        if not df_to_save.empty:
            df_to_save.to_csv(CSV_FILE, mode="a", header=False, index=False)
            logging.info(f"Menambahkan {len(df_to_save)} berita news baru.")
    else:
        df_new.to_csv(CSV_FILE, index=False)
        logging.info(f"Membuat file CSV news baru dengan {len(df_new)} berita.")

if __name__ == "__main__":
    run_job()
