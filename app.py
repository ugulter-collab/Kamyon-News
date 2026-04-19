import streamlit as st
from google import genai
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import urllib.parse
import gspread
from google.oauth2.service_account import Credentials

# ==========================================
# 1. GÜVENLİK VE API BAĞLANTILARI
# ==========================================
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    st.error("Secrets bulunamadı. Lütfen Cloud panelini kontrol edin.")
    st.stop()

client = genai.Client(api_key=GEMINI_API_KEY)

@st.cache_resource
def get_database():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        gc = gspread.authorize(creds)
        return gc.open("TruckerNews_DB").sheet1
    except Exception:
        return None

sheet = get_database()

# ==========================================
# 2. RAM HAFIZASI (VERİTABANINI TEK SEFERDE OKU)
# ==========================================
if 'mevcut_raporlar' not in st.session_state:
    st.session_state.mevcut_raporlar = {}
    if sheet:
        try:
            for row in sheet.get_all_records():
                st.session_state.mevcut_raporlar[row.get("Link")] = row.get("Analiz")
        except: pass

# ==========================================
# 3. GELİŞMİŞ GÖRSEL BULUCU
# ==========================================
@st.cache_data(ttl=900)
def resim_bul(google_news_url, baslik=""):
    yasakli = ['logo', 'icon', 'favicon', 'google', 'gstatic', 'avatar', 'news.google', 'blank']
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        r_init = requests.get(google_news_url, headers=headers, timeout=5, allow_redirects=True)
        final_url = r_init.url
        
        r = requests.get(final_url, headers=headers, timeout=7)
        soup = BeautifulSoup(r.content, 'html.parser')
        
        meta = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
        if meta and meta.get("content"):
            img_url = urllib.parse.urljoin(final_url, meta["content"])
            if not any(x in img_url.lower() for x in yasakli): return img_url
            
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src')
            if src and 'http' in src:
                if not any(x in src.lower() for x in yasakli): return src
    except: pass
    
    b = baslik.lower()
    if "volvo" in b: return "https://upload.wikimedia.org/wikipedia/commons/thumb/7/77/Volvo_FH_500.jpg/800px-Volvo_FH_500.jpg"
    if "scania" in b: return "https://upload.wikimedia.org/wikipedia/commons/thumb/2/25/Scania_R500_V8.jpg/800px-Scania_R500_V8.jpg"
    if "mercedes" in b: return "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Mercedes-Benz_Actros_1845.jpg/800px-Mercedes-Benz_Actros_1845.jpg"
    if "freightliner" in b: return "https://upload.wikimedia.org/wikipedia/commons/thumb/3/30/Freightliner_Cascadia_Evolution.jpg/800px-Freightliner_Cascadia_Evolution.jpg"
    if "bharat" in b: return "https://upload.wikimedia.org/wikipedia/commons/thumb/0/00/Tata_Prima_4928_S.jpg/800px-Tata_Prima_4928_S.jpg"
    return "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/MAN_TGX_18.440_XXL.jpg/800px-MAN_TGX_18.440_XXL.jpg"

# ==========================================
# 4. YAPAY ZEKA MOTORU
# ==========================================
def rapor_hazirla(link, baslik):
    if link in st.session_state.mevcut_raporlar:
        return st.session_state.mevcut_raporlar[link]

    prompt = f"Sen bir ağır vasıta piyasa analistisin. Şu haberi müşteri gözüyle değerlendiren kısa, ferah, Türkçe bir rapor yaz: {baslik}"
    try:
        cevap = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        if sheet: sheet.append_row([link, cevap.text])
        st.session_state.mevcut_raporlar[link] = cevap.text 
        return cevap.text
    except: return "Analiz şu an hazırlanamadı."

