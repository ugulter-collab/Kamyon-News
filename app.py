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
# 1. GÜVENLİK VE API BAĞLANTILARI
# ==========================================
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    st.error("Kritik Hata: API Şifreleri (Secrets) bulunamadı.")
    st.stop()

client = genai.Client(api_key=GEMINI_API_KEY)

# ==========================================
# 2. VERİTABANI BAĞLANTISI
# ==========================================
@st.cache_resource
def get_database():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        gc = gspread.authorize(creds)
        return gc.open("TruckerNews_DB").sheet1
    except Exception as e:
        return None

# ==========================================
# 3. GÖRSEL MOTORU (UNSPLASH KALDIRILDI, WIKIMEDIA EKLENDİ)
# ==========================================
@st.cache_data(ttl=900)
def rss_resim_al(entry):
    # media_content varsa
    if "media_content" in entry:
        return entry.media_content[0]["url"]

    # summary içinde img varsa
    if "summary" in entry:
        soup = BeautifulSoup(entry.summary, "html.parser")
        img = soup.find("img")
        if img and img.get("src"):
            return img["src"]

    return None
def resim_bul(google_news_url, baslik=""):
    yasakli_kelimeler = ['logo', 'icon', 'favicon', 'google', 'gstatic', 'avatar', 'news.google', 'blank']
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        
        # 1. Google Yönlendirmesini Aş
        ilk_istek = requests.get(google_news_url, headers=headers, timeout=5, allow_redirects=True)
        gercek_url = ilk_istek.url
        
        if "google.com" in gercek_url:
            soup_ilk = BeautifulSoup(ilk_istek.content, 'html.parser')
            a_tag = soup_ilk.find('a', href=True)
            if a_tag and 'http' in a_tag['href'] and 'accounts.google' not in a_tag['href']:
                gercek_url = a_tag['href']

        # 2. Gerçek Siteye Gir
        if "google.com" not in gercek_url:
            r = requests.get(gercek_url, headers=headers, timeout=8)
            soup = BeautifulSoup(r.content, 'html.parser')
            
            resim_url = None
            meta_img = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
            if meta_img and meta_img.get("content"):
                resim_url = meta_img["content"]
                
            if resim_url:
                res_url_duzenli = urllib.parse.urljoin(gercek_url, resim_url)
                if not any(x in res_url_duzenli.lower() for x in yasakli_kelimeler):
                    return res_url_duzenli

    except Exception:
        pass
    
    # 3. YEDEKLER: WIKIPEDIA DOĞRULANMIŞ TIR GÖRSELLERİ (ASLA KÖPEK ÇIKMAZ)
    baslik_lower = baslik.lower()
    if "volvo" in baslik_lower: 
        return "https://upload.wikimedia.org/wikipedia/commons/thumb/7/77/Volvo_FH_500.jpg/800px-Volvo_FH_500.jpg"
    elif "scania" in baslik_lower: 
        return "https://upload.wikimedia.org/wikipedia/commons/thumb/2/25/Scania_R500_V8.jpg/800px-Scania_R500_V8.jpg"
    elif "mercedes" in baslik_lower or "actros" in baslik_lower: 
        return "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Mercedes-Benz_Actros_1845.jpg/800px-Mercedes-Benz_Actros_1845.jpg"
    elif "freightliner" in baslik_lower: 
        return "https://upload.wikimedia.org/wikipedia/commons/thumb/3/30/Freightliner_Cascadia_Evolution.jpg/800px-Freightliner_Cascadia_Evolution.jpg"
    elif "bharat" in baslik_lower or "tata" in baslik_lower: 
        return "https://upload.wikimedia.org/wikipedia/commons/thumb/0/00/Tata_Prima_4928_S.jpg/800px-Tata_Prima_4928_S.jpg"
    else: 
        return "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/MAN_TGX_18.440_XXL.jpg/800px-MAN_TGX_18.440_XXL.jpg"

# ==========================================
# 4. VERİ GETİRME VE ANALİZ FONKSİYONLARI
# ==========================================
@st.cache_data(ttl=900)
def veri_getir(sorgu, adet, taze_mi=True):
    zaman_filtresi = " when:3d"
    guvenli_sorgu = urllib.parse.quote(sorgu + zaman_filtresi)
    rss_url = f"https://news.google.com/rss/search?q={guvenli_sorgu}&hl=en-US"
    feed = feedparser.parse(rss_url)
    return feed.entries[:adet]

def akilli_analiz_getir(link, baslik):
    sheet = get_database()
    if sheet is not None:
        try:
            for kayit in sheet.get_all_records():
                if kayit.get("Link") == link:
                    return f"*(Bu piyasa raporu arşivden getirilmiştir ⚡)*\n\n{kayit.get('Analiz')}"
        except: pass

    prompt = f"""
    Sen ticari araç sektöründe çalışan bir Piyasa Araştırmacısı ve Müşteri Analistisin.
    Şu haberi oku ve okuması çok kolay, net bir Türkçe piyasa raporu yaz: {baslik}
    
    Kurallar:
    1. Çok teknik detaylara boğma. Yenilik nedir ve müşteriye faydası nedir? Buna odaklan.
    2. Markanın pazardaki etkisini yorumla.
    3. Yazı ferah ve okuması kolay olsun. Kısa paragraflar kullan.
    4. Sonuna "Piyasa ve Müşteri Etkisi" başlıklı 2 maddelik özet ekle.
    """
    try:
        cevap = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        analiz_metni = cevap.text
        if sheet is not None: sheet.append_row([link, analiz_metni])
        return f"*(Yapay Zeka bu piyasa raporunu şimdi derledi 🤖)*\n\n{analiz_metni}"
    except Exception as e:
        return f"Analiz oluşturulurken hata oluştu."

