import urllib.parse
import streamlit as st
from google import genai
from googleapiclient.discovery import build
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time

# --- ANAHTARLAR (BULUT GÜVENLİĞİ) ---
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    YOUTUBE_API_KEY = st.secrets["YOUTUBE_API_KEY"]
except:
    st.error("API Şifreleri bulunamadı. Lütfen Streamlit Cloud 'Secrets' bölümünü kontrol edin.")
    st.stop()

client = genai.Client(api_key=GEMINI_API_KEY)
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

# --- SAYFA AYARLARI VE KANTAN CSS ---
st.set_page_config(page_title="Trucker.News", page_icon="🚛", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    body { background-color: #0e1117; }
    .kantan-title { font-family: 'Helvetica Neue', sans-serif; font-size: 3rem; font-weight: 900; color: #ffffff; letter-spacing: -1.5px; margin-bottom: 0px;}
    .kantan-title span { color: #e63946; }
    .kantan-date { font-family: monospace; color: #888888; border-bottom: 1px solid #333; padding-bottom: 10px; margin-bottom: 20px; }
    
    /* Kart Tasarımları */
    .card-container { background-color: #161b22; border-radius: 8px; transition: 0.3s; border: 1px solid #30363d; margin-bottom: 20px; overflow: hidden;}
    .card-container:hover { border-color: #e63946; transform: translateY(-3px); }
    .tag-news { background-color: #333; color: white; padding: 3px 8px; font-size: 0.7rem; font-weight: bold; border-radius: 3px; }
    
    /* Sekme (Tab) Tasarımları */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: #0e1117; padding-bottom: 5px; border-bottom: 2px solid #30363d;}
    .stTabs [data-baseweb="tab"] { background-color: #161b22; border-radius: 4px 4px 0px 0px; padding: 10px 20px; color: #888; border: 1px solid #30363d; border-bottom: none;}
    .stTabs [aria-selected="true"] { background-color: #e63946 !important; color: white !important; font-weight: bold; border-color: #e63946 !important;}
    
    /* Son Haberler Liste Tasarımı */
    .latest-news-row { padding: 15px 0; border-bottom: 1px solid #30363d; display: flex; align-items: center;}
    .latest-date { font-family: monospace; color: #e63946; font-size: 0.9rem; min-width: 120px; }
    .latest-title { font-size: 1.1rem; color: #e0e0e0; font-weight: 600; text-decoration: none;}
</style>
""", unsafe_allow_html=True)

# --- GELİŞMİŞ GÖRSEL BULUCU ---
@st.cache_data(ttl=3600)
def resim_bul(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=5, allow_redirects=True)
        soup = BeautifulSoup(r.content, 'html.parser')
        meta_image = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
        if meta_image and meta_image.get("content"):
            return meta_image["content"]
        for img in soup.find_all('img'):
            if img.get('src') and ('http' in img['src']) and (int(img.get('width', 0)) > 200):
                return img['src']
    except:
        pass
    return "https://images.unsplash.com/photo-1586191582056-96fcfdf9fd8b?auto=format&fit=crop&q=80&w=800"

# --- KATEGORİ BAZLI VERİ ÇEKME FONKSİYONU ---
@st.cache_data(ttl=3600)
def kategori_verisi_getir(sorgu, adet):
    # Boşlukları ve özel karakterleri internetin anlayacağı formata çevirir (URL Encoding)
    guvenli_sorgu = urllib.parse.quote(sorgu)
    rss_url = f"https://news.google.com/rss/search?q={guvenli_sorgu}&hl=en-US"
    feed = feedparser.parse(rss_url)
    return feed.entries[:adet]

# --- SESSION STATE (SAYFA YÖNETİMİ) ---
if 'sayfa' not in st.session_state: st.session_state.sayfa = 'ana'
if 'secili' not in st.session_state: st.session_state.secili = None

def detaya_git(icerik):
    st.session_state.secili = icerik
    st.session_state.sayfa = 'detay'

def anasayfaya_don():
    st.session_state.sayfa = 'ana'


# ==========================================
# 1. GÖRÜNÜM: DETAY SAYFASI
# ==========================================
if st.session_state.sayfa == 'detay':
    st.button("← Portala Geri Dön", on_click=anasayfaya_don)
    item = st.session_state.secili
    st.write("---")
    
    st.title(item.title)
    kaynak = item.source.title if 'source' in item else "Sektörel Medya"
    st.caption(f"Kaynak: {kaynak} | [Orijinal Makaleye Git]({item.link})")
    
    with st.spinner("Yapay Zeka makaleyi sektörel bir derinlikle analiz ediyor..."):
        try:
            analiz = client.models.generate_content(model='gemini-2.5-flash', contents=f"Şu haberi detaylı, profesyonel bir sektörel makaleye dönüştür: {item.title}")
            st.markdown(f'<div style="font-size: 1.1rem; line-height: 1.8; color: #e0e0e0;">{analiz.text}</div>', unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Analiz sırasında bir hata oluştu: {e}")

# ==========================================
# 2. GÖRÜNÜM: ANA SAYFA (PORTAL)
# ==========================================
else:
    # Üst Başlık
    st.markdown('<p class="kantan-title">TRUCKER<span>.NEWS</span></p>', unsafe_allow_html=True)
    st.markdown(f'<p class="kantan-date">{datetime.now().strftime("%d %B %Y")} | GLOBAL AĞIR VASITA İSTİHBARATI</p>', unsafe_allow_html=True)

    # --- KATEGORİ SEKMELERİ (TABS) ---
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🌟 Öne Çıkanlar", 
        "🖥️ HMI", 
        "📡 Connectivity", 
        "🛡️ Sürücü Asistanı", 
        "⚡ Elektrifikasyon", 
        "🏭 Üreticiler"
    ])

    # Kategori Sorgu Tanımları
    sorgular = {
        "HMI": "heavy duty trucks HMI OR dashboard OR user interface",
        "Connectivity": "heavy duty trucks connectivity OR telematics OR software",
        "ADAS": "heavy duty trucks ADAS OR active brake assist OR driver assistance",
        "Elektrifikasyon": "heavy duty trucks electric OR EV OR battery",
        "Üretici": "heavy duty trucks MAN OR Scania OR Mercedes-Benz"
    }

    # --- SEKME 1: ÖNE ÇIKANLAR VE SON HABERLER ---
    with tab1:
        with st.spinner('Ana akış derleniyor...'):
            # İlk sayfa için geniş bir havuz (15 haber) çekiyoruz
            genel_haberler = kategori_verisi_getir("heavy duty trucks innovations", 15)
            
        if genel_haberler:
            st.subheader("🔥 Günün Öne Çıkanları")
            # İlk 3 haberi manşet (Hero) olarak büyük kartlarla basıyoruz
            hero_cols = st.columns(3)
            for i in range(3):
                if i < len(genel_haberler):
                    h = genel_haberler[i]
                    with hero_cols[i]:
                        img_url = resim_bul(h.link)
                        st.image(img_url, use_container_width=True)
                        st.markdown('<span class="tag-news">MANŞET</span>', unsafe_allow_html=True)
                        st.markdown(f'<p style="font-size: 1.2rem; font-weight: bold; margin-top: 10px;">{h.title[:80]}...</p>', unsafe_allow_html=True)
                        st.button("İncele", key=f"hero_{i}", on_click=detaya_git, args=(h,), use_container_width=True)

            st.write("---")
            
            # Geri kalan 12 haberi "Yeniden Eskiye" sıralayıp liste halinde basıyoruz
            st.subheader("⏱️ Son Haberler (Kronolojik)")
            
            kalan_haberler = genel_haberler[3:]
            
            def parse_date(entry):
                if 'published_parsed' in entry:
                    return time.mktime(entry.published_parsed)
                return 0

            # Tarihe göre sıralama (En yeni en üstte)
            sirali_haberler = sorted(kalan_haberler, key=parse_date, reverse=True)
            
            for i, h in enumerate(sirali_haberler):
                # Tarih formatını okunabilir hale getirme
                tarih_str = "Tarih Yok"
                if 'published_parsed' in h:
                    dt = datetime.fromtimestamp(time.mktime(h.published_parsed))
                    tarih_str = dt.strftime("%d %b %H:%M")

                col1, col2 = st.columns([1, 5])
                with col1:
                    st.markdown(f'<p class="latest-date">{tarih_str}</p>', unsafe_allow_html=True)
                with col2:
                    st.button(h.title, key=f"latest_{i}", on_click=detaya_git, args=(h,), use_container_width=True)


    # --- DİĞER KATEGORİ SEKMELERİNİ OLUŞTURAN YARDIMCI FONKSİYON ---
    def kategori_sekmesi_olustur(sorgu, tab_adi):
        with st.spinner(f'{tab_adi} verileri taranıyor...'):
            haberler = kategori_verisi_getir(sorgu, 6) # Her grup için 6 haber
            
        if haberler:
            # 6 haberi 2 satır, 3 kolon (Grid) şeklinde basıyoruz
            for row in range(0, 6, 3):
                cols = st.columns(3)
                for i in range(3):
                    idx = row + i
                    if idx < len(haberler):
                        h = haberler[idx]
                        with cols[i]:
                            img_url = resim_bul(h.link)
                            st.image(img_url, use_container_width=True)
                            st.markdown(f'<p style="font-size: 1.05rem; font-weight: bold; margin-top:10px;">{h.title[:80]}...</p>', unsafe_allow_html=True)
                            st.button("Detay", key=f"{tab_adi}_{idx}", on_click=detaya_git, args=(h,), use_container_width=True)

    # --- DİĞER SEKMELERİ DOLDURMA ---
    with tab2: kategori_sekmesi_olustur(sorgular["HMI"], "HMI")
    with tab3: kategori_sekmesi_olustur(sorgular["Connectivity"], "Conn")
    with tab4: kategori_sekmesi_olustur(sorgular["ADAS"], "ADAS")
    with tab5: kategori_sekmesi_olustur(sorgular["Elektrifikasyon"], "EV")
    with tab6: kategori_sekmesi_olustur(sorgular["Üretici"], "Uretici")
