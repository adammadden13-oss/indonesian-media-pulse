import os
import re
import json
import urllib.parse
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7"
}

def clean_text(text):
    if not text:
        return ""
    return " ".join(text.split())

# 1. MEDIA SOSIAL: X (TWITTER) INDONESIA
def fetch_twitter_trends(scraped_time):
    url = "https://getdaytrends.com/indonesia/"
    trends = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        count = 0
        for tr in soup.find_all("tr"):
            if count >= 15:
                break
            a_tag = tr.find("a", href=True)
            if a_tag and "/trend/" in a_tag["href"]:
                topic = clean_text(a_tag.get_text())
                if len(topic) < 2:
                    continue

                desc_el = tr.find("td", class_="desc") or tr.find("span", class_="text-muted")
                tweet_count = clean_text(desc_el.get_text()) if desc_el else "Trending di X"
                encoded_query = urllib.parse.quote(topic)

                trends.append({
                    "Waktu Tarik": scraped_time,
                    "Wilayah": "Indonesia",
                    "Sumber": "X (Twitter) Trending",
                    "Topik / Kata Kunci": topic,
                    "Volume Pencarian": tweet_count,
                    "Judul Berita": f"Trending Topic X Indonesia: {topic}",
                    "URL": f"https://x.com/search?q={encoded_query}&src=trend_click"
                })
                count += 1
    except Exception as e:
        logging.error(f"Gagal X Trends: {e}")
    return trends

# 2. MEDIA SOSIAL: YOUTUBE TRENDING INDONESIA
def fetch_youtube_trends(scraped_time):
    url = "https://www.youtube.com/feed/trending?gl=ID&hl=id"
    videos = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        html = resp.text
        idx = html.find("var ytInitialData")
        if idx != -1:
            start_idx = html.find("{", idx)
            data, _ = json.JSONDecoder().raw_decode(html[start_idx:])

            def extract_video_renderers(obj):
                found = []
                if isinstance(obj, dict):
                    if "videoRenderer" in obj:
                        vr = obj["videoRenderer"]
                        vid_id = vr.get("videoId")
                        title = "".join([r.get("text", "") for r in vr.get("title", {}).get("runs", [])])
                        channel = "".join([r.get("text", "") for r in vr.get("ownerText", {}).get("runs", [])])
                        views = vr.get("viewCountText", {}).get("simpleText", "Trending YouTube")
                        
                        if vid_id and title:
                            found.append({
                                "Waktu Tarik": scraped_time,
                                "Wilayah": "Indonesia",
                                "Sumber": f"YouTube Trending ({channel})",
                                "Topik / Kata Kunci": clean_text(title)[:40] + "...",
                                "Volume Pencarian": views,
                                "Judul Berita": clean_text(title),
                                "URL": f"https://www.youtube.com/watch?v={vid_id}"
                            })
                    else:
                        for v in obj.values():
                            found.extend(extract_video_renderers(v))
                elif isinstance(obj, list):
                    for item in obj:
                        found.extend(extract_video_renderers(item))
                return found

            all_vids = extract_video_renderers(data)
            videos = all_vids[:15]
    except Exception as e:
        logging.error(f"Gagal YouTube Trends: {e}")
    return videos

# 3. MESIN PENCARI: GOOGLE TRENDS INDONESIA
def fetch_google_trends(scraped_time):
    url = "https://trends.google.com/trending/rss?geo=ID"
    articles = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
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
                source_name = clean_text(source_el.text) if source_el is not None else "Google Trends ID"
            else:
                news_title, news_url, source_name = "-", "-", "Google Trends ID"

            articles.append({
                "Waktu Tarik": scraped_time,
                "Wilayah": "Indonesia",
                "Sumber": f"Google Trends ({source_name})",
                "Topik / Kata Kunci": keyword,
                "Volume Pencarian": traffic,
                "Judul Berita": news_title,
                "URL": news_url
            })
    except Exception as e:
        logging.error(f"Gagal Google Trends: {e}")
    return articles

# 4. DETIKCOM: GENERAL & DETIKNEWS TERPOPULER (BUKAN SELEB)
def fetch_detik_terpopuler(scraped_time):
    articles = []
    targets = [
        {"url": "https://www.detik.com/terpopuler/news", "sumber": "detikNews Terpopuler (Nasional)"},
        {"url": "https://www.detik.com/terpopuler", "sumber": "Detik.com Terpopuler (General)"}
    ]
    for t in targets:
        try:
            resp = requests.get(t["url"], headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            for el in soup.find_all("a", attrs={"dtr-ttl": True}):
                title = clean_text(el.get("dtr-ttl", ""))
                link = el.get("href", "").strip()
                section = clean_text(el.get("dtr-evt", "")).lower()
                if any(x in section for x in ["header", "footer", "menu", "logo"]) or len(title) < 20:
                    continue
                articles.append({
                    "Waktu Tarik": scraped_time,
                    "Wilayah": "Indonesia",
                    "Sumber": t["sumber"],
                    "Topik / Kata Kunci": "Trending News",
                    "Volume Pencarian": "Top Traffic",
                    "Judul Berita": title,
                    "URL": link
                })
        except Exception as e:
            logging.error(f"Gagal {t['sumber']}: {e}")
    return articles

# 5. KOMPAS.COM TERPOPULER NASIONAL
def fetch_kompas_terpopuler(scraped_time):
    articles = []
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
    return articles

# 6. TRIBUNNEWS TERPOPULER NASIONAL
def fetch_tribun_terpopuler(scraped_time):
    articles = []
    try:
        resp = requests.get("https://www.tribunnews.com/populer", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"].split("?")[0].strip()
            if "tribunnews.com" in href and re.search(r'/\d{4}/\d{2}/\d{2}/', href):
                title = clean_text(a.get("title") or a.get_text())
                if len(title) >= 25 and not any(x in title.lower() for x in ["halaman selanjutnya", "lihat foto", "arsip"]):
                    articles.append({
                        "Waktu Tarik": scraped_time,
                        "Wilayah": "Indonesia",
                        "Sumber": "Tribunnews Terpopuler",
                        "Topik / Kata Kunci": "Trending Nasional",
                        "Volume Pencarian": "Top Traffic",
                        "Judul Berita": title,
                        "URL": href
                    })
    except Exception as e:
        logging.error(f"Gagal Tribunnews: {e}")
    return articles

def run_trending():
    scraped_time = datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S")
    logging.info("Memulai penarikan tren terpadu (General News & Sosmed)...")
    
    all_data = []

    # 1. Media Sosial
    all_data.extend(fetch_twitter_trends(scraped_time))
    all_data.extend(fetch_youtube_trends(scraped_time))

    # 2. Mesin Pencari
    all_data.extend(fetch_google_trends(scraped_time))

    # 3. Portal Berita Nasional General & Terpopuler
    all_data.extend(fetch_detik_terpopuler(scraped_time))
    all_data.extend(fetch_kompas_terpopuler(scraped_time))
    all_data.extend(fetch_tribun_terpopuler(scraped_time))

    if not all_data:
        logging.warning("Data trending kosong.")
        return

    df_trending = pd.DataFrame(all_data).drop_duplicates(subset=["URL"])
    kolom = ["Waktu Tarik", "Wilayah", "Sumber", "Topik / Kata Kunci", "Volume Pencarian", "Judul Berita", "URL"]
    df_trending = df_trending[kolom]
    
    df_trending.to_csv(CSV_TRENDING, index=False)
    logging.info(f"Berhasil menyimpan {len(df_trending)} data tren ke {CSV_TRENDING}.")

if __name__ == "__main__":
    run_trending()
