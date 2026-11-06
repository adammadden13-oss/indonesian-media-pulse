import os
import re
import logging
from datetime import datetime, timezone, timedelta
import requests
from bs4 import BeautifulSoup
import pandas as pd
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logging.basicConfig(filename="scraper.log", level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

CSV_FILE = "berita_terkini.csv"
WIB = timezone(timedelta(hours=7))

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
    if not isinstance(text, str) or not text: return ""
    cleaned = " ".join(text.split())
    cleaned = cleaned.replace(',', ' -').replace('"', "'")
    return cleaned.strip()

def get_img_url(img):
    if not img: return ""
    url = img.get('data-src') or img.get('data-original') or img.get('src') or ""
    if url.startswith('//'): return 'https:' + url
    return url

def extract_image(element):
    """Fungsi Super Ekstraktor Gambar"""
    img = element.find('img')
    if img: return get_img_url(img)
    
    prev = element.find_previous_sibling('a')
    if prev:
        img = prev.find('img')
        if img: return get_img_url(img)
        
    parent = element.parent
    if parent:
        links = parent.find_all('a')
        if len(links) <= 3:
            img = parent.find('img')
            if img: return get_img_url(img)
            
    if parent and parent.parent:
        links = parent.parent.find_all('a')
        if len(links) <= 3:
            img = parent.parent.find('img')
            if img: return get_img_url(img)
            
    return ""

def parse_detik(soup, sumber):
    articles = []
    for el in soup.find_all("a", attrs={"dtr-ttl": True}):
        title = clean_text(el.get("dtr-ttl", ""))
        link = el.get("href", "").strip()
        section = clean_text(el.get("dtr-evt", "")).title()
        article_id = el.get("dtr-id", "").strip()
        img_url = extract_image(el)

        if any(x in section.lower() for x in ["header", "footer", "menu", "logo", "login", "register"]): continue
        if not article_id.isdigit():
            m = re.search(r'/d-(\d+)/', link)
            if not m: continue

        if len(title) >= 20 and link.startswith("http"):
            articles.append({"Sumber": sumber, "Kategori": section or "Berita Utama", "Judul": title, "URL": link, "Gambar": img_url})
    return articles

def parse_grid(soup):
    articles = []
    for a in soup.find_all("a", href=True):
        link = a["href"].split("?")[0].strip()
        if "grid.id/read/" in link:
            title = clean_text(a.get("title") or a.get_text())
            img_url = extract_image(a)
            if len(title) >= 20 and "halaman" not in title.lower():
                articles.append({"Sumber": "Grid.ID", "Kategori": "Celebrity", "Judul": title, "URL": link, "Gambar": img_url})
    return articles

def parse_okezone(soup):
    articles = []
    for a in soup.find_all("a", href=True):
        link = a["href"].split("?")[0].strip()
        if "celebrity.okezone.com/read/" in link:
            title = clean_text(a.get("title") or a.get_text())
            img_url = extract_image(a)
            if len(title) >= 20:
                articles.append({"Sumber": "Okezone Celebrity", "Kategori": "Celebrity", "Judul": title, "URL": link, "Gambar": img_url})
    return articles

def parse_tribun(soup):
    articles = []
    for a in soup.find_all("a", href=True):
        link = a["href"].split("?")[0].strip()
        if "trends.tribunnews.com" in link and re.search(r'/\d{4}/\d{2}/\d{2}/', link):
            title = clean_text(a.get("title") or a.get_text())
            img_url = extract_image(a)
            if len(title) >= 20 and not any(x in title.lower() for x in ["halaman selanjutnya", "lihat foto", "baca juga"]):
                articles.append({"Sumber": "TribunTrends", "Kategori": "Infotainment", "Judul": title, "URL": link, "Gambar": img_url})
    return articles

def fetch_all():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    session = get_session()
    all_data = []
    scraped_time = datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S")

    for target in TARGETS:
        try:
            resp = session.get(target["url"], headers=headers, timeout=20)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            if target["tipe"] == "detik": items = parse_detik(soup, target["sumber"])
            elif target["tipe"] == "grid": items = parse_grid(soup)
            elif target["tipe"] == "okezone": items = parse_okezone(soup)
            elif target["tipe"] == "tribun": items = parse_tribun(soup)
            else: items = []

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
        logging.warning("Tidak ada data yang ditemukan.")
        return

    df_new = pd.DataFrame(data).drop_duplicates(subset=["URL"])
    
    # Siapkan kolom agar selaras dengan Berita Nasional
    if "Gambar" not in df_new.columns: df_new["Gambar"] = ""
    df_new["Sentimen"] = ""
    df_new["Skor Sentimen"] = ""

    kolom_urut = ["Waktu Tarik", "Sumber", "Kategori", "Judul", "URL", "Gambar", "Sentimen", "Skor Sentimen"]
    df_new = df_new[kolom_urut]

    if os.path.exists(CSV_FILE):
        try:
            df_existing = pd.read_csv(CSV_FILE)
            if "Sentimen" not in df_existing.columns: df_existing["Sentimen"] = ""
            if "Skor Sentimen" not in df_existing.columns: df_existing["Skor Sentimen"] = ""
            if "Gambar" not in df_existing.columns: df_existing["Gambar"] = ""
            
            df_existing["Judul"] = df_existing["Judul"].apply(clean_text)
            
            # Gabungkan data baru dengan data lama
            df_combined = pd.concat([df_new, df_existing], ignore_index=True)
            df_combined = df_combined.drop_duplicates(subset=["URL"], keep="first")
            df_combined = df_combined.sort_values(by="Waktu Tarik", ascending=False)
            df_combined = df_combined[kolom_urut]
            df_combined.to_csv(CSV_FILE, index=False)
            logging.info(f"Berhasil memperbarui {len(df_combined)} berita infotainment.")
        except Exception as e:
            logging.error(f"Gagal membaca CSV lama, membuat baru: {e}")
            df_new.to_csv(CSV_FILE, index=False)
    else:
        df_new.to_csv(CSV_FILE, index=False)

if __name__ == "__main__":
    run_job()
