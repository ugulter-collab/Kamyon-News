"""
Trucker.Markets — Ağır Vasıta Endüstrisi Global Haber Portalı
Gemini 2.5 Flash · Google Sheets hafıza · Paralel görsel çekme · Base64 embedding
"""

import streamlit as st
import feedparser
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import gspread
from google.oauth2.service_account import Credentials
from google.genai import Client
import re
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed

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
# GLOBAL CSS — kantan.news tarzı koyu, hızlı, temiz
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Inter:wght@400;500;600;700&display=swap');

*, *::before, *::after { box-sizing: border-box; }

[data-testid="stAppViewContainer"],
[data-testid="stHeader"],
section.main,
[data-testid="stSidebar"] {
    background-color: #080b12 !important;
}

.block-container {
    max-width: 1100px !important;
    margin: 0 auto !important;
    padding: 1.8rem 1rem 4rem !important;
}

/* ── Header ── */
.tm-header { display:flex; align-items:baseline; gap:10px; margin-bottom:2px; }
.tm-logo-text {
    font-family: 'Space Mono', monospace;
    font-size: 1.9rem; font-weight:700;
    color:#f4f4f5; letter-spacing:-1.5px; line-height:1; margin:0;
}
.tm-logo-text .dot { color:#F59E0B; }
.tm-tagline {
    font-family:'Space Mono',monospace; font-size:0.65rem;
    color:#3f4760; letter-spacing:3.5px; text-transform:uppercase; margin-bottom:1.2rem;
}
.tm-divider { border:none; border-top:1px solid #151b2e; margin:0.4rem 0 1.5rem; }

/* ── Kart ── */
.tm-card {
    background:#0d1220; border:1px solid #151b2e; border-radius:12px;
    overflow:hidden; display:flex; flex-direction:column;
    transition:transform .18s ease,border-color .2s ease,box-shadow .2s ease;
    margin-bottom: 4px;
}
.tm-card:hover {
    transform:translateY(-5px); border-color:#F59E0B;
    box-shadow:0 10px 40px rgba(245,158,11,.13);
}
.tm-card-img {
    width:100%; height:190px; object-fit:cover; display:block;
    border-bottom:1px solid #151b2e; background:#111827;
}
.tm-card-img-placeholder {
    width:100%; height:190px;
    background:linear-gradient(135deg,#111827 0%,#1a2035 100%);
    display:flex; align-items:center; justify-content:center;
    font-size:2.8rem; border-bottom:1px solid #151b2e;
}
.tm-card-body { padding:13px 15px 6px; flex:1; display:flex; flex-direction:column; gap:7px; }
.tm-card-source {
    font-family:'Space Mono',monospace; font-size:0.62rem;
    color:#F59E0B; letter-spacing:1.8px; text-transform:uppercase;
}
.tm-card-title {
    font-family:'Inter',sans-serif; font-size:0.87rem; font-weight:600;
    color:#e2e4ea; line-height:1.5; flex:1;
}
.tm-card-date { font-family:'Space Mono',monospace; font-size:0.62rem; color:#2d3448; padding-bottom:4px; }

/* ── Streamlit buton override ── */
[data-testid="stButton"] > button {
    background:transparent !important; border:1px solid #1e2740 !important;
    color:#F59E0B !important; font-family:'Space Mono',monospace !important;
    font-size:0.7rem !important; letter-spacing:.8px !important;
    border-radius:7px !important; padding:5px 16px !important;
    width:100% !important;
    transition:background .15s,border-color .15s !important;
}
[data-testid="stButton"] > button:hover {
    background:#F59E0B18 !important; border-color:#F59E0B !important;
}

/* ── Tabs ── */
[data-testid="stTabs"] [role="tablist"] { border-bottom:1px solid #151b2e !important; gap:4px !important; }
[data-testid="stTabs"] button[role="tab"] {
    font-family:'Space Mono',monospace !important; font-size:0.73rem !important;
    color:#3f4760 !important; padding:6px 14px !important;
    border-radius:6px 6px 0 0 !important;
}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    color:#F59E0B !important; background:#0d1220 !important;
    border-bottom:2px solid #F59E0B !important;
}

/* ── Detay ── */
.tm-article-wrap { max-width:780px; margin:0 auto; }
.tm-article-hero {
    width:100%; max-height:420px; object-fit:cover;
    border-radius:14px; margin-bottom:24px; border:1px solid #151b2e;
}
.tm-article-category {
    font-family:'Space Mono',monospace; font-size:0.65rem;
    color:#F59E0B; letter-spacing:2.5px; text-transform:uppercase; margin-bottom:10px;
}
.tm-article-title {
    font-family:'Inter',sans-serif; font-size:1.65rem; font-weight:700;
    color:#f0f0f2; line-height:1.35; margin-bottom:14px;
}
.tm-article-meta {
    font-family:'Space Mono',monospace; font-size:0.68rem; color:#2d3448;
    margin-bottom:28px; padding-bottom:20px; border-bottom:1px solid #151b2e;
}
.tm-article-body {
    font-family:'Inter',sans-serif; font-size:1rem; line-height:1.85; color:#b8bcc8;
}
.tm-article-body p { margin-bottom:1.2rem; }
.tm-article-source {
    margin-top:32px; padding-top:20px; border-top:1px solid #151b2e;
    font-family:'Space Mono',monospace; font-size:0.65rem;
}
.tm-article-source a { color:#3f4760; text-decoration:none; }
.tm-article-source a:hover { color:#F59E0B; }

/* ── Alert ── */
[data-testid="stAlert"] {
    background:#0d1220 !important; border-color:#151b2e !important;
    color:#b8bcc8 !important; font-family:'Inter',sans-serif !important;
}

/* ── Loader çubuğu ── */
.tm-loader {
    height:2px;
    background:linear-gradient(90deg,#F59E0B,#fb923c,#F59E0B);
    background-size:200% 100%; animation:tmshimmer 1.4s ease infinite;
    border-radius:2px; margin:10px 0 20px;
}
@keyframes tmshimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }

/* ── Scrollbar ── */
::-webkit-scrollbar { width:4px; }
::-webkit-scrollbar-track { background:#080b12; }
::-webkit-scrollbar-thumb { background:#1e2740; border-radius:4px; }
::-webkit-scrollbar-thumb:hover { background:#F59E0B; }

/* ── st.image sıfırla ── */
[data-testid="stImage"] { margin:0 !important; padding:0 !important; }
[data-testid="stImage"] img { border-radius:14px !important; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# SABİT VERİLER
# ──────────────────────────────────────────────────────────────────────────────
TABS = [
    {"label": "🌟 Manşetler",       "queries": ["heavy duty trucks news 2025", "trucking industry news", "commercial truck transport news"]},
    {"label": "🇸🇪 Volvo & Scania", "queries": ["Volvo Trucks news", "Scania trucks news", "Volvo Scania heavy duty"]},
    {"label": "🇩🇪 Mercedes",       "queries": ["Mercedes Actros news", "Mercedes-Benz trucks 2025", "Mercedes heavy truck"]},
    {"label": "🇺🇸 Freightliner",   "queries": ["Freightliner trucks news", "Freightliner Cascadia 2025", "Daimler Trucks North America"]},
    {"label": "🇮🇳 BharatBenz",     "queries": ["BharatBenz trucks news", "Daimler India Commercial Vehicles", "BharatBenz heavy"]},
]

FALLBACK_IMAGES = {
    "volvo":        "https://upload.wikimedia.org/wikipedia/commons/thumb/6/64/Volvo_FH_2012.jpg/640px-Volvo_FH_2012.jpg",
    "scania":       "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/Scania_R_500_V8.jpg/640px-Scania_R_500_V8.jpg",
    "mercedes":     "https://upload.wikimedia.org/wikipedia/commons/thumb/4/44/Mercedes-Benz_Actros_2545_LS.jpg/640px-Mercedes-Benz_Actros_2545_LS.jpg",
    "actros":       "https://upload.wikimedia.org/wikipedia/commons/thumb/4/44/Mercedes-Benz_Actros_2545_LS.jpg/640px-Mercedes-Benz_Actros_2545_LS.jpg",
    "freightliner": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3e/Freightliner_Cascadia_Evolution.jpg/640px-Freightliner_Cascadia_Evolution.jpg",
    "bharatbenz":   "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b2/BharatBenz_1217C.jpg/640px-BharatBenz_1217C.jpg",
    "daimler":      "https://upload.wikimedia.org/wikipedia/commons/thumb/4/44/Mercedes-Benz_Actros_2545_LS.jpg/640px-Mercedes-Benz_Actros_2545_LS.jpg",
    "default":      "https://upload.wikimedia.org/wikipedia/commons/thumb/6/64/Volvo_FH_2012.jpg/640px-Volvo_FH_2012.jpg",
}

REJECT = ["logo", "icon", "google", "avatar", "banner", "pixel", "1x1",
          "tracking", "sprite", "blank", "placeholder", "spacer"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

SHEETS_SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
SHEET_NAME = "TruckerNews_DB"

# ──────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ──────────────────────────────────────────────────────────────────────────────
for _k, _v in {
    "view": "list", "selected_item": None,
    "cache": {}, "sheets_loaded": False,
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ──────────────────────────────────────────────────────────────────────────────
# GEMİNİ
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_gemini():
    return Client(api_key=st.secrets["GEMINI_API_KEY"])

def gemini_call(prompt: str) -> str:
    return get_gemini().models.generate_content(
        model="gemini-2.5-flash", contents=prompt
    ).text.strip()

# ──────────────────────────────────────────────────────────────────────────────
# GOOGLE SHEETS
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_sheet():
    try:
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), scopes=SHEETS_SCOPE
        )
        gc = gspread.authorize(creds)
        try:
            sh = gc.open(SHEET_NAME)
        except gspread.SpreadsheetNotFound:
            sh = gc.create(SHEET_NAME)
            sh.sheet1.append_row(["link", "tr_title", "tr_body", "image_url"])
        return sh.sheet1
    except Exception as e:
        st.warning(f"Google Sheets bağlantısı kurulamadı: {e}")
        return None

def load_cache_from_sheets():
    if st.session_state.sheets_loaded:
        return
    ws = get_sheet()
    if ws:
        try:
            for row in ws.get_all_records():
                lnk = row.get("link", "")
                if lnk:
                    st.session_state.cache[lnk] = {
                        "tr_title":  row.get("tr_title", ""),
                        "tr_body":   row.get("tr_body", ""),
                        "image_url": row.get("image_url", ""),
                    }
        except Exception:
            pass
    st.session_state.sheets_loaded = True

def save_to_sheets(link, tr_title, tr_body, image_url):
    ws = get_sheet()
    if ws:
        try:
            ws.append_row([link, tr_title, tr_body, image_url])
        except Exception:
            pass

# ──────────────────────────────────────────────────────────────────────────────
# GÖRSEL YARDIMCILARI
# ──────────────────────────────────────────────────────────────────────────────
def valid_img(url: str) -> bool:
    if not url or not url.startswith("http"):
        return False
    return not any(p in url.lower() for p in REJECT)

def fallback_url(title: str) -> str:
    low = title.lower()
    for k, v in FALLBACK_IMAGES.items():
        if k in low:
            return v
    return FALLBACK_IMAGES["default"]

def url_to_b64(url: str, timeout: int = 7) -> str:
    """
    Görseli sunucu tarafında indirip base64 data-URI'ye çevir.
    Tarayıcı bu URI'yi doğrudan render eder — CSP engeli yok, her zaman görünür.
    """
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, stream=True)
        r.raise_for_status()
        ct = r.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
        if "image" not in ct:
            return ""
        raw = r.content
        if len(raw) < 800:      # tracker piksel veya boş
            return ""
        return f"data:{ct};base64,{base64.b64encode(raw).decode()}"
    except Exception:
        return ""

def resolve_redirect(url: str) -> str:
    try:
        return requests.get(url, headers=HEADERS, allow_redirects=True, timeout=8).url
    except Exception:
        return url

def og_image_url(url: str) -> str:
    """Sayfanın OG/Twitter image URL'sini çek."""
    try:
        real = resolve_redirect(url)
        r = requests.get(real, headers=HEADERS, timeout=9)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for prop in ["og:image", "twitter:image", "og:image:secure_url"]:
            tag = (soup.find("meta", property=prop) or
                   soup.find("meta", attrs={"name": prop}))
            if tag:
                img = tag.get("content", "")
                if valid_img(img):
                    return img
        # Fallback: büyük <img>
        for tag in soup.find_all("img", src=True):
            src = tag.get("src", "")
            if src.startswith("http") and valid_img(src):
                try:
                    if int(str(tag.get("width", "0")).replace("px", "")) >= 300:
                        return src
                except Exception:
                    pass
    except Exception:
        pass
    return ""

def scrape_body(url: str) -> tuple:
    """(image_url, article_text) döner."""
    img_url, body = "", ""
    try:
        real = resolve_redirect(url)
        r = requests.get(real, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for prop in ["og:image", "twitter:image", "og:image:secure_url"]:
            tag = (soup.find("meta", property=prop) or
                   soup.find("meta", attrs={"name": prop}))
            if tag:
                img = tag.get("content", "")
                if valid_img(img):
                    img_url = img
                    break
        texts = [p.get_text(" ", strip=True)
                 for p in soup.find_all("p") if len(p.get_text(strip=True)) > 60]
        body = "\n\n".join(texts)[:4500]
    except Exception:
        pass
    return img_url, body

# ──────────────────────────────────────────────────────────────────────────────
# PARALEl GÖRSEL YÜKLEME (ana hız kazanımı)
# ──────────────────────────────────────────────────────────────────────────────
def _fetch_one_image(item: dict) -> tuple:
    """
    Tek bir haber için base64 görsel al.
    Öncelik: Sheets cache → RSS thumbnail → OG scrape → Wikipedia fallback
    """
    link = item["link"]

    # 1. Sheets cache
    cached_url = st.session_state.cache.get(link, {}).get("image_url", "")
    if cached_url:
        b64 = url_to_b64(cached_url)
        if b64:
            return link, b64

    # 2. RSS thumbnail (feedparser media:content / enclosure)
    thumb = item.get("thumbnail", "")
    if thumb and valid_img(thumb):
        b64 = url_to_b64(thumb)
        if b64:
            st.session_state.cache.setdefault(link, {})["image_url"] = thumb
            return link, b64

    # 3. OG image scrape
    og = og_image_url(link)
    if og:
        b64 = url_to_b64(og)
        if b64:
            st.session_state.cache.setdefault(link, {})["image_url"] = og
            return link, b64

    # 4. Wikipedia fallback
    fb = fallback_url(item.get("title", ""))
    return link, url_to_b64(fb, timeout=8)

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_tab_data(queries_key: str, queries: list) -> list:
    """
    RSS çek + tüm görselleri paralel indirip base64'e çevir + başlıkları al.
    ttl=1800: 30 dk cache, tekrar açıldığında anında gelir.
    """
    # ── RSS ──
    entries, seen = [], set()
    for q in queries:
        enc = quote_plus(f"{q} when:3d")
        url = f"https://news.google.com/rss/search?q={enc}&hl=en-US&gl=US&ceid=US:en"
        try:
            feed = feedparser.parse(url)
            for e in feed.entries:
                lnk = e.get("link", "")
                if lnk and lnk not in seen:
                    seen.add(lnk)
                    # RSS thumbnail dene
                    thumb = ""
                    if hasattr(e, "media_thumbnail") and e.media_thumbnail:
                        thumb = e.media_thumbnail[0].get("url", "")
                    elif hasattr(e, "enclosures") and e.enclosures:
                        for enc_e in e.enclosures:
                            if enc_e.get("type", "").startswith("image"):
                                thumb = enc_e.get("href", "")
                                break
                    entries.append({
                        "title":     e.get("title", ""),
                        "link":      lnk,
                        "published": e.get("published", "")[:16],
                        "source":    e.get("source", {}).get("title", ""),
                        "thumbnail": thumb,
                    })
        except Exception:
            continue

    entries = entries[:24]
    if not entries:
        return []

    # ── Paralel base64 görsel çekme (8 thread) ──
    img_map: dict = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = {pool.submit(_fetch_one_image, item): item for item in entries}
        for fut in as_completed(futs):
            try:
                lnk, b64 = fut.result()
                img_map[lnk] = b64
            except Exception:
                pass

    for item in entries:
        item["image_b64"] = img_map.get(item["link"], "")

    return entries

# ──────────────────────────────────────────────────────────────────────────────
# GEMİNİ ÇEVİRİ
# ──────────────────────────────────────────────────────────────────────────────
def translate_titles_bulk(items: list) -> list:
    to_tr = []
    for i, item in enumerate(items):
        cached = st.session_state.cache.get(item["link"], {})
        if cached.get("tr_title"):
            item["tr_title"] = cached["tr_title"]
        else:
            to_tr.append((i, item["title"]))

    if not to_tr:
        return items

    numbered = "\n".join(f"{i+1}. {t}" for i, (_, t) in enumerate(to_tr))
    prompt = f"""Sen profesyonel bir ağır vasıta endüstrisi çevirmensin.
Aşağıdaki numaralı İngilizce haber başlıklarını Türkçeye çevir.
- Birebir, yorumsuz çeviri yap.
- Marka/model adlarını (Volvo, Scania, Mercedes, Freightliner, BharatBenz vb.) değiştirme.
- Çıktı sadece "N. Türkçe Başlık" satırlarından oluşsun.

{numbered}"""
    try:
        raw = gemini_call(prompt)
        lines = [l.strip() for l in raw.strip().split("\n") if l.strip()]
        for idx, line in enumerate(lines):
            clean = re.sub(r"^\d+[\.\)]\s*", "", line)
            if idx < len(to_tr):
                orig_i, _ = to_tr[idx]
                items[orig_i]["tr_title"] = clean
                st.session_state.cache.setdefault(items[orig_i]["link"], {})["tr_title"] = clean
    except Exception:
        for orig_i, title in to_tr:
            items[orig_i]["tr_title"] = title
    return items

def translate_article(title: str, body: str) -> str:
    if body and len(body) > 200:
        prompt = f"""Sen profesyonel bir ağır vasıta sektörü gazetecisin.
Aşağıdaki İngilizce haber metnini Türkçeye birebir çevir.
- Yorumsuz, tarafsız, akıcı dil.
- Marka/model adlarını koru.
- Paragraf yapısını koru.
- Sadece çeviriyi yaz.

METİN:
{body}"""
    else:
        prompt = f"""Sen deneyimli bir ağır vasıta sektörü gazetecisin.
Aşağıdaki başlığa dayanarak 3-4 paragraf, bilgilendirici Türkçe haber yaz.
- Gazetecilik dili kullan.
- Marka/teknik terimleri doğru kullan.
- Sadece haber metnini yaz.

BAŞLIK: {title}"""
    try:
        return gemini_call(prompt)
    except Exception as e:
        return f"Çeviri hatası: {e}"

# ──────────────────────────────────────────────────────────────────────────────
# HEADER
# ──────────────────────────────────────────────────────────────────────────────
def render_header():
    st.markdown("""
    <div class="tm-header">
      <h1 class="tm-logo-text">🚛 Trucker<span class="dot">.Markets</span></h1>
    </div>
    <p class="tm-tagline">Global Ağır Vasıta Endüstrisi · YZ Destekli Haber Portalı</p>
    <hr class="tm-divider">
    """, unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# LİSTE GÖRÜNÜMÜ
# ──────────────────────────────────────────────────────────────────────────────
def render_list_view():
    render_header()
    tabs = st.tabs([t["label"] for t in TABS])

    for tab_idx, (tab, tab_data) in enumerate(zip(tabs, TABS)):
        with tab:
            qkey = "|".join(tab_data["queries"])

            with st.spinner("Haberler hazırlanıyor…"):
                raw = fetch_tab_data(qkey, tab_data["queries"])

            if not raw:
                st.info("Bu kategori için haber bulunamadı.")
                continue

            items = translate_titles_bulk(raw)

            for row_start in range(0, len(items), 3):
                row = items[row_start:row_start + 3]
                cols = st.columns(3)
                for ci, (col, item) in enumerate(zip(cols, row)):
                    with col:
                        _card(item, f"t{tab_idx}r{row_start}c{ci}")

def _card(item: dict, key: str):
    tr_title  = item.get("tr_title", item.get("title", ""))
    source    = item.get("source", "")
    date_str  = item.get("published", "")
    b64       = item.get("image_b64", "")

    img_html = (f'<img class="tm-card-img" src="{b64}" alt="">'
                if b64 else
                '<div class="tm-card-img-placeholder">🚛</div>')

    st.markdown(f"""
    <div class="tm-card">
      {img_html}
      <div class="tm-card-body">
        <div class="tm-card-source">{source}</div>
        <div class="tm-card-title">{tr_title}</div>
        <div class="tm-card-date">{date_str}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("Haberi Oku →", key=f"r_{key}"):
        st.session_state.selected_item = item
        st.session_state.view = "detail"
        st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# DETAY GÖRÜNÜMÜ
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
        st.rerun()

    render_header()

    tr_title = item.get("tr_title", item.get("title", ""))
    link     = item.get("link", "")
    source   = item.get("source", "")
    date_str = item.get("published", "")
    cached   = st.session_state.cache.get(link, {})

    # Hero görsel
    hero = item.get("image_b64", "")
    if not hero:
        cu = cached.get("image_url", "")
        if cu:
            hero = url_to_b64(cu) or ""
    if not hero:
        hero = url_to_b64(fallback_url(tr_title)) or ""

    st.markdown('<div class="tm-article-wrap">', unsafe_allow_html=True)
    if hero:
        st.markdown(f'<img class="tm-article-hero" src="{hero}" alt="">', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="tm-article-category">🚛 AĞIR VASITA ENDÜSTRİSİ</div>
    <div class="tm-article-title">{tr_title}</div>
    <div class="tm-article-meta">📡 {source} &nbsp;|&nbsp; 🕐 {date_str}</div>
    """, unsafe_allow_html=True)

    # ── Çift Katmanlı Hafıza ──
    if cached.get("tr_body"):
        body_html = cached["tr_body"].replace("\n", "<br>")
        st.markdown(f'<div class="tm-article-body">{body_html}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="tm-loader"></div>', unsafe_allow_html=True)
        with st.spinner("Makale çekiliyor ve Türkçeye çevriliyor…"):
            img_url, body_en = scrape_body(link)
            tr_body = translate_article(tr_title, body_en)

        final_img = img_url if valid_img(img_url) else cached.get("image_url", "")
        st.session_state.cache[link] = {
            "tr_title": tr_title, "tr_body": tr_body, "image_url": final_img,
        }
        save_to_sheets(link, tr_title, tr_body, final_img)

        st.markdown(f'<div class="tm-article-body">{tr_body.replace(chr(10), "<br>")}</div>',
                    unsafe_allow_html=True)

    st.markdown(f"""
    <div class="tm-article-source">
      🔗 Orijinal Kaynak: <a href="{link}" target="_blank">{source or link}</a>
    </div></div>
    """, unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# ANA AKIŞ
# ──────────────────────────────────────────────────────────────────────────────
def main():
    load_cache_from_sheets()
    if st.session_state.view == "detail":
        render_detail_view()
    else:
        render_list_view()

if __name__ == "__main__":
    main()
