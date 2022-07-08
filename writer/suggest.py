import itertools
import os, time, json, logging, unicodedata
import re
import http.client
from urllib.parse import urlparse
import ssl
from bs4 import BeautifulSoup

from .ml_tutorial import tfidf
from .websearch import search
from tmtcorenlp import TmtCoreNLP

logger = logging.getLogger(__name__)

ssl._create_default_https_context = ssl._create_unverified_context

__SRC = os.path.dirname(os.path.abspath(__file__))
with open(f"{__SRC}/templates.json", encoding="utf8") as f:
    template = json.load(f)

def get_page(url, timeout=15):
    logger.info(f": Request page: {url}")
    u = urlparse(url)
    netloc = u.netloc
    path = u.path
    try:
        conn = http.client.HTTPSConnection(netloc, timeout=timeout)
    except: 
        logger.info(f"=== Can't reach this page: {netloc}.")
        return 

    payload = ''
    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.75 Safari/537.36'}
    try:
        conn.request("GET", path, payload, headers)
        res = conn.getresponse()
        html = res.read()
        soup = BeautifulSoup(html, 'html.parser')
        return {
            "host": netloc, 
            "soup": soup
        }
    except: 
        logger.info(f"=== Can't get page content: {netloc}.")
        return 
    
def get_article(soup, host, ignore_short_headline=5) -> list:
    logger.info(f"GET CONTENT PAGE: {host}")
    if host not in template.keys():
        logger.info(f"=== {host} has not defined in templates")
        return

    data = {
        "headlines": [],
        "content": [""]
    }
    ar_sel = template[host]["article"]["selector"]

    head_sel = template[host]["header"]["selector"]
    head_name = '' if not(head_sel) else \
                [s.strip().split()[-1].split('.', maxsplit=1)[0] for s in head_sel.split(',')]

    text_sel = template[host]["content"]["selector"]
    text_name = '' if not(text_sel) else \
                [s.strip().split()[-1].split('.', maxsplit=1)[0] for s in text_sel.split(',')]
    
    for _ in soup.select(ar_sel):
        line = unicodedata.normalize("NFKD", _.getText()).strip()

        if _.name in head_name:
            line = max(re.split(r'[`#.]', line), key=len).strip('\s\n\t')
            if len(line.split()) > ignore_short_headline:
                data["headlines"].append(line)
                data["content"].append(line)

        elif _.name in text_name: 
            data["content"][-1] = data["content"][-1] + "\n" + line

    if len(data["content"]) == 1: 
        data["content"] = data["content"][0].splitlines(keepends=False)

    logger.info(f"=== Got {len(data)} paragraphs from {host}\n")
    return data

from vncorenlp import VnCoreNLP

def ifidf_match(user_question, corpus, stopwords, top_k=5, **args):
    logger.info(f"=== Corpus size: {len(corpus)}")
    if not corpus: 
        return []

    nlp = VnCoreNLP(address=args['vncorenlp']['host'], port=args['vncorenlp']['port'])

    def wseg(doc: str):
        tok_sents = nlp.tokenize(doc)
        sents = [' '.join(_) for _ in tok_sents]
        return sents

    # Preprocessing
    corpus_ = list(itertools.chain.from_iterable([wseg(doc) for doc in corpus]))
    logger.info('=== Creating tfidf matrix...')

    # Learn vocabulary and idf, return term-document matrix
    _,V = tfidf.create_tfidf_features(corpus_, stopwords=stopwords, ngram_range=(1, 3))
    search_start = time.time()

    resource = [' '.join(wseg(doc)) for doc in corpus]
    query = wseg(user_question)

    sim_vecs, cosine_similarities = tfidf.calculate_similarity(resource, V, query, top_k=min(top_k, len(resource)))
    search_time = time.time() - search_start

    logger.info("=== search time: {:.2f} ms".format(search_time * 1000))
    ret = [(cosine_similarities[index], corpus[index]) for index in sim_vecs]
    print(ret)
    return ret
    