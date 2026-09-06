import requests
import pandas as pd
from pytrends.request import TrendReq
from datetime import datetime, timezone, timedelta
import os
import time

# --- KONFIGURASI WAKTU ---
WIB = timezone(timedelta(hours=7))
scraped_time = datetime.now(WIB).strftime('%Y-%m-%d %H:%M:%S')

# --- MASUKKAN API KEY TMDB ANDA DI SINI ---
# Ganti teks 'MASUKKAN_API_KEY_ANDA_DISINI' dengan API Key dari akun TMDb Anda.
TMDB_API_KEY = '07c788e9f2fed481316aca80d719d8f4' 

def fetch_trending_movies_indonesia():
    print("Menarik data Film Trending dari TMDb...")
    # Menarik tren harian (bisa diganti 'week' untuk tren mingguan)
    url = f"https://api.themoviedb.org/3/trending/movie/day?api_key={TMDB_API_KEY}&language=id-ID&region=ID"
    movies_data = []
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        results = response.json().get('results', [])
        
        for idx, movie in enumerate(results, 1):
            movies_data.append({
                'Waktu Tarik': scraped_time,
                'Peringkat': idx,
                'Kategori': 'Film (TMDb)',
                'Judul': movie.get('title') or movie.get('original_title'),
                'Popularitas': movie.get('popularity'),
                'Tanggal Rilis': movie.get('release_date'),
                'Sinopsis Singkat': movie.get('overview', '')[:100] + '...' if movie.get('overview') else 'Tidak ada sinopsis',
            })
    except Exception as e:
        print(f"Gagal menarik data TMDb: {e}")
        
    return movies_data

def fetch_google_trends_searches():
    print("Menarik data Pencarian Teratas Google Trends (Consumer View)...")
    trends_data = []
    try:
        # Pytrends kadang butuh waktu/retry karena limitasi Google
        pytrend = TrendReq(hl='id-ID', tz=-420) # tz -420 adalah offset untuk WIB (UTC+7)
        
        # Mengambil trending searches khusus untuk Indonesia ('indonesia')
        trending_df = pytrend.trending_searches(pn='indonesia')
        
        # Pytrends mengembalikan DataFrame dengan satu kolom (indeks 0).
        for idx, row in trending_df.iterrows():
            if idx >= 15: # Ambil Top 15 saja
                break
            keyword = row[0]
            trends_data.append({
                'Waktu Tarik': scraped_time,
                'Peringkat': idx + 1,
                'Kategori': 'Penelusuran Web (Google)',
                'Judul': keyword.title(),
                'Popularitas': 'Trending Hari Ini',
                'Tanggal Rilis': datetime.now(WIB).strftime('%Y-%m-%d'),
                'Sinopsis Singkat': f"Topik pencarian: {keyword}"
            })
            
    except Exception as e:
        print(f"Gagal menarik data Google Trends: {e}")
        
    return trends_data

def main():
    all_data = []
    
    # 1. Tarik Film
    if TMDB_API_KEY != 'MASUKKAN_API_KEY_ANDA_DISINI':
        movies = fetch_trending_movies_indonesia()
        all_data.extend(movies)
    else:
        print("PERINGATAN: TMDB_API_KEY belum diisi. Lewati penarikan data film.")
        
    # Jeda sejenak sebelum request ke Google
    time.sleep(2)
    
    # 2. Tarik Opini/Pencarian Publik
    searches = fetch_google_trends_searches()
    all_data.extend(searches)
    
    if all_data:
        df = pd.DataFrame(all_data)
        file_name = 'hiburan_dan_opini.csv'
        df.to_csv(file_name, index=False)
        print(f"[SUCCESS] Berhasil menyimpan {len(df)} baris data ke {file_name}")
    else:
        print("Tidak ada data yang berhasil ditarik.")

if __name__ == "__main__":
    main()
