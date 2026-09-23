import os
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt

def create_wordcloud():
    try:
        # 1. Baca semua file CSV yang relevan
        # PERBAIKAN: Fokus pada berita hari ini agar relevan, ambil dari berita_news dan berita_trending
        df_news = pd.DataFrame()
        df_trends = pd.DataFrame()

        if os.path.exists("berita_news.csv"):
            df_news = pd.read_csv("berita_news.csv")
        
        if os.path.exists("berita_trending.csv"):
            df_trends = pd.read_csv("berita_trending.csv")

        # 2. Gabungkan teks dari judul berita
        text = ""
        if not df_news.empty and 'Judul' in df_news.columns:
             # Ambil 500 berita terbaru saja agar wordcloud update harian
            text += " ".join(df_news['Judul'].dropna().head(500).astype(str).tolist()) + " "
        
        if not df_trends.empty and 'Topik / Kata Kunci' in df_trends.columns:
            # Berikan bobot lebih untuk tren dengan mengulanginya
            trends_text = " ".join(df_trends['Topik / Kata Kunci'].dropna().astype(str).tolist())
            text += (trends_text + " ") * 3 # Bobot 3x lipat
            
        if not text.strip():
            print("Tidak ada teks untuk Word Cloud.")
            return

        # 3. Kata-kata yang diabaikan (Stopwords Bahasa Indonesia)
        stopwords = set([
            "di", "ke", "dari", "dan", "atau", "untuk", "dengan", "yang", "ini", "itu",
            "pada", "dalam", "sebagai", "oleh", "karena", "sehingga", "bahwa", "jika",
            "ada", "adalah", "saja", "juga", "sudah", "belum", "bisa", "akan", "telah",
            "saat", "setelah", "lalu", "kemudian", "namun", "tetapi", "tapi", "sedang",
            "lagi", "baru", "satu", "dua", "hari", "tahun", "bulan", "berita", "indonesia",
            "video", "foto", "nasional", "baca", "juga", "lihat", "viral", "tiktok", "trending"
        ])

        # 4. Generate Word Cloud dengan desain yang lebih segar
        wordcloud = WordCloud(
            width=1200, height=600,
            background_color='white',
            stopwords=stopwords,
            colormap='viridis', # Gunakan tema warna yang lebih modern
            min_font_size=12,
            max_words=100,
            collocations=False # Mencegah pengulangan kata berdekatan
        ).generate(text)

        # 5. Simpan gambar
        plt.figure(figsize=(12, 6), facecolor=None)
        plt.imshow(wordcloud, interpolation="bilinear")
        plt.axis("off")
        plt.tight_layout(pad=0)
        
        # Simpan dengan nama tetap agar GitHub URL tidak berubah
        plt.savefig("wordcloud.png", format="png", bbox_inches='tight', dpi=150)
        plt.close()
        print("Berhasil membuat dan menyimpan wordcloud.png yang diperbarui.")

    except Exception as e:
        print(f"Gagal membuat Word Cloud: {e}")

if __name__ == "__main__":
    create_wordcloud()
