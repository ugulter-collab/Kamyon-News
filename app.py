import streamlit as st
from google import genai
from googleapiclient.discovery import build
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time

# --- ANAHTARLAR ---
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
YOUTUBE_API_KEY = st.secrets["YOUTUBE_API_KEY"]

client = genai.Client(api_key=GEMINI_API_KEY)
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Trucker.News", page_icon="🚛", layout="wide")

st.markdown("""
<style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    body { background-color: #0e1117; }
    .kantan-title { font-family: 'Helvetica Neue', sans-serif; font-size: 3rem; font-weight: 900; color: #ffffff; letter-spacing: -1.5px; }
    .kantan-title span { color: #e63946; }
    .kantan-date { font-family: monospace; color: #888888; border-bottom: 1px solid #333; padding-bottom: 10px; margin-bottom: 30px; }
    .card-container { background-color: #161b22; border-radius: 10px; padding: 0px; transition: 0.3s; border: 1px solid #30363d; margin-bottom: 25px; height: 100%; }
    .card-container:hover { border-color: #e63946; transform: translateY(-5px); }
    .card-img { width: 100%; height: 200px; object-fit: cover; border-radius: 10px 10px 0 0; }
    .card-content { padding: 15px; }
    .card-title { font-size: 1.1rem; font-weight: bold; color: #f0f6fc; line-height: 1.4; margin-bottom: 10px; }
    .card-meta { font-size: 0.7rem; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; }
</style>
""", unsafe_allow_html=True)

# --- GELİŞMİŞ GÖRSEL BULUCU ---
@st.cache_data(ttl=3600)
def resim_bul(url):
    try:
        # Gerçek bir tarayıcı gibi davranan header
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # Google News linklerini takip et (allow_redirects=True)
        r = requests.get(url, headers=headers, timeout=8, allow_redirects=True)
        soup = BeautifulSoup(r.content, 'html.parser')
        
        # og:image veya twitter:image meta etiketlerini ara
        meta_image = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
        
        if meta_image and meta_image.get("content"):
            return meta_image["content"]
            
        # Eğer meta etiketi yoksa sayfadaki ilk büyük resmi bulmaya çalış
        for img in soup.find_all('img'):
            if img.get('src') and ('http' in img['src']) and (int(img.get('width', 0)) > 200 or 'banner' in img['src'] or 'headline' in img['src']):
                return img['src']
    except:
        pass
    # Hepsinde başarısız olursa kaliteli bir endüstriyel görsel döndür
    return "https://images.unsplash.com/photo-1586191582056-96fcfdf9fd8b?auto=format&fit=crop&q=80&w=800"

@st.cache_data(ttl=3600)
def verileri_hazirla():
    rss_url = "https://news.google.com/rss/search?q=heavy+duty+trucks+innovations&hl=en-US"
    haberler = feedparser.parse(rss_url).entries[:12]
    
    istek = youtube.search().list(q='heavy duty truck innovations 2026', part='snippet', type='video', maxResults=3, order='relevance')
    videolar = istek.execute().get('items', [])
    
    return haberler, videolar

# --- SESSION STATE ---
if 'sayfa' not in st.session_state: st.session_state.sayfa = 'ana'
if 'secili' not in st.session_state: st.session_state.secili = None

# --- EKRAN 1: DETAY SAYFASI ---
if st.session_state.sayfa == 'detay':
    if st.button("← Akışa Geri Dön"): 
        st.session_state.sayfa = 'ana'
        st.rerun()
    
    item = st.session_state.secili
    st.write("---")
    
    if 'link' in item: # Bu bir haberdir
        st.title(item.title)
        st.caption(f"Kaynak: {item.source.name} | [Habere Git]({item.link})")
        with st.spinner("Analist makaleyi hazırlıyor..."):
            analiz = client.models.generate_content(model='gemini-2.5-flash', contents=f"Şu haberi detaylı bir sektörel makaleye dönüştür: {item.title}")
            st.markdown(analiz.text)
    else: # Bu bir videodur
        st.title(item['snippet']['title'])
        st.video(f"https://www.youtube.com/watch?v={item['id']['videoId']}")
        with st.spinner("Video içeriği yazılı habere dönüştürülüyor..."):
            analiz = client.models.generate_content(model='gemini-2.5-flash', contents=f"Bu video içeriğini profesyonel bir yazılı habere dönüştür: {item['snippet']['title']}. Detaylar: {item['snippet']['description']}")
            st.markdown(analiz.text)

# --- EKRAN 2: ANA SAYFA ---
else:
    st.markdown('<p class="kantan-title">TRUCKER<span>.NEWS</span></p>', unsafe_allow_html=True)
    st.markdown(f'<p class="kantan-date">{datetime.now().strftime("%d %B %Y")} | STRATEJİK İSTİHBARAT</p>', unsafe_allow_html=True)
    
    with st.spinner('Gerçek zamanlı görseller ve haberler derleniyor...'):
        haberler, videolar = verileri_hazirla()

    # VİDEO BÖLÜMÜ
    st.subheader("📺 Video Analizleri")
    v_cols = st.columns(3)
    for i, v in enumerate(videolar):
        with v_cols[i]:
            st.image(v['snippet']['thumbnails']['high']['url'], use_container_width=True)
            st.markdown(f'<p class="card-title">{v["snippet"]["title"][:60]}...</p>', unsafe_allow_html=True)
            if st.button("İncele", key=f"v_{i}", use_container_width=True):
                st.session_state.secili = v
                st.session_state.sayfa = 'detay'
                st.rerun()

    st.write("---")
    st.subheader("📰 Yazılı Haber Akışı")
    
    # 12 HABER GRİD (4 satır x 3 sütun)
    for row in range(0, 12, 3):
        cols = st.columns(3)
        for i in range(3):
            idx = row + i
            if idx < len(haberler):
                h = haberler[idx]
                with cols[i]:
                    img_url = resim_bul(h.link)
                    st.image(img_url, use_container_width=True)
                    st.markdown(f'<p class="card-title">{h.title[:85]}...</p>', unsafe_allow_html=True)
                    if st.button("Detayları Oku", key=f"h_{idx}", use_container_width=True):
                        st.session_state.secili = h
                        st.session_state.sayfa = 'detay'
                        st.rerun()