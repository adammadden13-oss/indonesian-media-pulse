import os
import logging
from datetime import datetime, timezone, timedelta
import requests
from bs4 import BeautifulSoup
import pandas as pd
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(
    filename="scraper.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

CSV_EKONOMI_AUDIO = "ekonomi_audio.csv"
WIB = timezone(timedelta(hours=7))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7"
}

# 1. MAKRO EKONOMI (IHSG, Kurs USD, Emas)
def fetch_macro_economy(scraped_time):
    data = []
    
    # A. Kurs USD ke IDR (Google Finance)
    try:
        resp = requests.get("https://www.google.com/finance/quote/USD-IDR", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        price_div = soup.find("div", class_="YMlKec fxKbKc")
        if price_div:
            price = price_div.text.strip()
            data.append({
                "Waktu Tarik": scraped_time, "Sumber": "Google Finance", "Kategori": "Makro Ekonomi",
                "Indikator": "USD/IDR", "Nilai": price, "URL": "https://www.google.com/finance/quote/USD-IDR"
            })
    except Exception as e:
        logging.error(f"Gagal menarik Kurs USD: {e}")

    # B. IHSG / Jakarta Composite Index (Google Finance)
    try:
        resp = requests.get("https://www.google.com/finance/quote/COMPOSITE:IDX", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        price_div = soup.find("div", class_="YMlKec fxKbKc")
        if price_div:
            price = price_div.text.strip()
            data.append({
                "Waktu Tarik": scraped_time, "Sumber": "Google Finance", "Kategori": "Makro Ekonomi",
                "Indikator": "IHSG (Saham)", "Nilai": price, "URL": "https://www.google.com/finance/quote/COMPOSITE:IDX"
            })
    except Exception as e:
        logging.error(f"Gagal menarik IHSG: {e}")

    # C. Harga Emas Antam (Scraping Logam Mulia / Portal Emas)
    try:
        resp = requests.get("https://harga-emas.org/", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        # Mencari tabel harga 1 gram
        tds = soup.find_all("td")
        for i, td in enumerate(tds):
            if "1 gram" in td.text.lower() and i + 1 < len(tds):
                price = tds[i+1].text.strip()
                data.append({
                    "Waktu Tarik": scraped_time, "Sumber": "Harga-Emas.org", "Kategori": "Makro Ekonomi",
                    "Indikator": "Emas Antam (1g)", "Nilai": price, "URL": "https://harga-emas.org/"
                })
                break
    except Exception as e:
        logging.error(f"Gagal menarik Harga Emas: {e}")
        
    return data

# 2. AUDIO (Podcast & Musik Top Indonesia via API Terbuka)
def fetch_audio_trends(scraped_time):
    data = []
    
    # A. Top 10 Podcasts Indonesia (Apple Podcasts API - Sangat stabil untuk robot)
    try:
        url_podcast = "https://rss.applemarketingtools.com/api/v2/id/podcasts/top/10/podcasts.json"
        resp = requests.get(url_podcast, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            results = resp.json().get("feed", {}).get("results", [])
            for idx, item in enumerate(results, 1):
                data.append({
                    "Waktu Tarik": scraped_time, "Sumber": "Apple Podcasts ID", "Kategori": "Top Podcast",
                    "Indikator": f"#{idx} Podcast", "Nilai": f"{item.get('name')} (by {item.get('artistName')})", "URL": item.get("url")
                })
    except Exception as e:
        logging.error(f"Gagal menarik Top Podcast: {e}")

    # B. Top 10 Lagu Indonesia
    try:
        url_music = "https://rss.applemarketingtools.com/api/v2/id/music/most-played/10/songs.json"
        resp = requests.get(url_music, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            results = resp.json().get("feed", {}).get("results", [])
            for idx, item in enumerate(results, 1):
                data.append({
                    "Waktu Tarik": scraped_time, "Sumber": "Apple Music ID", "Kategori": "Top Musik",
                    "Indikator": f"#{idx} Song", "Nilai": f"{item.get('name')} - {item.get('artistName')}", "URL": item.get("url")
                })
    except Exception as e:
        logging.error(f"Gagal menarik Top Musik: {e}")

    return data

def run_economy_audio_tracker():
    scraped_time = datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S")
    logging.info("Memulai tracker Ekonomi & Audio...")
    
    all_data = []
    all_data.extend(fetch_macro_economy(scraped_time))
    all_data.extend(fetch_audio_trends(scraped_time))

    if not all_data:
        logging.warning("Data Ekonomi & Audio kosong.")
        return

    df = pd.DataFrame(all_data)
    kolom = ["Waktu Tarik", "Sumber", "Kategori", "Indikator", "Nilai", "URL"]
    
    # Validasi struktur kolom
    for col in kolom:
        if col not in df.columns:
            df[col] = "-"
            
    df = df[kolom]
    df.to_csv(CSV_EKONOMI_AUDIO, index=False)
    logging.info(f"Berhasil menyimpan {len(df)} data ke {CSV_EKONOMI_AUDIO}.")

if __name__ == "__main__":
    run_economy_audio_tracker()
