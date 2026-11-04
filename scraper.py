# ... existing code ...
def clean_text(text):
    if not text:
        return ""
    return " ".join(text.split())

def extract_image(element):
    """Fungsi ajaib menembus lazy-loading untuk mencari URL thumbnail gambar."""
    img = element.find('img')
    if not img and element.parent:
        img = element.parent.find('img')
    if not img and element.parent and element.parent.parent:
        img = element.parent.parent.find('img')
        
    if img:
        # KUNCI: Prioritaskan atribut lazy-loading sebelum atribut 'src' standar
        url = img.get('data-src') or img.get('data-original') or img.get('src') or ""
        # Bersihkan URL jika formatnya //domain.com
        if url.startswith('//'):
            url = 'https:' + url
        return url
    return ""

def parse_detik(soup, sumber):
    articles = []
    for el in soup.find_all("a", attrs={"dtr-ttl": True}):
        title = clean_text(el.get("dtr-ttl", ""))
        link = el.get("href", "").strip()
        section = clean_text(el.get("dtr-evt", "")).title()
        article_id = el.get("dtr-id", "").strip()
        img_url = extract_image(el)

        if any(x in section.lower() for x in ["header", "footer", "menu", "logo", "login", "register"]):
            continue
        if not article_id.isdigit():
            m = re.search(r'/d-(\d+)/', link)
            if not m:
                continue

        if len(title) >= 20 and link.startswith("http"):
            articles.append({
                "Sumber": sumber,
                "Kategori": section or "Berita Utama",
                "Judul": title,
                "URL": link,
                "Gambar": img_url
            })
    return articles

def parse_grid(soup):
    articles = []
    for a in soup.find_all("a", href=True):
        link = a["href"].split("?")[0].strip()
        if "grid.id/read/" in link:
            title = clean_text(a.get("title") or a.get_text())
            img_url = extract_image(a)
            if len(title) >= 20 and "halaman" not in title.lower():
                articles.append({
                    "Sumber": "Grid.ID",
                    "Kategori": "Celebrity",
                    "Judul": title,
                    "URL": link,
                    "Gambar": img_url
                })
    return articles

def parse_okezone(soup):
    articles = []
    for a in soup.find_all("a", href=True):
        link = a["href"].split("?")[0].strip()
        if "celebrity.okezone.com/read/" in link:
            title = clean_text(a.get("title") or a.get_text())
            img_url = extract_image(a)
            if len(title) >= 20:
                articles.append({
                    "Sumber": "Okezone Celebrity",
                    "Kategori": "Celebrity",
                    "Judul": title,
                    "URL": link,
                    "Gambar": img_url
                })
    return articles

def parse_tribun(soup):
    articles = []
    for a in soup.find_all("a", href=True):
        link = a["href"].split("?")[0].strip()
        if "trends.tribunnews.com" in link and re.search(r'/\d{4}/\d{2}/\d{2}/', link):
            title = clean_text(a.get("title") or a.get_text())
            img_url = extract_image(a)
            if len(title) >= 20 and not any(x in title.lower() for x in ["halaman selanjutnya", "lihat foto", "baca juga"]):
                articles.append({
                    "Sumber": "TribunTrends",
                    "Kategori": "Infotainment",
                    "Judul": title,
                    "URL": link,
                    "Gambar": img_url
                })
    return articles

def fetch_all():
# ... existing code ...
def run_job():
    data = fetch_all()
    if not data:
        logging.warning("Tidak ada data yang ditemukan.")
        return

    df_new = pd.DataFrame(data).drop_duplicates(subset=["URL"])

    if "Gambar" not in df_new.columns:
        df_new["Gambar"] = ""

    # 1. Pastikan urutan kolom: 'Waktu Tarik' paling kiri
    kolom_urut = ["Waktu Tarik", "Sumber", "Kategori", "Judul", "URL", "Gambar"]
    df_new = df_new[kolom_urut]

    # 2. Tulis ulang (overwrite) file CSV agar data lama langsung diganti dengan data baru yang bersih
    df_new.to_csv(CSV_FILE, index=False)
    logging.info(f"Berhasil memperbarui {len(df_new)} berita terbaru.")

if __name__ == "__main__":
    run_job()
