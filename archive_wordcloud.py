import pandas as pd
import os
import re
from datetime import datetime, timezone, timedelta
from wordcloud import WordCloud

WIB = timezone(timedelta(hours=7))
scraped_time = datetime.now(WIB).strftime('%Y-%m-%d %H:%M:%S')

# Daftar kata yang akan diabaikan agar Word Cloud fokus pada Subjek/Objek penting
STOPWORDS_ID = set([
    'dan', 'di', 'yang', 'untuk', 'pada', 'ke', 'dari', 'ini', 'itu', 'dengan', 
    'dalam', 'tidak', 'akan', 'ada', 'juga', 'oleh', 'tahun', 'hari', 'saat', 
    'setelah', 'sudah', 'karena', 'bisa', 'lebih', 'atau', 'menjadi', 'lagi', 
    'hingga', 'sampai', 'sebagai', 'kepada', 'tentang', 'lalu', 'baru', 'banyak',
    'satu', 'dua', 'mereka', 'kita', 'kami', 'saya', 'dia', 'apakah', 'terkait'
])

def create_wordcloud():
    print("=== Memulai Pembuatan Word Cloud ===")
    teks_gabungan = ""
    
    # Membaca data berita nasional dan tren
    file_sumber = ['berita_news.csv', 'berita_trending.csv']
    for file in file_sumber:
        if os.path.exists(file):
            try:
                df = pd.read_csv(file)
                # Ambil kolom 'Judul' atau 'Judul Berita' atau 'Topik / Kata Kunci'
                kolom_teks = [kol for kol in df.columns if 'Judul' in kol or 'Topik' in kol]
                if kolom_teks:
                    # Gabungkan semua teks dari kolom yang relevan
                    teks = " ".join(df[kolom_teks[0]].dropna().astype(str).tolist())
                    teks_gabungan += " " + teks
            except Exception as e:
                print(f"Gagal membaca teks dari {file}: {e}")
                
    if not teks_gabungan.strip():
        print("Tidak ada teks untuk dibuatkan Word Cloud.")
        return

    # Bersihkan teks dari simbol dan angka
    teks_bersih = re.sub(r'[^a-zA-Z\s]', '', teks_gabungan.lower())

    # Generate Word Cloud
    print("Menggambar gambar Word Cloud...")
    wordcloud = WordCloud(
        width=800, 
        height=400, 
        background_color='white',
        colormap='inferno', # Skema warna cerah berapi-api
        stopwords=STOPWORDS_ID,
        max_words=100,
        contour_width=3, 
        contour_color='steelblue'
    ).generate(teks_bersih)

    # Simpan sebagai file gambar (tanpa perlu matplotlib, lebih aman di server GitHub)
    wordcloud.to_file('wordcloud.png')
    print("[SUCCESS] Berhasil menyimpan wordcloud.png")

def update_master_archive():
    print("=== Memperbarui Master Arsip Historis ===")
    master_file = 'master_arsip.csv'
    file_sumber = ['berita_news.csv', 'berita_trending.csv']
    df_list = []
    
    # 1. Baca data hari ini
    for file in file_sumber:
        if os.path.exists(file):
            try:
                df_temp = pd.read_csv(file)
                df_list.append(df_temp)
            except:
                pass
                
    if not df_list:
        return
        
    df_hari_ini = pd.concat(df_list, ignore_index=True)
    
    # 2. Buka Master Arsip (jika sudah ada)
    if os.path.exists(master_file):
        df_master = pd.read_csv(master_file)
        # Gabungkan arsip lama dengan data hari ini
        df_gabungan = pd.concat([df_master, df_hari_ini], ignore_index=True)
    else:
        df_gabungan = df_hari_ini
        
    # 3. Hapus data yang sama persis (Berdasarkan URL) agar tidak duplikat
    if 'URL' in df_gabungan.columns:
        df_gabungan = df_gabungan.drop_duplicates(subset=['URL'], keep='last')
        
    # Simpan kembali ke Master Arsip
    df_gabungan.to_csv(master_file, index=False)
    print(f"[SUCCESS] Berhasil memperbarui {master_file} dengan total {len(df_gabungan)} baris data historis.")

if __name__ == "__main__":
    create_wordcloud()
    update_master_archive()
