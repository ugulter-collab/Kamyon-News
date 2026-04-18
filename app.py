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
    st.error("Kritik Hata: API Şifreleri (Secrets) bulunamadı.")
    st.stop()

client = genai.Client(api_key=GEMINI_API_KEY)

# --- GOOGLE SHEETS (AKILLI HAFIZA) BAĞLANTISI ---
@st.cache_resource
def get_database():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        gc = gspread.authorize(creds)
        # Tablonuzun adının TruckerNews_DB ve sekmenin Sheet1 olduğundan emin olun
        return gc.open("TruckerNews_DB").sheet1
    except Exception as e:
        st.error(f"Veritabanı bağlantı hatası: {e}")
        return None

# ==========================================
# YAPAY ZEKA GAZETECİSİ VE HAFIZA MOTORU
# ==========================================
def akilli_analiz_getir(link, baslik):
    sheet = get_database()
    if sheet is None:
        return "Veritabanına bağlanılamadı. Sistem geçici olarak devre dışı."

    # 1. HAFIZA KONTROLÜ (Maliyet: 0 TL)
    try:
        kayitlar = sheet.get_all_records()
        for kayit in kayitlar:
            if kayit.get("Link") == link:
                return f"*(Bu vizyoner analiz arşivden anında getirilmiştir ⚡)*\n\n{kayit.get('Analiz')}"
    except Exception:
        pass

    # 2. YENİ ANALİZ ÜRETİMİ (Teknik Gazeteci Karakteri)
    prompt = f"""
    Sen otomotiv teknolojileri ve mekatronik üzerine yazan, vizyoner ve heyecan verici bir teknoloji gazetecisisin. 
    Şu haberi oku ve mekatronik mühendislerinin çok ilgisini çekecek akıcı bir Türkçe makale yaz: {baslik}
    
    Kurallar:
    1. Sıkıcı kurumsal dili (finansal karlar, şirket övgüleri vb.) tamamen çöpe at.
    2. Haberin içindeki en ilginç "Teknik İnovasyon" veya "Mühendislik Çözümü" nedir? Sadece buna odaklan.
    3. Okuması çok kolay olsun. Mutlaka kısa paragraflar ve vurucu ara başlıklar kullan.
    4. Yazının sonuna "Mekatronik Test Ekibi İçin Neden Önemli?" adında 2 maddelik kısa bir özet ekle.
    """
    
    try:
        cevap = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        analiz_metni = cevap.text
        
        # Gelecekteki ziyaretçiler için E-Tabloya kaydet (A1: Link, B1: Analiz olmalı)
        sheet.append_row([link, analiz_metni])
        return f"*(Yapay Zeka bu analizi sizin için şimdi üretti 🤖)*\n\n{analiz_metni}"
    except Exception as e:
        return f"Analiz oluşturulurken hata oluştu: {e}"

