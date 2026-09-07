import os
import re
import urllib.parse
from datetime import datetime, timezone, timedelta
import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup
import pandas as pd

WIB = timezone(timedelta(hours=7))
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36', 
    'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7'
}
CSV_TRENDING = 'berita_trending.csv'
KOMPAS_CATS = r'(?:Regional|Nasional|Megapolitan|Global|News|Bola|Tekno|Otomotif|Money|Food|Health|Tren|Edukasi|Sains|Hype|Lifestyle|Homey|Properti|Travel|UMKM|JEO)'

def clean_text_trending(text):
    if not isinstance(text, str) or not text: return ''
    cleaned = ' '.join(text.split())
    cleaned = re.sub(rf'\s+{KOMPAS_CATS}\s+\d{{1,2}}\s+[A-Za-z]+\s+\d{{4}}(?:\s*[-–—]?\s*\d{{1,2}}:\d{{2}}(?:\s*(?:WIB|WITA|WIT))?)?\s*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+\d{1,2}\s+[A-Za-z]+\s+\d{4}(?:\s*[-–—]?\s*\d{1,2}:\d{2}(?:\s*(?:WIB|WITA|WIT))?)?\s*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+\d+\s*(?:menit|jam|hari|detik)\s*(?:yang)?\s*lalu\s*$', '', cleaned, flags=re.IGNORECASE)
    return cleaned.strip()

def fetch_twitter_trends(scraped_time):
    url = 'https://getdaytrends.com/indonesia/'
    trends = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        count = 0
        for tr in soup.find_all('tr'):
            if count >= 10: break # Ambil top 10 saja
            a_tag = tr.find('a', href=True)
            if a_tag and '/trend/' in a_tag['href']:
                topic = clean_text_trending(a_tag.get_text())
                if len(topic) < 2: continue
                desc_el = tr.find('td', class_='desc') or tr.find('span', class_='text-muted')
                tweet_count = clean_text_trending(desc_el.get_text()) if desc_el else 'Trending di X'
                encoded_query = urllib.parse.quote(topic)
                trends.append({
                    'Waktu Tarik': scraped_time, 'Wilayah': 'Indonesia', 'Sumber': 'X (Twitter) Trending', 
                    'Topik / Kata Kunci': topic, 'Volume Pencarian': tweet_count, 
                    'Judul Berita': f'Trending Topic X Indonesia: {topic}', 
                    'URL': f'https://x.com/search?q={encoded_query}&src=trend_click'
                })
                count += 1
    except Exception as e:
        print(f'Gagal X Trends: {e}')
    return trends

def fetch_tiktok_trends(scraped_time):
    print("Menarik data tren TikTok via News Aggregator...")
    articles = []
    # Menggunakan Google News RSS khusus kueri TikTok untuk bypass Anti-Bot
    url = 'https://news.google.com/rss/search?q=viral+tiktok+OR+trending+tiktok+when:1d&hl=id&gl=ID&ceid=ID:id'
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        root = ET.fromstring(resp.content)
        count = 0
        for item in root.findall('./channel/item'):
            if count >= 10: break  # Ambil top 10 berita TikTok terviral hari ini
            
            raw_title = item.find('title').text if item.find('title') is not None else ''
            # Bersihkan nama publisher di akhir judul (misal: "... - detikcom")
            title = re.sub(r'\s*-\s*[^-]+$', '', raw_title)
            link = item.find('link').text if item.find('link') is not None else '-'
            
            articles.append({
                'Waktu Tarik': scraped_time,
                'Wilayah': 'Indonesia',
                'Sumber': 'TikTok Trending (News)',
                'Topik / Kata Kunci': 'Viral TikTok',
                'Volume Pencarian': 'Trending Sosmed',
                'Judul Berita': clean_text_trending(title),
                'URL': link
            })
            count += 1
    except Exception as e:
        print(f'Gagal menarik TikTok Trends: {e}')
    return articles