# ==========================================
# 5. İSKELET VE TASARIM
# ==========================================
st.set_page_config(page_title="Trucker.Markets", page_icon="🚛", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    body { background-color: #0e1117; }
    
    .block-container { max-width: 1100px; margin: 0 auto; padding-top: 2rem; }
    
    .kantan-title { font-family: 'Helvetica Neue', sans-serif; font-size: 2.8rem; font-weight: 900; color: #ffffff; letter-spacing: -1px; margin-bottom: 0px;}
    .kantan-title span { color: #e63946; }
    .kantan-date { font-family: monospace; color: #888888; border-bottom: 1px solid #333; padding-bottom: 10px; margin-bottom: 25px; font-size: 0.9rem;}
    
    .card-container { background-color: #161b22; border-radius: 8px; border: 1px solid #30363d; margin-bottom: 15px; padding-bottom: 10px; transition: 0.3s;}
    .card-container:hover { border-color: #e63946; transform: translateY(-3px); }
    .card-img { width: 100%; height: 180px; object-fit: cover; border-radius: 8px 8px 0 0; margin-bottom: 10px; background-color: #0e1117;}
    .card-title { font-size: 1rem; font-weight: bold; color: #e0e0e0; line-height: 1.3; margin-bottom: 15px; padding: 0 10px; height: 60px; overflow: hidden;}
    
    .stTabs [data-baseweb="tab-list"] { gap: 8px; border-bottom: 2px solid #30363d;}
    .stTabs [data-baseweb="tab"] { background-color: #161b22; border-radius: 4px 4px 0px 0px; padding: 10px 15px; color: #888; border: 1px solid #30363d; border-bottom: none;}
    .stTabs [aria-selected="true"] { background-color: #e63946 !important; color: white !important; font-weight: bold; border-color: #e63946 !important;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 6. SAYFA YÖNETİMİ VE EKRANLAR
# ==========================================
if 'page' not in st.session_state: st.session_state.page = 'home'
if 'data' not in st.session_state: st.session_state.data = None

def view_details(item):
    st.session_state.data = item
    st.session_state.page = 'details'

def go_home():
    st.session_state.page = 'home'

if st.session_state.page == 'details':
    st.button("← Geri Dön", on_click=go_home)
    h = st.session_state.data
    st.write("---")
    
    detay_resim_url = resim_bul(h.link, h.title)
    st.image(detay_resim_url, use_container_width=True)
    
    st.title(h.title)
    kaynak = h.source.title if hasattr(h, 'source') and hasattr(h.source, 'title') else 'Global Medya'
    st.caption(f"Kaynak: {kaynak} | [Haberin Orijinaline Git]({h.link})")
    
    with st.spinner("Piyasa raporu hazırlanıyor..."):
        analiz_sonucu = akilli_analiz_getir(h.link, h.title)
        st.markdown(f'<div style="font-size:1.15rem; line-height:1.8; color:#e0e0e0; padding: 0 10px;">{analiz_sonucu}</div>', unsafe_allow_html=True)

else:
    st.markdown('<p class="kantan-title">TRUCKER<span>.MARKETS</span></p>', unsafe_allow_html=True)
    st.markdown(f'<p class="kantan-date">{datetime.now().strftime("%d %B %Y")} | MARKALAR, YENİLİKLER VE MÜŞTERİ GERİ BİLDİRİMLERİ</p>', unsafe_allow_html=True)

    tabs = st.tabs(["🌟 Piyasaya Bakış", "🇸🇪 Volvo & Scania", "🇩🇪 Mercedes-Benz", "🇺🇸 Freightliner", "🇮🇳 BharatBenz", "🌐 Yeni Oyuncular"])
    
    sorgular = {
        "Piyasa": "heavy duty trucks new models OR customer feedback report",
        "VolvoScania": "Volvo trucks customer review OR Scania trucks new features",
        "Mercedes": "Mercedes-Benz Actros feedback OR Mercedes trucks innovations",
        "Freightliner": "Freightliner cascadia reviews OR Freightliner new truck market",
        "BharatBenz": "BharatBenz trucks performance OR BharatBenz market report",
        "YeniOyuncular": "new heavy truck brands OR electric truck market feedback"
    }

    def tab_doldur(sorgu, t_id, adet=9):
        with st.spinner("Piyasa verileri toplanıyor..."):
            haberler = veri_getir(sorgu, adet, taze_mi=True)
            if not haberler:
                st.info("Bu marka için son günlerde yeni bir rapor bulunamadı.")
                return
                
            for row in range(0, adet, 3):
                cols = st.columns(3)
                for j in range(3):
                    idx = row + j
                    if idx < len(haberler):
                        h = haberler[idx]
                        with cols[j]:
                            img_url = resim_bul(h.link, h.title)
                            st.markdown(f"""
                            <div class="card-container">
                                <img src="{img_url}" class="card-img">
                                <div class="card-title">{h.title[:80]}...</div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            st.button("Raporu Oku", key=f"btn_{t_id}_{idx}", on_click=view_details, args=(h,), use_container_width=True)

    with tabs[0]: tab_doldur(sorgular["Piyasa"], "piyasa", 12)
    with tabs[1]: tab_doldur(sorgular["VolvoScania"], "vs")
    with tabs[2]: tab_doldur(sorgular["Mercedes"], "merc")
    with tabs[3]: tab_doldur(sorgular["Freightliner"], "freight")
    with tabs[4]: tab_doldur(sorgular["BharatBenz"], "bharat")
    with tabs[5]: tab_doldur(sorgular["YeniOyuncular"], "yeni")
