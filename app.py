import streamlit as st
from google import genai
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import urllib.parse
import gspread
from google.oauth2.service_account import Credentials

# ==========================================
# GÜVENLİK VE API BAĞLANTILARI
# ==========================================
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    st.error("Secrets bulunamadı. Lütfen Cloud panelini kontrol edin.")
    st.stop()

client = genai.Client(api_key=GEMINI_API_KEY)

# --- GOOGLE SHEETS (KALICI HAFIZA) ---
@st.cache_resource
def get_database():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        gc = gspread.authorize(creds)
        return gc.open("TruckerNews_DB").sheet1
    except Exception:
        return None

# ==========================================
# GELİŞMİŞ GÖRSEL VE LİNK ÇÖZÜCÜ
# ==========================================
@st.cache_data(ttl=900)
def resim_bul(google_news_url, baslik=""):
    yasakli = ['logo', 'icon', 'favicon', 'google', 'gstatic', 'avatar', 'news.google', 'blank']
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        # Google Redirector'ı aş
        r_init = requests.get(google_news_url, headers=headers, timeout=5, allow_redirects=True)
        final_url = r_init.url
        
        # Gerçek siteye gir ve resmi ara
        r = requests.get(final_url, headers=headers, timeout=7)
        soup = BeautifulSoup(r.content, 'html.parser')
        
        # 1. Öncelik: Meta Etiketleri
        meta = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
        if meta and meta.get("content"):
            img_url = urllib.parse.urljoin(final_url, meta["content"])
            if not any(x in img_url.lower() for x in yasakli): return img_url
            
        # 2. Öncelik: Haberin içindeki en büyük görsel
        imgs = soup.find_all('img')
        for img in imgs:
            src = img.get('src') or img.get('data-src')
            if src and 'http' in src:
                if not any(x in src.lower() for x in yasakli): return src
    except: pass
    
    # Yedek: Markaya özel Wikipedia tır görselleri
    b = baslik.lower()
    if "volvo" in b: return "https://upload.wikimedia.org/wikipedia/commons/thumb/7/77/Volvo_FH_500.jpg/800px-Volvo_FH_500.jpg"
    if "scania" in b: return "https://upload.wikimedia.org/wikipedia/commons/thumb/2/25/Scania_R500_V8.jpg/800px-Scania_R500_V8.jpg"
    if "mercedes" in b: return "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Mercedes-Benz_Actros_1845.jpg/800px-Mercedes-Benz_Actros_1845.jpg"
    return "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/MAN_TGX_18.440_XXL.jpg/800px-MAN_TGX_18.440_XXL.jpg"

# ==========================================
# ARKA PLAN SENKRONİZASYON MOTORU
# ==========================================
def rapor_hazirla(link, baslik, sheet):
    # Eğer veritabanında zaten varsa hazırlama
    try:
        all_data = sheet.get_all_records()
        for row in all_data:
            if row.get("Link") == link: return row.get("Analiz")
    except: pass

    # Yoksa hazırla ve kaydet
    prompt = f"Sen bir ağır vasıta piyasa analistisin. Şu haberi müşteri gözüyle değerlendiren kısa, ferah, Türkçe bir rapor yaz: {baslik}"
    try:
        cevap = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        sheet.append_row([link, cevap.text])
        return cevap.text
    except: return "Analiz şu an hazırlanamadı."

# ==========================================
# TASARIM VE İSKELET
# ==========================================
st.set_page_config(page_title="Trucker.Markets", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    .block-container { max-width: 1100px; margin: 0 auto; }
    body { background-color: #0e1117; color: white; }
    .kantan-title { font-size: 2.8rem; font-weight: 900; margin-bottom: 0px; }
    .kantan-title span { color: #e63946; }
    .card-container { background-color: #161b22; border-radius: 8px; border: 1px solid #30363d; margin-bottom: 15px; }
    .card-img { width: 100%; height: 200px; object-fit: cover; border-radius: 8px 8px 0 0; }
    .card-title { font-size: 1rem; font-weight: bold; padding: 10px; height: 65px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# Sayfa Yönetimi
if 'page' not in st.session_state: st.session_state.page = 'home'
if 'data' not in st.session_state: st.session_state.data = None

# ==========================================
# EKRANLAR
# ==========================================
if st.session_state.page == 'details':
    st.button("← Geri Dön")
    if st.button("Anasayfa", on_click=lambda: st.session_state.update({"page": "home"})): pass
    
    h = st.session_state.data
    st.image(resim_bul(h.link, h.title), use_container_width=True)
    st.title(h.title)
    
    # Raporu veritabanından çek (Önceden hazırlandığı için anında gelecek)
    sheet = get_database()
    analiz = "Rapor bulunamadı."
    if sheet:
        recs = sheet.get_all_records()
        for r in recs:
            if r.get("Link") == h.link:
                analiz = r.get("Analiz")
                break
    
    st.markdown(f'<div style="font-size:1.2rem; line-height:1.8;">{analiz}</div>', unsafe_allow_html=True)
    st.caption(f"[Orijinal Kaynak]({h.link})")

else:
    st.markdown('<p class="kantan-title">TRUCKER<span>.MARKETS</span></p>', unsafe_allow_html=True)
    st.write(f"Sektörel İstihbarat | {datetime.now().strftime('%d %B %Y')}")
    
    tabs = st.tabs(["🌟 Piyasalar", "🇸🇪 Volvo & Scania", "🇩🇪 Mercedes", "🇺🇸 Freightliner", "🇮🇳 BharatBenz"])
    sorgular = ["heavy truck news", "Volvo Scania trucks", "Mercedes Actros news", "Freightliner trucks", "BharatBenz trucks"]
    
    sheet = get_database()

    for i, tab in enumerate(tabs):
        with tab:
            haberler = feedparser.parse(f"https://news.google.com/rss/search?q={urllib.parse.quote(sorgular[i])}&hl=en-US").entries[:6]
            
            # --- ARKA PLAN SENKRONİZASYONU ---
            # Kullanıcı sekmeyi açtığı an ilk 3 haberi arka planda hazırlar
            if sheet:
                with st.status(f"{tab.label} raporları önceden hazırlanıyor...", expanded=False):
                    for h in haberler[:3]:
                        rapor_hazirla(h.link, h.title, sheet)
            
            # HABER KARTLARI
            rows = [st.columns(3), st.columns(3)]
            for idx, h in enumerate(haberler):
                col = rows[idx // 3][idx % 3]
                with col:
                    img = resim_bul(h.link, h.title)
                    st.markdown(f'<div class="card-container"><img src="{img}" class="card-img"><div class="card-title">{h.title[:70]}...</div></div>', unsafe_allow_html=True)
                    if st.button("Raporu Oku", key=f"btn_{i}_{idx}"):
                        st.session_state.data = h
                        st.session_state.page = 'details'
                        st.rerun()