# ==========================================
# İSKELET VE TASARIM (KANTAN STYLE)
# ==========================================
st.set_page_config(page_title="Trucker.News", page_icon="🚛", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    body { background-color: #0e1117; }
    .kantan-title { font-family: 'Helvetica Neue', sans-serif; font-size: 3rem; font-weight: 900; color: #ffffff; letter-spacing: -1.5px; margin-bottom: 0px;}
    .kantan-title span { color: #e63946; }
    .kantan-date { font-family: monospace; color: #888888; border-bottom: 1px solid #333; padding-bottom: 15px; margin-bottom: 25px; font-size: 0.9rem;}
    .card-container { background-color: #161b22; border-radius: 12px; border: 1px solid #30363d; margin-bottom: 25px; transition: 0.4s; }
    .card-container:hover { border-color: #e63946; transform: translateY(-5px); }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; border-bottom: 2px solid #30363d;}
    .stTabs [data-baseweb="tab"] { background-color: #161b22; border-radius: 4px 4px 0px 0px; padding: 10px 20px; color: #888; border: 1px solid #30363d; border-bottom: none;}
    .stTabs [aria-selected="true"] { background-color: #e63946 !important; color: white !important; font-weight: bold; border-color: #e63946 !important;}
    .latest-time { color: #e63946; font-family: monospace; font-weight: bold; font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# VERİ ÇEKME MOTORLARI
# ==========================================
@st.cache_data(ttl=900)
def resim_bul(url, baslik=""):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        r = requests.get(url, headers=headers, timeout=8, allow_redirects=True)
        soup = BeautifulSoup(r.content, 'html.parser')
        
        # 1. Öncelik: OG Image
        og_img = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
        resim_url = og_img["content"] if og_img and og_img.get("content") else None
        
        # 2. Öncelik: En büyük görsel
        if not resim_url:
            for img in soup.find_all('img'):
                src = img.get('src', '')
                if 'http' in src and any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                    resim_url = src
                    break
        
        # Anti-Bot ve Logoları Filtrele
        if resim_url and not any(x in resim_url.lower() for x in ['google', 'gstatic', 'logo', 'icon', 'favicon']):
            return resim_url
    except:
        pass
    
    # Yedek Görsel Havuzu (Ağır Vasıta & İnovasyon)
    yedekler = [
        "https://images.unsplash.com/photo-1601584115197-04ecc0da31d7?q=80&w=800",
        "https://images.unsplash.com/photo-1586191582056-96fcfdf9fd8b?q=80&w=800",
        "https://images.unsplash.com/photo-1519003722824-194d4455a60c?q=80&w=800"
    ]
    return yedekler[len(baslik) % len(yedekler)]

@st.cache_data(ttl=900)
def veri_getir(sorgu, adet, taze_mi=True):
    zaman_filtresi = " when:12h" if taze_mi else ""
    guvenli_sorgu = urllib.parse.quote(sorgu + zaman_filtresi)
    rss_url = f"https://news.google.com/rss/search?q={guvenli_sorgu}&hl=en-US"
    feed = feedparser.parse(rss_url)
    return feed.entries[:adet]

# ==========================================
# SAYFA YÖNETİMİ (ROUTING)
# ==========================================
if 'page' not in st.session_state: st.session_state.page = 'home'
if 'data' not in st.session_state: st.session_state.data = None

def view_details(item):
    st.session_state.data = item
    st.session_state.page = 'details'

def go_home():
    st.session_state.page = 'home'

# ==========================================
# EKRAN 1: MAKALELER (DETAY SAYFASI)
# ==========================================
if st.session_state.page == 'details':
    st.button("← Portala Geri Dön", on_click=go_home)
    h = st.session_state.data
    st.write("---")
    st.title(h.title)
    kaynak = h.source.title if 'source' in h else 'Global Medya'
    st.caption(f"Kaynak: {kaynak} | [Haberin Orijinaline Git]({h.link})")
    
    with st.spinner("Mekatronik uzmanı haberi analiz ediyor..."):
        analiz_sonucu = akilli_analiz_getir(h.link, h.title)
        st.markdown(f'<div style="font-size:1.15rem; line-height:1.8; color:#e0e0e0;">{analiz_sonucu}</div>', unsafe_allow_html=True)

# ==========================================
# EKRAN 2: ANA PORTAL (VİTRİN)
# ==========================================
else:
    st.markdown('<p class="kantan-title">TRUCKER<span>.NEWS</span></p>', unsafe_allow_html=True)
    st.markdown(f'<p class="kantan-date">{datetime.now().strftime("%d %B %Y")} | MEKATRONİK SİSTEMLER VE İNOVASYON İSTİHBARATI</p>', unsafe_allow_html=True)

    tabs = st.tabs(["🌟 İnovasyon Radarı", "🖥️ HMI Ekranları", "📡 Bağlantılı Araçlar", "🛡️ Otonom & ADAS", "⚡ Elektrifikasyon", "🏭 Dev Üreticiler"])
    
    # ÖZEL GAZETECİLİK SORGULARI
    sorgular = {
        "HMI": "truck dashboard interface teardown OR next-gen truck cabin screens",
        "Connectivity": "truck V2X communication OR over the air updates heavy duty",
        "ADAS": "autonomous truck road test OR truck emergency braking system test",
        "Electric": "electric semi truck real world range OR hydrogen fuel cell truck test",
        "OEM": "MAN truck engineering OR Scania new powertrain OR Mercedes-Benz truck prototype"
    }

    # --- ANA SEKME (MANŞETLER VE ZAMAN ÇİZELGESİ) ---
    with tabs[0]:
        manset_haberler = veri_getir("heavy duty truck engineering OR mechatronics innovations", 15, taze_mi=True)
        
        st.subheader("🔥 Günün Test Radarı")
        cols = st.columns(3)
        for i in range(3):
            if i < len(manset_haberler):
                h = manset_haberler[i]
                with cols[i]:
                    st.image(resim_bul(h.link, h.title), use_container_width=True)
                    st.markdown(f"<p style='font-weight:bold; font-size:1.1rem; margin-top:10px;'>{h.title[:75]}...</p>", unsafe_allow_html=True)
                    st.button("İncele", key=f"top_{i}", on_click=view_details, args=(h,), use_container_width=True)

        st.write("---")
        st.subheader("⏱️ Canlı Akış")
        sirali = sorted(manset_haberler[3:], key=lambda x: x.get('published_parsed', 0), reverse=True)
        for i, h in enumerate(sirali):
            tarih = datetime.fromtimestamp(time.mktime(h.published_parsed)).strftime("%H:%M") if 'published_parsed' in h else "Bugün"
            c1, c2 = st.columns([1, 8])
            with c1: st.markdown(f'<p class="latest-time">{tarih}</p>', unsafe_allow_html=True)
            with c2: st.button(h.title, key=f"list_{i}", on_click=view_details, args=(h,), use_container_width=True)

    # --- DİĞER KATEGORİ SEKMELERİ ---
    def tab_doldur(sorgu, t_id):
        with st.spinner("Endüstri taranıyor..."):
            haberler = veri_getir(sorgu, 6, taze_mi=True)
            for row in range(0, 6, 3):
                cols = st.columns(3)
                for j in range(3):
                    idx = row + j
                    if idx < len(haberler):
                        h = haberler[idx]
                        with cols[j]:
                            st.image(resim_bul(h.link, h.title), use_container_width=True)
                            st.markdown(f"<p style='font-weight:bold; font-size:1.05rem; margin-top:10px;'>{h.title[:65]}...</p>", unsafe_allow_html=True)
                            st.button("Detaylar", key=f"btn_{t_id}_{idx}", on_click=view_details, args=(h,), use_container_width=True)

    with tabs[1]: tab_doldur(sorgular["HMI"], "hmi")
    with tabs[2]: tab_doldur(sorgular["Connectivity"], "conn")
    with tabs[3]: tab_doldur(sorgular["ADAS"], "adas")
    with tabs[4]: tab_doldur(sorgular["Electric"], "ev")
    with tabs[5]: tab_doldur(sorgular["OEM"], "oem")
