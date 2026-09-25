import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timezone, timedelta

WIB = timezone(timedelta(hours=7))
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}
CSV_FILE = "ekonomi_audio.csv"

def fetch_financial_data(scraped_time):
    """Menarik data IHSG dan Kurs Rupiah dari Google Finance"""
    results = []
    print("Menarik data Ekonomi (IHSG & Kurs)...")
    
    # 1. IHSG (Indeks Harga Saham Gabungan)
    try:
        url_ihsg = "https://www.google.com/finance/quote/COMPOSITE:IDX"
        resp = requests.get(url_ihsg, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Mengambil harga dan persentase perubahan
        price_el = soup.find('div', class_='YMlKec fxKbKc')
        change_el = soup.find('div', class_='JwB6zf') # elemen persentase perubahan
        
        if price_el:
            perubahan = change_el.text.strip() if change_el else "Naik/Turun"
            results.append({
                "Waktu Tarik": scraped_time,
                "Kategori": "Pasar Modal",
                "Indikator / Judul Trek": "IHSG (Indeks Harga Saham Gabungan)",
                "Nilai / Artis": price_el.text.strip(),
                "Satuan / Platform": "Poin / BEI",
                "Perubahan / Status Tren": perubahan,
                "Insight & Dampak": "Data harian dari Google Finance",
                "URL": url_ihsg
            })
    except Exception as e:
        print(f"Gagal menarik IHSG: {e}")

    # 2. Kurs USD ke IDR
    try:
        url_usd = "https://www.google.com/finance/quote/USD-IDR"
        resp = requests.get(url_usd, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        price_el = soup.find('div', class_='YMlKec fxKbKc')
        change_el = soup.find('div', class_='JwB6zf')
        
        if price_el:
            perubahan = change_el.text.strip() if change_el else "Fluktuatif"
            results.append({
                "Waktu Tarik": scraped_time,
                "Kategori": "Mata Uang & Valas",
                "Indikator / Judul Trek": "Kurs USD / IDR",
                "Nilai / Artis": f"Rp {price_el.text.strip()}",
                "Satuan / Platform": "IDR per USD",
                "Perubahan / Status Tren": perubahan,
                "Insight & Dampak": "Data harian dari Google Finance",
                "URL": url_usd
            })
    except Exception as e:
        print(f"Gagal menarik Kurs USD: {e}")
        
    return results

def fetch_audio_podcast_data(scraped_time):
    """Menarik Top 5 Lagu dan Podcast di Indonesia via Apple API"""
    results = []
    print("Menarik data Top Audio & Podcast via API Resmi...")
    
    # 1. Top Songs (Apple Music Indonesia)
    try:
        url_songs = "https://itunes.apple.com/id/rss/topsongs/limit=5/json"
        resp = requests.get(url_songs, timeout=15)
        data = resp.json()
        
        entries = data.get('feed', {}).get('entry', [])
        for idx, entry in enumerate(entries):
            # Mendapatkan Judul Lagu
            title = entry.get('title', {}).get('label', 'Tanpa Judul')
            # Memisahkan Judul dan Artis (format API Apple: "Judul - Artis")
            if " - " in title:
                judul_lagu, artis = title.split(" - ", 1)
            else:
                judul_lagu = title
                artis = "Artis Tidak Diketahui"
                
            link = entry.get('link', [{}])[0].get('attributes', {}).get('href', '-')
            
            results.append({
                "Waktu Tarik": scraped_time,
                "Kategori": "Streaming Musik Populer",
                "Indikator / Judul Trek": judul_lagu.strip(),
                "Nilai / Artis": artis.strip(),
                "Satuan / Platform": "Apple Music ID",
                "Perubahan / Status Tren": f"Peringkat #{idx+1}",
                "Insight & Dampak": "Lagu terpopuler hari ini di Indonesia",
                "URL": link
            })
    except Exception as e:
        print(f"Gagal menarik Top Songs: {e}")

    # 2. Top Podcasts (Apple Podcasts Indonesia)
    try:
        url_podcasts = "https://itunes.apple.com/id/rss/toppodcasts/limit=5/json"
        resp = requests.get(url_podcasts, timeout=15)
        data = resp.json()
        
        entries = data.get('feed', {}).get('entry', [])
        for idx, entry in enumerate(entries):
            title = entry.get('title', {}).get('label', 'Tanpa Judul')
            if " - " in title:
                judul_podcast, podcaster = title.split(" - ", 1)
            else:
                judul_podcast = title
                podcaster = "Podcaster Tidak Diketahui"
                
            link = entry.get('link', [{}])[0].get('attributes', {}).get('href', '-')
            
            results.append({
                "Waktu Tarik": scraped_time,
                "Kategori": "Top Podcast",
                "Indikator / Judul Trek": judul_podcast.strip(),
                "Nilai / Artis": podcaster.strip(),
                "Satuan / Platform": "Apple Podcasts ID",
                "Perubahan / Status Tren": f"Peringkat #{idx+1}",
                "Insight & Dampak": "Podcast terpopuler hari ini di Indonesia",
                "URL": link
            })
    except Exception as e:
        print(f"Gagal menarik Top Podcasts: {e}")

    return results

def run_job():
    print("=== Memulai penarikan Ekonomi & Audio ===")
    scraped_time = datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S")
    
    # Kumpulkan Data
    data_finance = fetch_financial_data(scraped_time)
    data_audio = fetch_audio_podcast_data(scraped_time)
    
    all_data = data_finance + data_audio
    
    if not all_data:
        print("Gagal menarik seluruh data Ekonomi & Audio hari ini.")
        return
        
    df = pd.DataFrame(all_data)
    
    # Pastikan urutan dan nama kolom persis seperti di Google Sheets pengguna
    kolom_urut = [
        "Waktu Tarik", "Kategori", "Indikator / Judul Trek", 
        "Nilai / Artis", "Satuan / Platform", "Perubahan / Status Tren", 
        "Insight & Dampak", "URL"
    ]
    for col in kolom_urut:
        if col not in df.columns:
            df[col] = "-"
            
    df = df[kolom_urut]
    
    # Simpan ke CSV (Menimpa data lama agar AI dan GSheets selalu mendapat data fresh hari ini)
    df.to_csv(CSV_FILE, index=False)
    print(f"[SUCCESS] Tersimpan {len(df)} baris data Ekonomi & Audio ke {CSV_FILE}.")

if __name__ == "__main__":
    run_job()
```

*(Jangan lupa, agar Dashboard HTML Anda tidak berantakan setelah penyesuaian kolom ini, terapkan juga modifikasi `index.html` dari respons saya yang sebelumnya. Serta pastikan Anda melakukan **Run workflow** di tab Actions GitHub setelah semuanya tersimpan!)*