def fetch_youtube_trends(scraped_time):
    url = 'https://www.youtube.com/feed/trending?gl=ID&hl=id'
    videos = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        html = resp.text
        import json
        idx = html.find('var ytInitialData')
        if idx != -1:
            start_idx = html.find('{', idx)
            data, _ = json.JSONDecoder().raw_decode(html[start_idx:])
            def extract_video_renderers(obj):
                found = []
                if isinstance(obj, dict):
                    if 'videoRenderer' in obj:
                        vr = obj['videoRenderer']
                        vid_id = vr.get('videoId')
                        title = ''.join([r.get('text', '') for r in vr.get('title', {}).get('runs', [])])
                        channel = ''.join([r.get('text', '') for r in vr.get('ownerText', {}).get('runs', [])])
                        views = vr.get('viewCountText', {}).get('simpleText', 'Trending YouTube')
                        if vid_id and title:
                            found.append({
                                'Waktu Tarik': scraped_time, 'Wilayah': 'Indonesia', 'Sumber': f'YouTube Trending ({channel})', 
                                'Topik / Kata Kunci': clean_text_trending(title)[:40] + '...', 'Volume Pencarian': views, 
                                'Judul Berita': clean_text_trending(title), 'URL': f'https://www.youtube.com/watch?v={vid_id}'
                            })
                    else:
                        for v in obj.values(): found.extend(extract_video_renderers(v))
                elif isinstance(obj, list):
                    for item in obj: found.extend(extract_video_renderers(item))
                return found
            all_vids = extract_video_renderers(data)
            videos = all_vids[:10] # Top 10 YouTube
    except Exception as e:
        print(f'Gagal YouTube Trends: {e}')
    return videos

def fetch_google_trends(scraped_time):
    url = 'https://trends.google.com/trending/rss?geo=ID'
    articles = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        root = ET.fromstring(resp.content)
        for item in root.findall('./channel/item')[:10]: # Top 10
            keyword = clean_text_trending(item.find('title').text) if item.find('title') is not None else '-'
            traffic_el = item.find('{https://trends.google.com/trending/rss}approx_traffic')
            traffic = clean_text_trending(traffic_el.text) if traffic_el is not None else '-'
            news_item = item.find('{https://trends.google.com/trending/rss}news_item')
            if news_item is not None:
                title_el = news_item.find('{https://trends.google.com/trending/rss}news_item_title')
                url_el = news_item.find('{https://trends.google.com/trending/rss}news_item_url')
                news_title = clean_text_trending(title_el.text) if title_el is not None else '-'
                news_url = url_el.text.strip() if url_el is not None else '-'
            else:
                news_title, news_url = '-', '-'
            articles.append({
                'Waktu Tarik': scraped_time, 'Wilayah': 'Indonesia', 'Sumber': 'Google Trends ID', 
                'Topik / Kata Kunci': keyword, 'Volume Pencarian': traffic, 'Judul Berita': news_title, 'URL': news_url
            })
    except Exception as e:
        print(f'Gagal Google Trends: {e}')
    return articles

def run_trending():
    scraped_time = datetime.now(WIB).strftime('%Y-%m-%d %H:%M:%S')
    print('=== Memulai penarikan tren sosial media terpadu ===')
    all_data = []
    
    all_data.extend(fetch_tiktok_trends(scraped_time)) # Fitur Baru
    all_data.extend(fetch_twitter_trends(scraped_time))
    all_data.extend(fetch_youtube_trends(scraped_time))
    all_data.extend(fetch_google_trends(scraped_time))
    
    if not all_data:
        print('Data trending kosong. Pastikan koneksi internet stabil.')
        return
        
    df_trending = pd.DataFrame(all_data).drop_duplicates(subset=['URL'])
    df_trending['Judul Berita'] = df_trending['Judul Berita'].apply(clean_text_trending)
    
    kolom = ['Waktu Tarik', 'Wilayah', 'Sumber', 'Topik / Kata Kunci', 'Volume Pencarian', 'Judul Berita', 'URL']
    df_trending = df_trending[kolom]
    
    # Simpan sebagai CSV agar ringan dan kompatibel dengan AI/Web
    df_trending.to_csv(CSV_TRENDING, index=False)
    print(f'[SUCCESS] Berhasil menyimpan {len(df_trending)} data tren ke {CSV_TRENDING}')

if __name__ == "__main__":
    run_trending()
