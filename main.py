import time
import re
from numpy import empty
import yaml
import streamlit as st
import random
import logging
from writer.websearch import search as gsearch
from writer.suggest import get_article, get_page, ifidf_match
from writer.g2t import Graph2Text
from writer.t2g import Text2Graph

from multiprocessing import Process

st.set_page_config(
    page_title="AIContentCreator - Baseline version",
    page_icon="",
    layout="wide",
    initial_sidebar_state="auto",
    menu_items={
        'Get Help': 'https://tmtco.asia/',
        'Report a bug': "https://tmtco.asia/",
        'About': ""
     },
)
hide_footer_style = """
<style>
footer {visibility: hidden;}   
</style>
"""
st.markdown(hide_footer_style, unsafe_allow_html=True)

st.title("AI content creator")
st.text("machine-assistant for content writing")

# Set up  all things
with open("config.yaml", "r") as cf:
    try:
        args = yaml.safe_load(cf)
    except yaml.YAMLError as exc:
        print(exc)

G2T = Graph2Text(**args)
T2G = Text2Graph(**args)

logger = logging.getLogger(__name__)

f_handler = logging.FileHandler('file.log')
f_handler.setLevel(logging.ERROR)
f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
f_handler.setFormatter(f_format)

# Add handlers to the logger
logger.addHandler(f_handler)

if "input_text" not in st.session_state:
    st.session_state.input_text = ""
if "suggestions" not in st.session_state:
    st.session_state.suggestions = set()
if "searches" not in st.session_state:
    st.session_state.searches = iter(())
if "corpus" not in st.session_state:
    st.session_state.corpus = []
if "docfound" not in st.session_state:
    st.session_state.docfound = []


def reset_state():
    st.session_state.input_text = ""
    st.session_state.suggestions = set()
    st.session_state.searches = iter(())
    st.session_state.corpus = []
    st.session_state.docfound = []

def data_ingest(expect_corpus_size = None, timeout=60):
    start_time = time.time()
    suggestions = set()

    while time.time()-start_time < timeout:
        # Get more data nếu
        if not expect_corpus_size:
            if len(suggestions) > 5: 
                break
        elif len(st.session_state.corpus) >= expect_corpus_size:
            logger.info("Corpus size matches the expectation.")
            break

        try:
            url = next(st.session_state.searches)
        except StopIteration:
            break
        
        data = getar(url)
        if not data:
            continue

        for txt in data['headlines']:
            if any([(_ in input_text.split()) for _ in txt.split()]):
                suggestions.add(txt)
            else: 
                suggestions.add(f"{input_text.capitalize()}: {txt}")

        st.session_state.suggestions.update(suggestions)
        content = [p for p in data['content'] if len(p) > 256 and len(p) < 1000]
        st.session_state.corpus.extend(content)

@st.cache(allow_output_mutation=False, show_spinner=False, ttl=300)
def getar(url):
    page = get_page(url)
    data = None if not page else get_article(page['soup'], page['host'])
    return data


with open("stopwords.txt", 'r', encoding="utf8") as sw:
    STOPWORDS = sw.readlines()

sg, gen = st.columns(2)

container_input = sg.container()
container_sg = sg.container()
container_para = gen.container()

form = container_input.form(key="submit-sg-form")
input_text = re.sub("\s+", " ", form.text_input("Bạn muốn viết gì?"))

sug_btn = form.form_submit_button("Xem thêm gợi ý")
generate_btn = form.form_submit_button("Viết luôn (Ấn lần nữa để viết lại)")


if sug_btn: 
    logger.info("New Input text: " + input_text)
    logger.info("Old Input text: " + st.session_state.input_text)
    if input_text != st.session_state.input_text:
        # Update session state then do the search process
        reset_state()
        st.session_state.input_text = input_text
        st.session_state.searches = gsearch(input_text, num_results=100, max_requests=10, lang='vi')

    with st.spinner("Đang tìm ý tưởng..."):
        data_ingest()
        
    phrases = random.sample(st.session_state.suggestions, k=min(5, len(st.session_state.suggestions)))
    if not phrases: 
        container_sg.write("Hệ thống không tìm thấy thông tin liên quan, hãy thử lại với những câu gợi ý khác (Lưu ý: Thông tin nên thuộc lĩnh vực Công nghệ/Thiết bị số)")
    else: 
        container_sg.write(phrases)

if generate_btn:
    # container_para.empty()
    logger.info("New Input text: " + input_text)
    logger.info("Old Input text: " + st.session_state.input_text)

    if input_text != st.session_state.input_text: # If state's changed 
        # Update session state then do the search process
        reset_state()
        st.session_state.input_text = input_text
        st.session_state.searches = gsearch(input_text, num_results=100, max_requests=10, lang='vi')
    
    data = None
    with st.spinner("Đang tìm thông tin..."):
        data_ingest(expect_corpus_size=20)

        if len(st.session_state.docfound)==0:
            docs = ifidf_match(input_text, st.session_state.corpus, stopwords=STOPWORDS, top_k=5, **args)
            st.session_state.docfound = docs
        try:
            _, data = st.session_state.docfound.pop(0)
        except:
            container_para.write("Hệ thống không tìm thấy thông tin liên quan, hãy thử lại với những câu gợi ý khác (Lưu ý: Thông tin nên thuộc lĩnh vực Công nghệ/Thiết bị số)")
            st.stop()

    with st.spinner("Đang viết..."):
        try:
            logger.info("---> T2G")
            start = time.time()
            g = T2G.t2g(data)
            logger.info(f"Text to graph time: {time.time()-start:.3f}")

        except Exception as e:
            container_para.info("Đã xảy ra lỗi gì đó, xin hãy thử lại...")
            logger.debug(e)
            st.stop()
        
        try:
            logger.info("---> G2T")
            start = time.time()
            sents = G2T.g2t(g)
            logger.info(f"Graph to text time: {time.time()-start:.3f}")
            if sents:
                container_para.write(sents)  
            else: 
                container_para.info("Đã xảy ra lỗi gì đó, xin hãy thử lại...")
            
        except Exception as e:
            container_para.info("Đã xảy ra lỗi gì đó, xin hãy thử lại...")
            logger.debug(e)
            st.stop()
