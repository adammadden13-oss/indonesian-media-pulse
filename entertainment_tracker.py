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

CSV_HIBURAN = "hiburan_dan_opini.csv"
WIB = timezone(timedelta(hours=7))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7"
}

def clean_text(text):
    if not isinstance(text, str) or not text:
        return ""
    return " ".join(text.split()).strip()

# 1. FILM TRENDING TMDb (THE MOVIE DATABASE)
def fetch_tmdb_trending(scraped_time):
    """Mengambil film terpopuler/trending dari TMDb."""
    movies = []
    tmdb_api_key = os.environ.get("TMDB_API_KEY", "")
    
    if tmdb_api_key:
        try:
            url = f"https://api.themoviedb.org/3/trending/movie/week?api_key={tmdb_api_key}&language=id-ID"
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                results = resp.json().get("results", [])[:8]
                for m in results:
                    title = clean_text(m.get("title") or m.get("original_title"))
                    m_id = m.get("id")
                    overview = clean_text(m.get("overview", ""))[:120]
                    desc = f"{title}: {overview}..." if overview else title
                    movies.append({
                        "Waktu Tarik": scraped_time,
                        "Sumber": "TMDb Trending",
                        "Kategori": "Film Bioskop & Box Office",
                        "Judul": desc,
                        "URL": f"https://www.themoviedb.org/movie/{m_id}"
                    })
        except Exception as e:
            logging.error(f"Gagal TMDb API: {e}")

    # Fallback jika API key belum diatur: scraping film trending bioskop publik
    if not movies:
        try:
            url = "https://21cineplex.com/"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            count = 0
            for a in soup.find_all("a", href=True):
                if "/movie/" in a["href"] or "/gui.movie_details" in a["href"]:
                    title = clean_text(a.get("title") or a.get_text())
                    if len(title) >= 4 and count < 6:
                        link = a["href"] if a["href"].startswith("http") else f"https://21cineplex.com{a['href']}"
                        movies.append({
                            "Waktu Tarik": scraped_time,
                            "Sumber": "Cinema XXI / Bioskop",
                            "Kategori": "Film Bioskop & Box Office",
                            "Judul": f"Film Populer Bioskop: {title}",
                            "URL": link
                        })
                        count += 1
        except Exception as e:
            logging.error(f"Gagal scraping bioskop fallback: {e}")

    return movies

# 2. TREN PENCARIAN GOOGLE (HIBURAN & POP CULTURE)
def fetch_google_entertainment_trends(scraped_time):
    url = "https://trends.google.com/trending/rss?geo=ID"
    trends = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        root = ET.fromstring(resp.content)
        for item in root.findall('./channel/item')[:6]:
            keyword = clean_text(item.find('title').text) if item.find('title') is not None else ""
            news_item = item.find('{https://trends.google.com/trending/rss}news_item')
            news_title = clean_text(news_item.find('{https://trends.google.com/trending/rss}news_item_title').text) if news_item is not None else f"Tren Pencarian: {keyword}"
            news_url = news_item.find('{https://trends.google.com/trending/rss}news_item_url').text.strip() if news_item is not None else f"https://trends.google.com/trending?geo=ID&q={keyword}"

            if keyword:
                trends.append({
                    "Waktu Tarik": scraped_time,
                    "Sumber": "Google Trends ID",
                    "Kategori": "Tren Pencarian Google",
                    "Judul": f"[{keyword}] {news_title}",
                    "URL": news_url
                })
    except Exception as e:
        logging.error(f"Gagal Google Trends: {e}")
    return trends

# 3. OPINI & EDITORIAL PERS NASIONAL
def fetch_editorial_opini(scraped_time):
    url = "https://epaper.mediaindonesia.com/category/editorial"
    articles = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        count = 0
        for a in soup.find_all("a", href=True):
            if count >= 6:
                break
            title = clean_text(a.get_text())
            link = a["href"].strip()
            if len(title) >= 20 and not any(x in title.lower() for x in ["redaksi", "pedoman", "login", "kontak", "epaper"]):
                full_url = link if link.startswith("http") else f"https://epaper.mediaindonesia.com{link}"
                articles.append({
                    "Waktu Tarik": scraped_time,
                    "Sumber": "Media Indonesia",
                    "Kategori": "Opini & Editorial",
                    "Judul": f"Editorial: {title}",
                    "URL": full_url
                })
                count += 1
    except Exception as e:
        logging.error(f"Gagal Editorial: {e}")
    return articles

def run_entertainment_tracker():
    scraped_time = datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S")
    logging.info("Memulai tracker Hiburan & Opini...")
    
    all_data = []
    all_data.extend(fetch_tmdb_trending(scraped_time))
    all_data.extend(fetch_google_entertainment_trends(scraped_time))
    all_data.extend(fetch_editorial_opini(scraped_time))

    if not all_data:
        logging.warning("Data hiburan & opini kosong.")
        return

    df = pd.DataFrame(all_data).drop_duplicates(subset=["Judul"])
    kolom = ["Waktu Tarik", "Sumber", "Kategori", "Judul", "URL"]
    df = df[kolom]
    
    df.to_csv(CSV_HIBURAN, index=False)
    logging.info(f"Berhasil menyimpan {len(df)} data ke {CSV_HIBURAN}.")

if __name__ == "__main__":
    run_entertainment_tracker()
