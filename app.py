import streamlit as st
from google import genai
from googleapiclient.discovery import build
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import urllib.parse

# --- GÜVENLİK VE API YAPILANDIRMASI ---
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    YOUTUBE_API_KEY = st.secrets["YOUTUBE_API_KEY"]
except:
    st.error("Secrets bulunamadı. Lütfen Cloud panelinden API anahtarlarınızı ekleyin.")
    st.stop()

client = genai.Client(api_key=GEMINI_API_KEY)
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

# --- PORTAL TASARIMI ---
st.set_page_config(page_title="Trucker.News Portal", page_icon="🚛", layout="wide")

st.markdown("""
<style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    body { background-color: #0e1117; }
    .kantan-title { font-family: 'Helvetica Neue', sans-serif; font-size: 3rem; font-weight: 900; color: #ffffff; letter-spacing: -1.5px; margin-bottom: 0px;}
    .kantan-title span { color: #e63946; }
    .kantan-date { font-family: monospace; color: #888888; border-bottom: 1px solid #333; padding-bottom: 15px; margin-bottom: 25px; font-size: 0.9rem;}
    .card-container { background-color: #161b22; border-radius: 12px; border: 1px solid #30363d; margin-bottom: 25px; transition: 0.4s; }
    .card-container:hover { border-color: #e63946; transform: translateY(-5px); }
    .latest-row { padding: 12px 0; border-bottom: 1px solid #21262d; }
    .latest-time { color: #e63946; font-family: monospace; font-weight: bold; font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)

# --- GELİŞMİŞ GÖRSEL MOTORU (Original Source Scraper) ---
@st.cache_data(ttl=900) # 15 dakika cache
def resim_bul(url, baslik=""):
    try:
        # Gerçek tarayıcı kimliği (Daha güçlü)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'
        }
        
        # Google Redirector'ı takip et
        r = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        final_url = r.url # Yönlenilen asıl haber sitesi
        
        soup = BeautifulSoup(r.content, 'html.parser')
        
        # 1. Öncelik: OpenGraph Görseli (og:image)
        og_img = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
        if og_img and og_img.get("content"):
            return og_img["content"]
            
        # 2. Öncelik: Sayfanın en büyük/ilk anlamlı görseli
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if 'http' in src and any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                if 'logo' not in src.lower() and 'icon' not in src.lower():
                    return src
    except:
        pass
    
    # Yedek: Sektörel Yüksek Kaliteli Fotoğraflar
    yedekler = [
        "https://images.unsplash.com/photo-1601584115197-04ecc0da31d7?q=80&w=800",
        "https://images.unsplash.com/photo-1586191582056-96fcfdf9fd8b?q=80&w=800",
        "https://images.unsplash.com/photo-1519003722824-194d4455a60c?q=80&w=800"
    ]
    return yedekler[len(baslik) % len(yedekler)]

# --- GÜNCEL VERİ ÇEKME MOTORU ---
@st.cache_data(ttl=900)
def veri_getir(sorgu, adet, taze_mi=False):
    # Eğer son haberler isteniyorsa Google'a "son 12 saat" filtresi ekle
    zaman_filtresi = " when:12h" if taze_mi else ""
    guvenli_sorgu = urllib.parse.quote(sorgu + zaman_filtresi)
    
    rss_url = f"https://news.google.com/rss/search?q={guvenli_sorgu}&hl=en-US"
    feed = feedparser.parse(rss_url)
    return feed.entries[:adet]

# --- SAYFA MANTIĞI ---
if 'page' not in st.session_state: st.session_state.page = 'home'
if 'data' not in st.session_state: st.session_state.data = None

def view_details(item):
    st.session_state.data = item
    st.session_state.page = 'details'

def go_home():
    st.session_state.page = 'home'

# ==========================================
# 1. GÖRÜNÜM: DETAYLAR
# ==========================================
if st.session_state.page == 'details':
    st.button("← Ana Sayfaya Dön", on_click=go_home)
    h = st.session_state.data
    st.write("---")
    st.title(h.title)
    st.caption(f"Kaynak: {h.source.title if 'source' in h else 'Global Medya'} | [Haberi Sitede Oku]({h.link})")
    
    with st.spinner("Yapay Zeka derinlemesine mekatronik ve endüstri analizi hazırlıyor..."):
        prompt = f"Şu haberi ağır vasıta sektörü uzmanı gözüyle detaylandır. Teknik yenilikleri, bağlantı çözümlerini ve ADAS sistemlerine etkisini vurgulayan Türkçe bir makale yaz: {h.title}"
        analiz = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        st.markdown(f'<div style="font-size:1.2rem; line-height:1.8;">{analiz.text}</div>', unsafe_allow_html=True)

# ==========================================
# 2. GÖRÜNÜM: ANA PORTAL
# ==========================================
else:
    st.markdown('<p class="kantan-title">TRUCKER<span>.NEWS</span></p>', unsafe_allow_html=True)
    st.markdown(f'<p class="kantan-date">{datetime.now().strftime("%d %B %Y %H:%M")} | MEKATRONİK SİSTEMLER VE 2030 STRATEJİSİ</p>', unsafe_allow_html=True)

    tab_titles = ["🌟 Öne Çıkanlar", "🖥️ HMI", "📡 Connectivity", "🛡️ ADAS", "⚡ Electric", "🏭 OEM News"]
    tabs = st.tabs(tab_titles)

    sorgular = {
        "HMI": "truck mechatronics HMI display dashboard",
        "Connectivity": "truck connectivity telematics 5G V2X",
        "ADAS": "truck ADAS safety active brake assist",
        "Electric": "electric truck battery hydrogen",
        "OEM": "MAN Scania Mercedes-Benz truck news"
    }

    # --- ÖNE ÇIKANLAR VE SON HABERLER ---
    with tabs[0]:
        st.subheader("🔥 Manşetler")
        manset_haberler = veri_getir("heavy duty truck innovations", 15, taze_mi=True)
        
        # Üstte 3 Büyük Manşet
        cols = st.columns(3)
        for i in range(3):
            if i < len(manset_haberler):
                h = manset_haberler[i]
                with cols[i]:
                    img = resim_bul(h.link, h.title)
                    st.image(img, use_container_width=True)
                    st.write(f"**{h.title[:75]}...**")
                    st.button("İncele", key=f"top_{i}", on_click=view_details, args=(h,), use_container_width=True)

        st.write("---")
        st.subheader("⏱️ Son Haberler (Kronolojik Akış)")
        
        son_haberler = manset_haberler[3:]
        # Tarihe göre sıralama (Yeniden eskiye)
        sirali = sorted(son_haberler, key=lambda x: x.get('published_parsed', 0), reverse=True)
        
        for i, h in enumerate(sirali):
            tarih = datetime.fromtimestamp(time.mktime(h.published_parsed)).strftime("%H:%M") if 'published_parsed' in h else "Bugün"
            c1, c2 = st.columns([1, 8])
            with c1: st.markdown(f'<p class="latest-time">{tarih}</p>', unsafe_allow_html=True)
            with c2: st.button(h.title, key=f"list_{i}", on_click=view_details, args=(h,), use_container_width=True)

    # --- KATEGORİ SEKMELERİ (Grup Başına 6 Haber) ---
    def tab_doldur(sorgu, t_id):
        haberler = veri_getir(sorgu, 6, taze_mi=True)
        for row in range(0, 6, 3):
            cols = st.columns(3)
            for j in range(3):
                idx = row + j
                if idx < len(haberler):
                    h = haberler[idx]
                    with cols[j]:
                        img = resim_bul(h.link, h.title)
                        st.image(img, use_container_width=True)
                        st.write(f"**{h.title[:65]}...**")
                        st.button("Detaylar", key=f"btn_{t_id}_{idx}", on_click=view_details, args=(h,), use_container_width=True)

    with tabs[1]: tab_doldur(sorgular["HMI"], "hmi")
    with tabs[2]: tab_doldur(sorgular["Connectivity"], "conn")
    with tabs[3]: tab_doldur(sorgular["ADAS"], "adas")
    with tabs[4]: tab_doldur(sorgular["Electric"], "ev")
    with tabs[5]: tab_doldur(sorgular["OEM"], "oem")
