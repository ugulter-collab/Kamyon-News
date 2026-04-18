import streamlit as st
from google import genai
from googleapiclient.discovery import build
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import urllib.parse
import gspread
from google.oauth2.service_account import Credentials

# --- GÜVENLİK VE API ---
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    YOUTUBE_API_KEY = st.secrets["YOUTUBE_API_KEY"]
except:
    st.error("Secrets bulunamadı. Lütfen Cloud panelinden ayarlarınızı kontrol edin.")
    st.stop()

client = genai.Client(api_key=GEMINI_API_KEY)
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

# --- GOOGLE SHEETS VERİTABANI BAĞLANTISI ---
@st.cache_resource
def get_database():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        gc = gspread.authorize(creds)
        # Tablonuzun adının TruckerNews_DB olduğundan emin olun
        return gc.open("TruckerNews_DB").sheet1
    except Exception as e:
        st.error(f"Veritabanı bağlantı hatası: {e}")
        return None

# --- YAPAY ZEKA VE HAFIZA MOTORU ---
def akilli_analiz_getir(link, baslik):
    sheet = get_database()
    if sheet is None:
        return "Veritabanına bağlanılamadı. Sistem geçici olarak devre dışı."

    # 1. TABLO KONTROLÜ (Hafızada var mı?)
    try:
        kayitlar = sheet.get_all_records()
        for kayit in kayitlar:
            if kayit.get("Link") == link:
                return f"*(Bu analiz arşivden anında getirilmiştir ⚡)*\n\n{kayit.get('Analiz')}"
    except Exception as e:
        # Eğer tablo tamamen boşsa ve başlıklar yoksa hata verebilir, yoksay ve devam et
        pass

    # 2. BULUNAMADIYSA API'Yİ ÇALIŞTIR VE KAYDET
    prompt = f"Şu haberi ağır vasıta sektörü uzmanı gözüyle detaylandır. Teknik yenilikleri, bağlantı çözümlerini ve ADAS sistemlerine etkisini vurgulayan Türkçe bir makale yaz: {baslik}"
    
    try:
        cevap = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        analiz_metni = cevap.text
        
        # Gelecekteki ziyaretçiler için veritabanına kaydet (Sütunlar: Link, Analiz)
        # Not: Tablonuzun 1. satırında A1 hücresinde "Link", B1 hücresinde "Analiz" yazdığından emin olun.
        sheet.append_row([link, analiz_metni])
        
        return f"*(Yapay Zeka bu analizi sizin için şimdi üretti 🤖)*\n\n{analiz_metni}"
    except Exception as e:
        return f"Analiz oluşturulurken hata oluştu: {e}"

