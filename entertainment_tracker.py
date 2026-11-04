import os
import re
from datetime import datetime, timezone, timedelta
import xml.etree.ElementTree as ET
import requests
import pandas as pd

WIB = timezone(timedelta(hours=7))
CSV_HIBURAN = "film_dan_hiburan.csv"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7'
}

def fetch_tmdb_trending(scraped_time):
    tmdb_key = os.environ.get("TMDB_API_KEY", "")
    if not tmdb_key:
        print("TMDB_API_KEY tidak ditemukan. Melewati scraping TMDb.")
        return []
        
    url = f"https://api.themoviedb.org/3/trending/movie/day?api_key={tmdb_key}&language=id-ID"
    results = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        for item in data.get("results", [])[:10]:
            judul = item.get("title", item.get("original_title", ""))
            rilis = item.get("release_date", "")
            
            # Ambil poster film beresolusi tinggi dari TMDb
            poster = item.get("poster_path", "")
            img_url = f"https://image.tmdb.org/t/p/w500{poster}" if poster else ""
            
            if judul:
                results.append({
                    "Waktu Tarik": scraped_time,
                    "Sumber": "TMDb Trending",
                    "Kategori": "Film Bioskop & Box Office",
                    "Judul": judul,
                    "URL": f"https://www.themoviedb.org/movie/{item.get('id')}",
                    "Tanggal_Filter": rilis,
                    "Gambar": img_url
                })
    except Exception as e:
        print(f"Gagal menarik TMDb: {e}")
    return results

def fetch_google_news_entertainment(scraped_time):
    print("Menarik data hiburan via Google News RSS (Anti-Blokir)...")
    # Mencari berita yang relevan dengan film, bioskop, atau series Netflix di Indonesia
    url = 'https://news.google.com/rss/search?q=(film+OR+bioskop+OR+netflix+OR+series)+when:1d&hl=id&gl=ID&ceid=ID:id'
    results = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        root = ET.fromstring(resp.content)
        count = 0
        for item in root.findall('./channel/item'):
            if count >= 15: break
            raw_title = item.find('title').text if item.find('title') is not None else ''
            # Hapus nama portal/publisher di akhir judul (misal: " - detikcom")
            title = re.sub(r'\s*-\s*[^-]+$', '', raw_title).strip() 
            link = item.find('link').text if item.find('link') is not None else '-'
            pub_date = item.find('pubDate').text if item.find('pubDate') is not None else '-'
            
            # Filter kata-kata berita keras yang salah masuk ke kategori hiburan
            if any(x in title.lower() for x in ['pembunuhan', 'korupsi', 'gempa', 'banjir', 'polisi', 'kriminal']):
                continue
                
            results.append({
                "Waktu Tarik": scraped_time,
                "Sumber": "Google News Hiburan",
                "Kategori": "Berita Film & Series",
                "Judul": title,
                "URL": link,
                "Tanggal_Filter": pub_date,
                "Gambar": ""
            })
            count += 1
    except Exception as e:
        print(f"Gagal menarik Google News Hiburan: {e}")
    return results

def run_entertainment_tracker():
    print("=== Memulai penarikan Film & Hiburan ===")
    scraped_time = datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. Kumpulkan data dari kedua sumber
    data_tmdb = fetch_tmdb_trending(scraped_time)
    data_news = fetch_google_news_entertainment(scraped_time)
    
    all_data = data_tmdb + data_news
    
    if not all_data:
        print("Tidak ada data film yang berhasil ditarik.")
        # Buat file darurat jika file sebelumnya belum ada agar dashboard tidak error (Blank)
        if not os.path.exists(CSV_HIBURAN):
            df_fallback = pd.DataFrame([{"Waktu Tarik": scraped_time, "Sumber": "Sistem", "Kategori": "Peringatan", "Judul": "Data diblokir (Cloudflare)", "URL": "-"}])
            df_fallback.to_csv(CSV_HIBURAN, index=False)
        return

    df_new = pd.DataFrame(all_data)

    # 2. Penggabungan dengan data yang sudah ada (Arsip CSV)
    if os.path.exists(CSV_HIBURAN):
        try:
            df_old = pd.read_csv(CSV_HIBURAN)
            df_combined = pd.concat([df_new, df_old], ignore_index=True)
        except Exception as e:
            print(f"Gagal membaca file CSV lama: {e}")
            df_combined = df_new
    else:
        df_combined = df_new

    # 3. Hapus duplikat berdasarkan judul (hanya simpan data yang paling baru)
    df_combined = df_combined.drop_duplicates(subset=["Judul"], keep="first")
    
    # 4. URUTKAN MUTLAK BERDASARKAN WAKTU TARIK (YANG TERBARU DI BARIS 1 / PALING ATAS)
    if "Waktu Tarik" in df_combined.columns:
        df_combined = df_combined.sort_values(by="Waktu Tarik", ascending=False)
        
    # 5. Potong maksimal 50 data teratas agar file CSV tetap ringan
    df_combined = df_combined.head(50)
    
    # 6. Susun urutan kolom yang sesuai untuk dibaca oleh Dashboard HTML
    kolom_final = ["Waktu Tarik", "Sumber", "Kategori", "Judul", "URL", "Gambar"]
    for col in kolom_final:
        if col not in df_combined.columns:
            df_combined[col] = "-"
    
    df_combined = df_combined[kolom_final]
    df_combined.to_csv(CSV_HIBURAN, index=False)
    print(f"[SUCCESS] Tersimpan {len(df_combined)} data hiburan ke {CSV_HIBURAN} (Terurut dari yang paling baru)")

if __name__ == "__main__":
    run_entertainment_tracker()
