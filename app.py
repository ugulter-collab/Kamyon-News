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
# 2. RAM HAFIZASI
# ==========================================
if 'mevcut_raporlar' not in st.session_state:
    st.session_state.mevcut_raporlar = {}
    if sheet:
        try:
            for row in sheet.get_all_records():
                st.session_state.mevcut_raporlar[row.get("Link")] = row.get("Analiz")
        except: pass

# ==========================================
# 3. YENİ: TOPLU BAŞLIK ÇEVİRİ MOTORU (ANA SAYFA İÇİN)
# ==========================================
@st.cache_data(ttl=900)
def basliklari_cevir(baslik_listesi):
    if not baslik_listesi: return []
    prompt = "Aşağıdaki İngilizce haber başlıklarını sırasını bozmadan Türkçeye çevir. Her satıra sadece çeviri metnini yaz, madde işareti veya numara kullanma:\n" + "\n".join(baslik_listesi)
    try:
        cevap = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        ceviriler = [b.strip().strip('-*1234567890. ') for b in cevap.text.strip().split('\n') if b.strip()]
        # Hata kontrolü: Çeviri sayısı eşleşiyorsa kullan, yoksa orijinali ver
        if len(ceviriler) == len(baslik_listesi):
            return ceviriler
        return baslik_listesi
    except:
        return baslik_listesi

# ==========================================
# 4. GELİŞMİŞ GÖRSEL BULUCU
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
# 5. YORUMSUZ ÇEVİRİ MOTORU (YAPAY ZEKA)
# ==========================================
def ceviri_hazirla(link, baslik):
    if link in st.session_state.mevcut_raporlar:
        return st.session_state.mevcut_raporlar[link]

    # PROMPT DEĞİŞTİRİLDİ: Analiz kaldırıldı, sadece objektif çeviri eklendi.
    prompt = f"Sen profesyonel bir çevirmensin. Aşağıdaki haber başlığını ve konusunu hiçbir yorum, analiz veya 'müşteriye etkisi' gibi çıkarımlar eklemeden doğrudan, objektif bir haber metni olarak Türkçeye çevir. Sadece haberi aktar:\n\n{baslik}"
    try:
        cevap = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        if sheet: sheet.append_row([link, cevap.text])
        st.session_state.mevcut_raporlar[link] = cevap.text 
        return cevap.text
    except: return "Haber şu an çevrilemedi."

# ==========================================
# 6. İSKELET VE TASARIM
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

if 'page' not in st.session_state: st.session_state.page = 'home'
if 'data' not in st.session_state: st.session_state.data = None
if 'gosterilecek_baslik' not in st.session_state: st.session_state.gosterilecek_baslik = ""

def view_details(item, turkce_baslik):
    st.session_state.data = item
    st.session_state.gosterilecek_baslik = turkce_baslik
    st.session_state.page = 'details'

def go_home():
    st.session_state.page = 'home'

# ==========================================
# 7. EKRANLAR
# ==========================================
if st.session_state.page == 'details':
    st.button("← Geri Dön", on_click=go_home)
    h = st.session_state.data
    st.write("---")
    
    st.image(resim_bul(h.link, h.title), use_container_width=True)
    st.title(st.session_state.gosterilecek_baslik) # Başlık artık detay sayfasında da Türkçe
    st.caption(f"[Haberin Orijinaline Git]({h.link})")
    
    analiz = st.session_state.mevcut_raporlar.get(h.link)
    
    if not analiz:
        with st.spinner("Haber Türkçeye çevriliyor..."):
            analiz = ceviri_hazirla(h.link, h.title)
            
    st.markdown(f'<div style="font-size:1.15rem; line-height:1.8; color:#e0e0e0;">{analiz}</div>', unsafe_allow_html=True)

else:
    st.markdown('<p class="kantan-title">TRUCKER<span>.MARKETS</span></p>', unsafe_allow_html=True)
    st.write(f"Global Haber Çeviri Portalı | {datetime.now().strftime('%d %B %Y')}")
    
    tab_isimleri = ["🌟 Piyasalar", "🇸🇪 Volvo & Scania", "🇩🇪 Mercedes", "🇺🇸 Freightliner", "🇮🇳 BharatBenz"]
    tabs = st.tabs(tab_isimleri)
    sorgular = ["heavy truck news", "Volvo Scania trucks", "Mercedes Actros news", "Freightliner trucks", "BharatBenz trucks"]

    for i, tab in enumerate(tabs):
        with tab:
            rss_link = f"https://news.google.com/rss/search?q={urllib.parse.quote(sorgular[i] + ' when:3d')}&hl=en-US"
            haberler = feedparser.parse(rss_link).entries[:6]
            
            # ANA SAYFA İÇİN BAŞLIKLARI TOPLUCA TÜRKÇEYE ÇEVİR (1 saniye sürer ve hafızaya alınır)
            orijinal_basliklar = [h.title for h in haberler]
            turkce_basliklar = basliklari_cevir(orijinal_basliklar)
            
            rows = [st.columns(3), st.columns(3)]
            for idx, h in enumerate(haberler):
                col = rows[idx // 3][idx % 3]
                with col:
                    img = resim_bul(h.link, h.title)
                    gosterilecek_baslik = turkce_basliklar[idx] if idx < len(turkce_basliklar) else h.title
                    
                    st.markdown(f'<div class="card-container"><img src="{img}" class="card-img"><div class="card-title">{gosterilecek_baslik[:70]}...</div></div>', unsafe_allow_html=True)
                    st.button("Haberi Oku", key=f"btn_{i}_{idx}", on_click=view_details, args=(h, gosterilecek_baslik), use_container_width=True)
