"""
Trucker.Markets — Ağır Vasıta Endüstrisi Global Haber Portalı
Gemini 2.5 Flash + Google Sheets çift katmanlı hafıza mimarisi
"""

import streamlit as st
import feedparser
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urlparse
import gspread
from google.oauth2.service_account import Credentials
from google.genai import Client
import json
import time
import re

# ──────────────────────────────────────────────────────────────────────────────
# SAYFA YAPISI
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Trucker.Markets",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ──────────────────────────────────────────────────────────────────────────────
# GLOBAL CSS — Kantan Dark Style
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Genel Arka Plan ── */
[data-testid="stAppViewContainer"],
[data-testid="stHeader"],
section.main {
    background-color: #0e1117 !important;
}
[data-testid="stSidebar"] { background-color: #0e1117 !important; }

/* ── İçerik Genişliği Kısıtlama ── */
.block-container {
    max-width: 1100px !important;
    margin: 0 auto !important;
    padding-top: 1.5rem !important;
    padding-bottom: 3rem !important;
}

/* ── Logo / Başlık Alanı ── */
.portal-header {
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 0.2rem;
}
.portal-logo {
    font-size: 2.6rem;
    line-height: 1;
}
.portal-title {
    font-family: 'Courier New', monospace;
    font-size: 2.1rem;
    font-weight: 800;
    letter-spacing: -1px;
    color: #f0f0f0;
    margin: 0;
}
.portal-title span {
    color: #FFC107;
}
.portal-subtitle {
    font-family: 'Courier New', monospace;
    font-size: 0.78rem;
    color: #666;
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-bottom: 1.4rem;
}
.portal-divider {
    border: none;
    border-top: 1px solid #1e2330;
    margin: 0.3rem 0 1.4rem 0;
}

/* ── Haber Kartı ── */
.news-card {
    background: #13161f;
    border: 1px solid #1e2330;
    border-radius: 10px;
    overflow: hidden;
    cursor: pointer;
    transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
    height: 100%;
    display: flex;
    flex-direction: column;
}
.news-card:hover {
    transform: translateY(-4px);
    border-color: #FFC107;
    box-shadow: 0 8px 32px rgba(255, 193, 7, 0.12);
}
.news-card img {
    width: 100%;
    height: 185px;
    object-fit: cover;
    display: block;
    border-bottom: 1px solid #1e2330;
}
.card-body {
    padding: 12px 14px 14px;
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 6px;
}
.card-source {
    font-size: 0.68rem;
    color: #FFC107;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    font-family: 'Courier New', monospace;
}
.card-title {
    font-size: 0.88rem;
    font-weight: 600;
    color: #e8e8e8;
    line-height: 1.45;
    font-family: 'Segoe UI', sans-serif;
    flex: 1;
}
.card-date {
    font-size: 0.68rem;
    color: #444;
    font-family: 'Courier New', monospace;
}

/* ── Detay Sayfası ── */
.article-header {
    background: linear-gradient(135deg, #13161f 0%, #1a1e2a 100%);
    border: 1px solid #1e2330;
    border-radius: 12px;
    padding: 28px 32px;
    margin-bottom: 1.5rem;
}
.article-title {
    font-size: 1.55rem;
    font-weight: 700;
    color: #f0f0f0;
    line-height: 1.4;
    margin-bottom: 10px;
    font-family: 'Segoe UI', sans-serif;
}
.article-meta {
    font-size: 0.75rem;
    color: #FFC107;
    font-family: 'Courier New', monospace;
    letter-spacing: 1px;
}
.article-body {
    font-size: 0.97rem;
    line-height: 1.8;
    color: #cdd0d8;
    font-family: 'Segoe UI', sans-serif;
    background: #13161f;
    border: 1px solid #1e2330;
    border-radius: 12px;
    padding: 28px 32px;
}
.article-body p {
    margin-bottom: 1rem;
}

/* ── Yükleniyor animasyonu ── */
.loading-bar {
    height: 3px;
    background: linear-gradient(90deg, #FFC107, #FF6B35, #FFC107);
    background-size: 200% 100%;
    animation: shimmer 1.2s infinite;
    border-radius: 3px;
    margin-bottom: 1rem;
}
@keyframes shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

/* ── Tab özelleştirme ── */
[data-testid="stTabs"] button {
    font-family: 'Courier New', monospace !important;
    font-size: 0.8rem !important;
    color: #666 !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #FFC107 !important;
    border-bottom-color: #FFC107 !important;
}

/* ── Geri Butonu ── */
.back-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: #FFC107;
    font-family: 'Courier New', monospace;
    font-size: 0.8rem;
    cursor: pointer;
    text-decoration: none;
    padding: 6px 12px;
    border: 1px solid #2a2f3e;
    border-radius: 6px;
    margin-bottom: 1.2rem;
    transition: border-color 0.15s;
}
.back-btn:hover { border-color: #FFC107; }

/* ── Genel buton rengi ── */
[data-testid="stButton"] button {
    background: #1a1e2a !important;
    color: #FFC107 !important;
    border: 1px solid #2a2f3e !important;
    font-family: 'Courier New', monospace !important;
    font-size: 0.78rem !important;
    border-radius: 6px !important;
    padding: 4px 14px !important;
    transition: border-color 0.15s, box-shadow 0.15s !important;
}
[data-testid="stButton"] button:hover {
    border-color: #FFC107 !important;
    box-shadow: 0 0 8px rgba(255,193,7,0.2) !important;
}

/* ── Info/warning kutuları ── */
[data-testid="stAlert"] {
    background: #13161f !important;
    border-color: #2a2f3e !important;
    color: #cdd0d8 !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: #0e1117; }
::-webkit-scrollbar-thumb { background: #2a2f3e; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# SABİT VERİLER
# ──────────────────────────────────────────────────────────────────────────────
TABS = [
    {
        "label": "🌟 Manşetler",
        "queries": ["heavy duty trucks news", "trucking industry news", "commercial trucks 2025"],
    },
    {
        "label": "🇸🇪 Volvo & Scania",
        "queries": ["Volvo Trucks news", "Scania trucks news", "Volvo Scania heavy transport"],
    },
    {
        "label": "🇩🇪 Mercedes",
        "queries": ["Mercedes Actros news", "Mercedes-Benz trucks", "Mercedes heavy duty truck"],
    },
    {
        "label": "🇺🇸 Freightliner",
        "queries": ["Freightliner trucks news", "Daimler Trucks North America", "Freightliner Cascadia"],
    },
    {
        "label": "🇮🇳 BharatBenz",
        "queries": ["BharatBenz trucks news", "Daimler India Commercial Vehicles", "BharatBenz heavy truck"],
    },
]

# Kurtarıcı Wikipedia resimleri (anahtar kelime → URL)
FALLBACK_IMAGES = {
    "volvo":       "https://upload.wikimedia.org/wikipedia/commons/thumb/6/64/Volvo_FH_2012.jpg/320px-Volvo_FH_2012.jpg",
    "scania":      "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/Scania_R_500_V8.jpg/320px-Scania_R_500_V8.jpg",
    "mercedes":    "https://upload.wikimedia.org/wikipedia/commons/thumb/4/44/Mercedes-Benz_Actros_2545_LS.jpg/320px-Mercedes-Benz_Actros_2545_LS.jpg",
    "actros":      "https://upload.wikimedia.org/wikipedia/commons/thumb/4/44/Mercedes-Benz_Actros_2545_LS.jpg/320px-Mercedes-Benz_Actros_2545_LS.jpg",
    "freightliner":"https://upload.wikimedia.org/wikipedia/commons/thumb/3/3e/Freightliner_Cascadia_Evolution.jpg/320px-Freightliner_Cascadia_Evolution.jpg",
    "bharatbenz":  "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b2/BharatBenz_1217C.jpg/320px-BharatBenz_1217C.jpg",
    "daimler":     "https://upload.wikimedia.org/wikipedia/commons/thumb/4/44/Mercedes-Benz_Actros_2545_LS.jpg/320px-Mercedes-Benz_Actros_2545_LS.jpg",
    "man":         "https://upload.wikimedia.org/wikipedia/commons/thumb/5/57/MAN_TGX_18.440.jpg/320px-MAN_TGX_18.440.jpg",
    "iveco":       "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8c/Iveco_Stralis_AS_440S50.jpg/320px-Iveco_Stralis_AS_440S50.jpg",
    "default":     "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b9/Above_Gotham.jpg/320px-Above_Gotham.jpg",
}

REJECT_PATTERNS = ["logo", "icon", "google", "avatar", "banner", "ad", "sprite", "pixel", "1x1", "tracking"]
SHEETS_SCOPE    = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
SHEET_NAME      = "TruckerNews_DB"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# ──────────────────────────────────────────────────────────────────────────────
# SESSION STATE BAŞLANGICI
# ──────────────────────────────────────────────────────────────────────────────
def init_session():
    defaults = {
        "view":           "list",      # "list" | "detail"
        "selected_item":  None,
        "translated_article": None,
        "cache":          {},           # link → {"tr_title": ..., "tr_body": ..., "image": ...}
        "sheets_loaded":  False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()

# ──────────────────────────────────────────────────────────────────────────────
# GEMİNİ İSTEMCİSİ
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_gemini_client():
    api_key = st.secrets["GEMINI_API_KEY"]
    return Client(api_key=api_key)

def gemini_translate(prompt: str, max_tokens: int = 2048) -> str:
    client = get_gemini_client()
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text.strip()

# ──────────────────────────────────────────────────────────────────────────────
# GOOGLE SHEETS BAĞLANTISI
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_sheet():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=SHEETS_SCOPE)
        gc = gspread.authorize(creds)
        try:
            sh = gc.open(SHEET_NAME)
            worksheet = sh.sheet1
        except gspread.SpreadsheetNotFound:
            sh = gc.create(SHEET_NAME)
            worksheet = sh.sheet1
            worksheet.append_row(["link", "tr_title", "tr_body", "image_url"])
        return worksheet
    except Exception as e:
        st.warning(f"Google Sheets bağlantısı kurulamadı: {e}")
        return None

def load_cache_from_sheets():
    """Sheets'ten cache'i RAM'e yükle (uygulama açılışında bir kez)."""
    if st.session_state.sheets_loaded:
        return
    ws = get_sheet()
    if ws is None:
        st.session_state.sheets_loaded = True
        return
    try:
        rows = ws.get_all_records()
        for row in rows:
            link = row.get("link", "")
            if link:
                st.session_state.cache[link] = {
                    "tr_title": row.get("tr_title", ""),
                    "tr_body":  row.get("tr_body", ""),
                    "image":    row.get("image_url", ""),
                }
    except Exception:
        pass
    st.session_state.sheets_loaded = True

def save_to_sheets(link: str, tr_title: str, tr_body: str, image_url: str):
    """Yeni çeviriyi Sheets'e yaz."""
    ws = get_sheet()
    if ws is None:
        return
    try:
        ws.append_row([link, tr_title, tr_body, image_url])
    except Exception:
        pass

# ──────────────────────────────────────────────────────────────────────────────
# RSS / HABER ÇEKME
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=1800)
def fetch_news(queries: list) -> list:
    """Birden fazla sorgu için Google News RSS'ten haber çek, birleştir."""
    entries = []
    seen_links = set()
    for q in queries:
        encoded = quote_plus(f"{q} when:3d")
        url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                link = entry.get("link", "")
                if link and link not in seen_links:
                    seen_links.add(link)
                    entries.append({
                        "title":     entry.get("title", ""),
                        "link":      link,
                        "published": entry.get("published", ""),
                        "source":    entry.get("source", {}).get("title", ""),
                    })
        except Exception:
            continue
    return entries[:30]  # Maksimum 30 haber

# ──────────────────────────────────────────────────────────────────────────────
# AKILLI GÖRSEL VE MAKALE KAZIYICI
# ──────────────────────────────────────────────────────────────────────────────
def resolve_redirect(url: str, timeout: int = 8) -> str:
    """Google News yönlendirmesini çöz, orijinal URL'e ulaş."""
    try:
        r = requests.get(url, headers=HEADERS, allow_redirects=True, timeout=timeout)
        return r.url
    except Exception:
        return url

def is_valid_image(url: str) -> bool:
    if not url:
        return False
    url_lower = url.lower()
    for pat in REJECT_PATTERNS:
        if pat in url_lower:
            return False
    # Geçerli resim uzantısı veya CDN paterni
    return True

def get_fallback_image(title: str) -> str:
    title_lower = title.lower()
    for key, img_url in FALLBACK_IMAGES.items():
        if key in title_lower:
            return img_url
    return FALLBACK_IMAGES["default"]

@st.cache_data(ttl=3600, show_spinner=False)
def scrape_article(url: str) -> dict:
    """
    Orijinal makale sayfasından OG görseli + tam metni çek.
    Döner: {"image": str, "body": str}
    """
    result = {"image": "", "body": ""}
    try:
        real_url = resolve_redirect(url)
        r = requests.get(real_url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # OG / Twitter görsel
        for prop in ["og:image", "twitter:image"]:
            tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
            if tag:
                img = tag.get("content", "")
                if is_valid_image(img):
                    result["image"] = img
                    break

        # Makale metni — <p> etiketlerini topla
        paragraphs = soup.find_all("p")
        texts = []
        for p in paragraphs:
            t = p.get_text(separator=" ", strip=True)
            if len(t) > 60:  # Çok kısa parçaları at
                texts.append(t)
        full_text = "\n\n".join(texts)
        result["body"] = full_text[:4500]

    except Exception:
        pass

    return result

# ──────────────────────────────────────────────────────────────────────────────
# GEMİNİ ÇEVİRİ FONKSİYONLARI
# ──────────────────────────────────────────────────────────────────────────────
def translate_titles_bulk(items: list) -> list:
    """
    Tüm İngilizce başlıkları tek bir Gemini çağrısıyla Türkçeye çevir.
    items: [{"title": ..., "link": ..., ...}, ...]
    Döner: aynı liste, tr_title alanı eklenmiş.
    """
    # Cache'te olanları atla
    to_translate = []
    for i, item in enumerate(items):
        cached = st.session_state.cache.get(item["link"])
        if cached and cached.get("tr_title"):
            item["tr_title"] = cached["tr_title"]
        else:
            to_translate.append((i, item["title"]))

    if not to_translate:
        return items

    # Toplu çeviri prompt
    numbered = "\n".join([f"{idx+1}. {title}" for idx, (_, title) in enumerate(to_translate)])
    prompt = f"""Sen profesyonel bir ağır vasıta endüstrisi haberlerini Türkçeye çeviren bir çevirmensin.
Aşağıdaki numaralı İngilizce haber başlıklarını Türkçeye çevir.
KURALLAR:
- Birebir, yorumsuz çeviri yap.
- Marka/model adlarını (Volvo, Scania, Mercedes, Freightliner, BharatBenz, vb.) olduğu gibi bırak.
- Her satır "N. Türkçe Başlık" formatında olsun, başka hiçbir şey yazma.

{numbered}"""

    try:
        raw = gemini_translate(prompt)
        lines = [l.strip() for l in raw.strip().split("\n") if l.strip()]
        for idx, line in enumerate(lines):
            # "1. Başlık" → "Başlık"
            clean = re.sub(r"^\d+[\.\)]\s*", "", line)
            if idx < len(to_translate):
                original_idx, _ = to_translate[idx]
                items[original_idx]["tr_title"] = clean
    except Exception:
        # Çeviri başarısız olursa orijinal başlığı kullan
        for original_idx, title in to_translate:
            items[original_idx]["tr_title"] = title

    return items

def translate_article(title: str, body: str) -> str:
    """Makale metnini Türkçeye çevir veya başlıktan üret."""
    if body and len(body) > 200:
        prompt = f"""Sen profesyonel bir ağır vasıta sektörü gazetecisin ve haber çevirisi yapıyorsun.
Aşağıdaki İngilizce haber metnini Türkçeye birebir çevir.
- Yorumsuz, tarafsız ve akıcı bir dille çevir.
- Teknik terimler ve marka adlarını (Volvo, Scania, Mercedes, Freightliner, BharatBenz, vb.) koru.
- Paragraf yapısını koru.
- Çevirinin dışında hiçbir şey yazma.

HABER METNİ:
{body}"""
    else:
        prompt = f"""Sen deneyimli bir ağır vasıta sektörü gazetecisin.
Aşağıdaki haber başlığına dayanarak, 3-4 paragraftan oluşan, bilgilendirici ve gerçekçi bir Türkçe haber metni yaz.
- Sektörel gazetecilik dili kullan.
- Marka adlarını ve teknik terimleri doğru kullan.
- Sadece haber metnini yaz, başka hiçbir şey ekleme.

BAŞLIK: {title}"""

    try:
        return gemini_translate(prompt, max_tokens=2048)
    except Exception as e:
        return f"Çeviri sırasında bir hata oluştu: {e}"

# ──────────────────────────────────────────────────────────────────────────────
# PORTAL HEADER
# ──────────────────────────────────────────────────────────────────────────────
def render_header():
    st.markdown("""
    <div class="portal-header">
        <div class="portal-logo">🚛</div>
        <h1 class="portal-title">Trucker<span>.Markets</span></h1>
    </div>
    <p class="portal-subtitle">Global Ağır Vasıta Endüstrisi Haber Portalı · Yapay Zeka Destekli</p>
    <hr class="portal-divider">
    """, unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# HABER LİSTESİ GÖRÜNÜMÜ
# ──────────────────────────────────────────────────────────────────────────────
def render_news_card(item: dict, col_key: str):
    """Tek bir haber kartı render eder."""
    image_url = ""

    # Cache'te görsel var mı?
    cached = st.session_state.cache.get(item["link"], {})
    if cached.get("image"):
        image_url = cached["image"]

    # Yok ise fallback
    if not image_url:
        image_url = get_fallback_image(item.get("tr_title", item.get("title", "")))

    tr_title = item.get("tr_title", item.get("title", ""))
    source   = item.get("source", "")
    date_str = item.get("published", "")[:16] if item.get("published") else ""

    # Kart HTML
    card_html = f"""
    <div class="news-card">
        <img src="{image_url}" alt="{tr_title}" onerror="this.src='https://upload.wikimedia.org/wikipedia/commons/thumb/b/b9/Above_Gotham.jpg/320px-Above_Gotham.jpg'">
        <div class="card-body">
            <div class="card-source">{source}</div>
            <div class="card-title">{tr_title}</div>
            <div class="card-date">{date_str}</div>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

    if st.button("Haberi Oku →", key=f"btn_{col_key}_{item['link'][-20:]}"):
        st.session_state.selected_item = item
        st.session_state.translated_article = None
        st.session_state.view = "detail"
        st.rerun()

def render_list_view():
    render_header()
    tab_labels = [t["label"] for t in TABS]
    tabs = st.tabs(tab_labels)

    for tab_idx, (tab, tab_data) in enumerate(zip(tabs, TABS)):
        with tab:
            with st.spinner("Haberler yükleniyor..."):
                raw_items = fetch_news(tab_data["queries"])

            if not raw_items:
                st.info("Bu kategori için haber bulunamadı.")
                continue

            # Toplu çeviri (önce cache'e bak)
            items = translate_titles_bulk(raw_items)

            # 3'lü grid
            for row_start in range(0, len(items), 3):
                row_items = items[row_start:row_start + 3]
                cols = st.columns(3)
                for ci, (col, item) in enumerate(zip(cols, row_items)):
                    with col:
                        render_news_card(item, f"t{tab_idx}r{row_start}c{ci}")

# ──────────────────────────────────────────────────────────────────────────────
# DETAY SAYFASI
# ──────────────────────────────────────────────────────────────────────────────
def render_detail_view():
    item = st.session_state.selected_item
    if not item:
        st.session_state.view = "list"
        st.rerun()
        return

    if st.button("← Ana Sayfaya Dön"):
        st.session_state.view = "list"
        st.session_state.selected_item = None
        st.session_state.translated_article = None
        st.rerun()

    render_header()

    tr_title = item.get("tr_title", item.get("title", ""))
    link     = item.get("link", "")
    source   = item.get("source", "")
    date_str = item.get("published", "")[:16] if item.get("published") else ""

    # Görsel
    image_url = st.session_state.cache.get(link, {}).get("image", "")
    if not image_url:
        image_url = get_fallback_image(tr_title)

    # Başlık ve görsel
    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown(f"""
        <div class="article-header">
            <div class="article-title">{tr_title}</div>
            <div class="article-meta">📡 {source} &nbsp;|&nbsp; 🕐 {date_str}</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f'<a href="{link}" target="_blank" style="font-family:Courier New;font-size:0.75rem;color:#555;">🔗 Orijinal Kaynak</a>', unsafe_allow_html=True)
    with c2:
        st.image(image_url, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Çift Katmanlı Hafıza: Önce RAM cache ──
    cached = st.session_state.cache.get(link, {})
    if cached.get("tr_body"):
        # RAM'de var → anında göster
        body_html = cached["tr_body"].replace("\n", "<br>")
        st.markdown(f'<div class="article-body">{body_html}</div>', unsafe_allow_html=True)
        return

    # ── Cache yok: Çeviri yap ──
    with st.spinner("🔄 Makale çekiliyor ve Türkçeye çevriliyor..."):
        st.markdown('<div class="loading-bar"></div>', unsafe_allow_html=True)

        # 1. Makale kazı
        scraped = scrape_article(link)
        body_en = scraped.get("body", "")
        scraped_image = scraped.get("image", "")

        # Görseli güncelle
        if scraped_image and is_valid_image(scraped_image):
            final_image = scraped_image
        else:
            final_image = image_url

        # 2. Gemini çeviri
        tr_body = translate_article(tr_title, body_en)

    # 3. Hem RAM hem Sheets'e kaydet
    st.session_state.cache[link] = {
        "tr_title": tr_title,
        "tr_body":  tr_body,
        "image":    final_image,
    }
    save_to_sheets(link, tr_title, tr_body, final_image)

    # 4. Göster
    body_html = tr_body.replace("\n", "<br>")
    st.markdown(f'<div class="article-body">{body_html}</div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# ANA AKIŞ
# ──────────────────────────────────────────────────────────────────────────────
def main():
    # Uygulama açılışında Sheets'ten cache yükle (bir kez)
    load_cache_from_sheets()

    if st.session_state.view == "detail":
        render_detail_view()
    else:
        render_list_view()

if __name__ == "__main__":
    main()