# --- TASARIM VE İSKELET AYARLARI ---
st.set_page_config(page_title="Trucker.News Portal", page_icon="🚛", layout="wide")
st.markdown("""
<style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    body { background-color: #0e1117; }
    .kantan-title { font-family: 'Helvetica Neue', sans-serif; font-size: 3rem; font-weight: 900; color: #ffffff; letter-spacing: -1.5px; margin-bottom: 0px;}
    .kantan-title span { color: #e63946; }
    .kantan-date { font-family: monospace; color: #888888; border-bottom: 1px solid #333; padding-bottom: 15px; margin-bottom: 25px; font-size: 0.9rem;}
    .card-container { background-color: #161b22; border-radius: 12px; border: 1px solid #30363d; margin-bottom: 25px; transition: 0.4s; }
    .latest-time { color: #e63946; font-family: monospace; font-weight: bold; font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)

# Görsel Bulucu (Aynı Kalıyor)
@st.cache_data(ttl=900)
def resim_bul(url, baslik=""):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        soup = BeautifulSoup(r.content, 'html.parser')
        og_img = soup.find("meta", property="og:image")
        if og_img and og_img.get("content"): return og_img["content"]
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if 'http' in src and any(ext in src.lower() for ext in ['.jpg', '.png', '.webp']) and 'logo' not in src.lower(): return src
    except: pass
    yedekler = ["https://images.unsplash.com/photo-1601584115197-04ecc0da31d7?q=80&w=800", "https://images.unsplash.com/photo-1586191582056-96fcfdf9fd8b?q=80&w=800"]
    return yedekler[len(baslik) % 2]

# Veri Getirici (Aynı Kalıyor)
@st.cache_data(ttl=900)
def veri_getir(sorgu, adet, taze_mi=False):
    zaman_filtresi = " when:12h" if taze_mi else ""
    guvenli_sorgu = urllib.parse.quote(sorgu + zaman_filtresi)
    feed = feedparser.parse(f"https://news.google.com/rss/search?q={guvenli_sorgu}&hl=en-US")
    return feed.entries[:adet]

# --- SAYFA YÖNETİMİ ---
if 'page' not in st.session_state: st.session_state.page = 'home'
if 'data' not in st.session_state: st.session_state.data = None

def view_details(item):
    st.session_state.data = item
    st.session_state.page = 'details'

def go_home():
    st.session_state.page = 'home'

# --- 1. DETAYLAR SAYFASI (YAPAY ZEKA BURADA DEVREYE GİRER) ---
if st.session_state.page == 'details':
    st.button("← Ana Sayfaya Dön", on_click=go_home)
    h = st.session_state.data
    st.write("---")
    st.title(h.title)
    st.caption(f"Kaynak: {h.source.title if 'source' in h else 'Global Medya'} | [Haberi Sitede Oku]({h.link})")
    
    with st.spinner("Arşiv kontrol ediliyor veya yeni analiz hazırlanıyor..."):
        # YENİ SİSTEM: API'ye direkt gitmek yerine akıllı hafıza motorunu çağırıyoruz
        analiz_sonucu = akilli_analiz_getir(h.link, h.title)
        st.markdown(f'<div style="font-size:1.1rem; line-height:1.8;">{analiz_sonucu}</div>', unsafe_allow_html=True)

# --- 2. ANA PORTAL SAYFASI (Değişiklik Yok) ---
else:
    st.markdown('<p class="kantan-title">TRUCKER<span>.NEWS</span></p>', unsafe_allow_html=True)
    st.markdown(f'<p class="kantan-date">{datetime.now().strftime("%d %B %Y %H:%M")} | MEKATRONİK SİSTEMLER STRATEJİSİ</p>', unsafe_allow_html=True)

    tabs = st.tabs(["🌟 Öne Çıkanlar", "🖥️ HMI", "📡 Connectivity", "🛡️ ADAS", "⚡ Electric", "🏭 OEM News"])
    sorgular = {"HMI": "truck mechatronics HMI", "Connectivity": "truck connectivity telematics", "ADAS": "truck ADAS safety", "Electric": "electric truck battery", "OEM": "MAN Scania Mercedes-Benz truck"}

    with tabs[0]:
        manset_haberler = veri_getir("heavy duty truck innovations", 15, taze_mi=True)
        cols = st.columns(3)
        for i in range(3):
            if i < len(manset_haberler):
                h = manset_haberler[i]
                with cols[i]:
                    st.image(resim_bul(h.link, h.title), use_container_width=True)
                    st.write(f"**{h.title[:75]}...**")
                    st.button("İncele", key=f"top_{i}", on_click=view_details, args=(h,), use_container_width=True)

        st.write("---")
        st.subheader("⏱️ Son Haberler")
        for i, h in enumerate(sorted(manset_haberler[3:], key=lambda x: x.get('published_parsed', 0), reverse=True)):
            tarih = datetime.fromtimestamp(time.mktime(h.published_parsed)).strftime("%H:%M") if 'published_parsed' in h else "Bugün"
            c1, c2 = st.columns([1, 8])
            with c1: st.markdown(f'<p class="latest-time">{tarih}</p>', unsafe_allow_html=True)
            with c2: st.button(h.title, key=f"list_{i}", on_click=view_details, args=(h,), use_container_width=True)

    def tab_doldur(sorgu, t_id):
        haberler = veri_getir(sorgu, 6, taze_mi=True)
        for row in range(0, 6, 3):
            cols = st.columns(3)
            for j in range(3):
                idx = row + j
                if idx < len(haberler):
                    h = haberler[idx]
                    with cols[j]:
                        st.image(resim_bul(h.link, h.title), use_container_width=True)
                        st.write(f"**{h.title[:65]}...**")
                        st.button("Detaylar", key=f"btn_{t_id}_{idx}", on_click=view_details, args=(h,), use_container_width=True)

    with tabs[1]: tab_doldur(sorgular["HMI"], "hmi")
    with tabs[2]: tab_doldur(sorgular["Connectivity"], "conn")
    with tabs[3]: tab_doldur(sorgular["ADAS"], "adas")
    with tabs[4]: tab_doldur(sorgular["Electric"], "ev")
    with tabs[5]: tab_doldur(sorgular["OEM"], "oem")
