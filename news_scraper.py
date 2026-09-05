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
    """Membersihkan judul dari spasi ganda, tag waktu, dan tanggal rilis."""
    if not isinstance(text, str) or not text:
        return ""
    cleaned = " ".join(text.split())
    
    # 1. Hapus pola tanggal & jam lengkap (contoh: "05 September 2026 - 23:23 WIB" atau "05 September 2026")
    cleaned = re.sub(r'\s*\d{1,2}\s+[A-Za-z]+\s+\d{4}(?:\s*[-–—]?\s*\d{1,2}:\d{2}(?:\s*(?:WIB|WITA|WIT))?)?\s*$', '', cleaned, flags=re.IGNORECASE)
    
    # 2. Hapus pola waktu relatif (contoh: "2 jam yang lalu", "15 menit lalu", "3 jam lalu")
    cleaned = re.sub(r'\s*\d+\s*(?:menit|jam|hari|detik)\s*(?:yang)?\s*lalu\s*$', '', cleaned, flags=re.IGNORECASE)
    
    return cleaned.strip()

# 1. DETIKNEWS
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

# 2. KOMPAS NASIONAL
def parse_kompas(soup, sumber):
    articles = []
    for a in soup.find_all("a", href=True):
        link = a["href"].split("?")[0].strip()
        if "kompas.com/read/" in link:
            raw_title = a.get("title") or a.get_text()
            title = clean_text(raw_title)
            if len(title) >= 25 and not any(x in title.lower() for x in ["lihat foto", "baca juga", "artikel kompas"]):
                articles.append({
                    "Sumber": sumber,
                    "Kategori": "Nasional & Kebijakan",
                    "Judul": title,
                    "URL": link
                })
    return articles

# 3. CNN INDONESIA
def parse_cnn(soup, sumber):
    articles = []
    for a in soup.find_all("a", href=True):
        link = a["href"].split("?")[0].strip()
        if "cnnindonesia.com/nasional/" in link:
            raw_title = a.get("title") or a.get_text()
            title = clean_text(raw_title)
            if len(title) >= 25 and not any(x in title.lower() for x in ["lihat foto", "video", "baca juga", "fokus"]):
                articles.append({
                    "Sumber": sumber,
                    "Kategori": "Nasional & Politik",
                    "Judul": title,
                    "URL": link
                })
    return articles

# 4. TRIBUNNEWS NASIONAL
def parse_tribun(soup, sumber):
    articles = []
    for a in soup.find_all("a", href=True):
        link = a["href"].split("?")[0].strip()
        if "tribunnews.com/nasional/" in link and re.search(r'/\d{4}/\d{2}/\d{2}/', link):
            raw_title = a.get("title") or a.get_text()
            title = clean_text(raw_title)
            if len(title) >= 25 and not any(x in title.lower() for x in ["halaman selanjutnya", "lihat foto", "arsip"]):
                articles.append({
                    "Sumber": sumber,
                    "Kategori": "Peristiwa Nasional",
                    "Judul": title,
                    "URL": link
                })
    return articles

# 5. SINDONEWS NASIONAL (Dibersihkan dari tag waktu)
def parse_sindo(soup, sumber):
    articles = []
    for a in soup.find_all("a", href=True):
        link = a["href"].split("?")[0].strip()
        if "sindonews.com/read/" in link:
            # Gunakan attribute title jika tersedia, atau get_text lalu bersihkan
            raw_title = a.get("title") or a.get_text()
            title = clean_text(raw_title)
            if len(title) >= 25 and not any(x in title.lower() for x in ["lihat foto", "halaman", "baca juga"]):
                articles.append({
                    "Sumber": sumber,
                    "Kategori": "Nasional & Politik",
                    "Judul": title,
                    "URL": link
                })
    return articles

# 6. INEWS NASIONAL
def parse_inews(soup, sumber):
    articles = []
    for a in soup.find_all("a", href=True):
        link = a["href"].split("?")[0].strip()
        if "inews.id/news/" in link:
            raw_title = a.get("title") or a.get_text()
            title = clean_text(raw_title)
            if len(title) >= 25 and not any(x in title.lower() for x in ["lihat foto", "video", "baca juga"]):
                articles.append({
                    "Sumber": sumber,
                    "Kategori": "Peristiwa & Hukum",
                    "Judul": title,
                    "URL": link
                })
    return articles

# 7. LIPUTAN6 NEWS
def parse_liputan6(soup, sumber):
    articles = []
    for a in soup.find_all("a", href=True):
        link = a["href"].split("?")[0].strip()
        if "liputan6.com/news/read/" in link:
            raw_title = a.get("title") or a.get_text()
            title = clean_text(raw_title)
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
        try:
            df_existing = pd.read_csv(CSV_FILE)
            # Bersihkan judul-judul lama yang sudah tersimpan dari eksekusi sebelumnya
            df_existing["Judul"] = df_existing["Judul"].apply(clean_text)
            
            # Gabungkan dengan data baru & eliminasi duplikasi berdasarkan URL
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            df_combined = df_combined.drop_duplicates(subset=["URL"], keep="first")
            df_combined = df_combined[kolom_urut]
            
            df_combined.to_csv(CSV_FILE, index=False)
            logging.info(f"Berhasil membersihkan dan memperbarui {len(df_combined)} berita.")
        except Exception as e:
            logging.error(f"Error memproses file lama: {e}")
            df_new.to_csv(CSV_FILE, index=False)
    else:
        df_new.to_csv(CSV_FILE, index=False)
        logging.info(f"Membuat file CSV news baru dengan {len(df_new)} berita.")

if __name__ == "__main__":
    run_job()
