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
# 1. GÜVENLİK VE VERİTABANI
# ==========================================
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    st.error("Secrets bulunamadı. Lütfen API anahtarınızı kontrol edin.")
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
# 2. HAFIZA VE ÇEVİRİ MOTORLARI
# ==========================================
if 'mevcut_ceviriler' not in st.session_state:
    st.session_state.mevcut_ceviriler = {}
    if sheet:
        try:
            for row in sheet.get_all_records():
                st.session_state.mevcut_ceviriler[row.get("Link")] = row.get("Analiz")
        except: pass

@st.cache_data(ttl=3600)
def basliklari_turkceye_cevir(baslik_listesi):
    """Ana sayfadaki başlıkları toplu ve hızlı şekilde çevirir."""
    if not baslik_listesi: return []
    prompt = "Aşağıdaki İngilizce haber başlıklarını anlamını bozmadan profesyonel bir haber diliyle Türkçeye çevir. Sadece çevirileri alt alta yaz:\n" + "\n".join(baslik_listesi)
    try:
        cevap = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        ceviriler = [b.strip() for b in cevap.text.strip().split('\n') if b.strip()]
        return ceviriler if len(ceviriler) == len(baslik_listesi) else baslik_listesi
    except:
        return baslik_listesi

def tam_metin_cevirisi(link, baslik):
    """Haberin tamamını yorumsuz şekilde Türkçeye çevirir."""
    if link in st.session_state.mevcut_ceviriler:
        return st.session_state.mevcut_ceviriler[link]

    prompt = f"Sen profesyonel bir haber çevirmenisin. Aşağıdaki haber konusunu hiçbir yorum, analiz veya ekleme yapmadan, doğrudan ve objektif bir şekilde Türkçeye çevir. Sadece haberi aktar:\n\n{baslik}"
    try:
        cevap = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        if sheet: sheet.append_row([link, cevap.text])
        st.session_state.mevcut_ceviriler[link] = cevap.text 
        return cevap.text
    except: return "Çeviri şu an yapılamadı."

# ==========================================
# 3. GÖRSEL BULUCU
# ==========================================
@st.cache_data(ttl=900)
def resim_bul(url, baslik=""):
    yasakli = ['logo', 'icon', 'favicon', 'google', 'gstatic', 'avatar', 'news.google']
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        r_init = requests.get(url, headers=headers, timeout=5, allow_redirects=True)
        f_url = r_init.url
        r = requests.get(f_url, headers=headers, timeout=5)
        soup = BeautifulSoup(r.content, 'html.parser')
        meta = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
        if meta and meta.get("content"):
            img = urllib.parse.urljoin(f_url, meta["content"])
            if not any(x in img.lower() for x in yasakli): return img
    except: pass
    
    b = baslik.lower()
    if "volvo" in b: return "https://upload.wikimedia.org/wikipedia/commons/thumb/7/77/Volvo_FH_500.jpg/800px-Volvo_FH_500.jpg"
    if "scania" in b: return "https://upload.wikimedia.org/wikipedia/commons/thumb/2/25/Scania_R500_V8.jpg/800px-Scania_R500_V8.jpg"
    if "mercedes" in b: return "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Mercedes-Benz_Actros_1845.jpg/800px-Mercedes-Benz_Actros_1845.jpg"
    return "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/MAN_TGX_18.440_XXL.jpg/800px-MAN_TGX_18.440_XXL.jpg"

# ==========================================
# 4. TASARIM VE SAYFA YAPISI
# ==========================================
st.set_page_config(page_title="Trucker.Markets", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    .block-container { max-width: 1100px; margin: 0 auto; padding-top: 1.5rem; }
    body { background-color: #0e1117; color: white; }
    .kantan-title { font-size: 2.8rem; font-weight: 900; margin-bottom: 0px; letter-spacing: -1px;}
    .kantan-title span { color: #e63946; }
    .card-container { background-color: #161b22; border-radius: 8px; border: 1px solid #30363d; margin-bottom: 15px; padding-bottom: 5px; transition: 0.2s;}
    .card-img { width: 100%; height: 200px; object-fit: cover; border-radius: 8px 8px 0 0; margin-bottom: 8px;}
    .card-title { font-size: 0.95rem; font-weight: bold; padding: 0 10px; height: 55px; overflow: hidden; color: #e0e0e0; line-height: 1.3;}
</style>
""", unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'home'
if 'data' not in st.session_state: st.session_state.data = None
if 'turkce_baslik' not in st.session_state: st.session_state.turkce_baslik = ""

def haberi_ac(item, baslik):
    st.session_state.data = item
    st.session_state.turkce_baslik = baslik
    st.session_state.page = 'details'

if st.session_state.page == 'details':
    if st.button("← Geri Dön"): st.session_state.page = 'home'; st.rerun()
    h = st.session_state.data
    st.write("---")
    st.image(resim_bul(h.link, h.title), use_container_width=True)
    st.title(st.session_state.turkce_baslik)
    
    analiz = st.session_state.mevcut_ceviriler.get(h.link)
    if not analiz:
        with st.spinner("Haber Türkçeye çevriliyor..."):
            analiz = tam_metin_cevirisi(h.link, h.title)
    
    st.markdown(f'<div style="font-size:1.15rem; line-height:1.8; color:#e0e0e0;">{analiz}</div>', unsafe_allow_html=True)
    st.caption(f"[Kaynağa Git]({h.link})")

else:
    st.markdown('<p class="kantan-title">TRUCKER<span>.MARKETS</span></p>', unsafe_allow_html=True)
    st.write(f"Global Haber Merkezi | {datetime.now().strftime('%d %B %Y')}")
    
    tab_adlari = ["🌟 Manşetler", "🇸🇪 Volvo & Scania", "🇩🇪 Mercedes", "🇺🇸 Freightliner", "🇮🇳 BharatBenz"]
    sorgular = ["heavy truck news", "Volvo Scania trucks", "Mercedes Actros news", "Freightliner trucks", "BharatBenz trucks"]
    tabs = st.tabs(tab_adlari)

    for i, tab in enumerate(tabs):
        with tab:
            raw_feed = feedparser.parse(f"https://news.google.com/rss/search?q={urllib.parse.quote(sorgular[i] + ' when:3d')}&hl=en-US").entries[:6]
            
            # ANA SAYFA BAŞLIKLARINI ÇEVİR
            orijinal_basliklar = [h.title for h in raw_feed]
            ceviriler = basliklari_turkceye_cevir(orijinal_basliklar)
            
            cols = [st.columns(3), st.columns(3)]
            for idx, h in enumerate(raw_feed):
                col = cols[idx // 3][idx % 3]
                with col:
                    t_baslik = ceviriler[idx] if idx < len(ceviriler) else h.title
                    img = resim_bul(h.link, h.title)
                    st.markdown(f'<div class="card-container"><img src="{img}" class="card-img"><div class="card-title">{t_baslik[:75]}</div></div>', unsafe_allow_html=True)
                    st.button("Haberi Oku", key=f"btn_{i}_{idx}", on_click=haberi_ac, args=(h, t_baslik), use_container_width=True)
