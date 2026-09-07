import pandas as pd
import os
import re
from textblob import TextBlob

# Definisi kata kunci sentimen Indonesia sederhana (Lexicon-based)
# Karena TextBlob asli berbahasa Inggris, kita kombinasikan dengan kamus manual 
# untuk menangani konteks berita Indonesia dengan lebih cepat tanpa membebani server GitHub.

KATA_POSITIF = [
    'bantuan', 'sukses', 'cemerlang', 'menang', 'untung', 'naik', 'turun harga', 'solusi', 
    'prestasi', 'juara', 'aman', 'lancar', 'sembuh', 'gratis', 'diskon', 'bebas', 'merdeka',
    'bantu', 'dukung', 'sepakat', 'damai', 'sejahtera', 'pulih', 'berhasil', 'inovasi'
]

KATA_NEGATIF = [
    'korupsi', 'bencana', 'tewas', 'demo', 'tolak', 'rugi', 'turun', 'anjlok', 'krisis',
    'darurat', 'bahaya', 'ancaman', 'bunuh', 'mati', 'sakit', 'wabah', 'gagal', 'pecat',
    'kecelakaan', 'macet', 'banjir', 'gempa', 'panik', 'takut', 'marah', 'protes', 'kasus'
]

def analyze_indonesian_sentiment(text):
    if not isinstance(text, str) or not text:
        return 'Netral', 0.0

    text_lower = text.lower()
    
    # 1. Coba pendekatan kamus (Lexicon) lokal dulu
    skor_positif = sum(1 for kata in KATA_POSITIF if re.search(rf'\b{kata}\b', text_lower))
    skor_negatif = sum(1 for kata in KATA_NEGATIF if re.search(rf'\b{kata}\b', text_lower))
    
    # Hitung sentimen lokal
    if skor_positif > skor_negatif:
        return 'Positif', (skor_positif / (skor_positif + skor_negatif)) * 100
    elif skor_negatif > skor_positif:
        return 'Negatif', (skor_negatif / (skor_positif + skor_negatif)) * -100
        
    # 2. Jika kamus lokal seimbang/kosong, gunakan TextBlob sebagai fallback
    # (Catatan: TextBlob kurang akurat untuk BI murni tanpa terjemahan, 
    # tapi cukup untuk menangkap polaritas umum jika ada kata serapan)
    try:
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        
        if polarity > 0.1:
            return 'Positif', polarity * 100
        elif polarity < -0.1:
            return 'Negatif', polarity * 100
        else:
            return 'Netral', 0.0
    except:
        return 'Netral', 0.0

def process_csv_sentiment(filename, text_column='Judul'):
    if not os.path.exists(filename):
        print(f"File {filename} tidak ditemukan. Melewati analisis.")
        return False
        
    print(f"Menganalisis sentimen untuk file: {filename}")
    
    try:
        # Baca CSV
        df = pd.read_csv(filename)
        
        # Cek apakah kolom teks ada
        if text_column not in df.columns:
            # Jika kolom 'Judul' tidak ada, coba cari alternatif (misal di file tren namanya beda)
            if 'Judul Berita' in df.columns:
                text_column = 'Judul Berita'
            else:
                print(f"Kolom {text_column} tidak ditemukan di {filename}.")
                return False
                
        # Terapkan fungsi analisis sentimen
        results = df[text_column].apply(analyze_indonesian_sentiment)
        
        # Pisahkan hasil tuple menjadi dua kolom baru
        df['Sentimen'] = [res[0] for res in results]
        df['Skor Sentimen'] = [round(res[1], 2) for res in results]
        
        # Simpan kembali ke CSV (menimpa file lama)
        df.to_csv(filename, index=False)
        print(f"[SUCCESS] Kolom Sentimen ditambahkan ke {filename}.")
        return True
        
    except Exception as e:
        print(f"[ERROR] Gagal memproses {filename}: {e}")
        return False

def main():
    print("=== Memulai Pipeline Analisis Sentimen NLP ===")
    
    # Daftar file yang ingin dianalisis
    target_files = [
        'berita_news.csv',      # Berita Nasional
        'berita_terkini.csv',   # Berita Hiburan/Selebriti
        'berita_trending.csv'   # Tren Portal/Sosmed
    ]
    
    for file in target_files:
        process_csv_sentiment(file)
        
    print("=== Analisis Sentimen Selesai ===")

if __name__ == "__main__":
    main()