# ==========================================
# 5. İSKELET VE TASARIM
# ==========================================
st.set_page_config(page_title="Trucker.Markets", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    .block-container { max-width: 1100px; margin: 0 auto; padding-top: 1.5rem; }
    body { background-color: #0e1117; color: white; }
    .kantan-title { font-size: 2.8rem; font-weight: 900; margin-bottom: 0px; letter-spacing: -1px;}
    .kantan-title span { color: #e63946; }
    .card-container { background-color: #161b22; border-radius: 8px; border: 1px solid #30363d; margin-bottom: 15px; padding-bottom: 5px; transition: 0.2s;}
    .card-container:hover { border-color: #e63946; transform: translateY(-2px); }
    .card-img { width: 100%; height: 200px; object-fit: cover; border-radius: 8px 8px 0 0; margin-bottom: 8px;}
    .card-title { font-size: 1rem; font-weight: bold; padding: 0 10px; height: 60px; overflow: hidden; color: #e0e0e0;}
    .stTabs [data-baseweb="tab-list"] { gap: 8px; border-bottom: 2px solid #30363d;}
    .stTabs [data-baseweb="tab"] { background-color: #161b22; border-radius: 4px 4px 0px 0px; padding: 10px 15px; color: #888; border: 1px solid #30363d; border-bottom: none;}
    .stTabs [aria-selected="true"] { background-color: #e63946 !important; color: white !important; font-weight: bold; border-color: #e63946 !important;}
</style>
""", unsafe_allow_html=True)

# Sayfa Yönetimi
if 'page' not in st.session_state: st.session_state.page = 'home'
if 'data' not in st.session_state: st.session_state.data = None

def view_details(item):
    st.session_state.data = item
    st.session_state.page = 'details'

def go_home():
    st.session_state.page = 'home'

# ==========================================
# 6. EKRANLAR
# ==========================================
if st.session_state.page == 'details':
    st.button("← Geri Dön", on_click=go_home)
    h = st.session_state.data
    st.write("---")
    
    st.image(resim_bul(h.link, h.title), use_container_width=True)
    st.title(h.title)
    st.caption(f"[Haberin Orijinaline Git]({h.link})")
    
    analiz = st.session_state.mevcut_raporlar.get(h.link)
    
    if not analiz:
        # SADECE yepyeni bir habere ilk kez tıklandığında yapay zeka çalışır.
        with st.spinner("Bu raporu okuyan ilk kişisiniz! Yapay zeka sizin için derliyor..."):
            analiz = rapor_hazirla(h.link, h.title)
            
    st.markdown(f'<div style="font-size:1.15rem; line-height:1.8; color:#e0e0e0;">{analiz}</div>', unsafe_allow_html=True)

else:
    st.markdown('<p class="kantan-title">TRUCKER<span>.MARKETS</span></p>', unsafe_allow_html=True)
    st.write(f"Sektörel İstihbarat | {datetime.now().strftime('%d %B %Y')}")
    
    tab_isimleri = ["🌟 Piyasalar", "🇸🇪 Volvo & Scania", "🇩🇪 Mercedes", "🇺🇸 Freightliner", "🇮🇳 BharatBenz"]
    tabs = st.tabs(tab_isimleri)
    sorgular = ["heavy truck news", "Volvo Scania trucks", "Mercedes Actros news", "Freightliner trucks", "BharatBenz trucks"]

    for i, tab in enumerate(tabs):
        with tab:
            rss_link = f"https://news.google.com/rss/search?q={urllib.parse.quote(sorgular[i] + ' when:3d')}&hl=en-US"
            haberler = feedparser.parse(rss_link).entries[:6]
            
            # Arka plan senkronizasyonu tamamen silindi.
            
            rows = [st.columns(3), st.columns(3)]
            for idx, h in enumerate(haberler):
                col = rows[idx // 3][idx % 3]
                with col:
                    img = resim_bul(h.link, h.title)
                    st.markdown(f'<div class="card-container"><img src="{img}" class="card-img"><div class="card-title">{h.title[:70]}...</div></div>', unsafe_allow_html=True)
                    st.button("Raporu Oku", key=f"btn_{i}_{idx}", on_click=view_details, args=(h,), use_container_width=True)
