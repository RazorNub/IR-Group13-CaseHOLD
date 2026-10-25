"""Search interface for the demo.

Run from the project folder:  streamlit run app/search_app.py
Type any legal passage (or load a CaseHOLD test query) and compare the
holdings returned by TF-IDF, BM25, the dense model and the RRF hybrid.
"""
import json
import os
import sys

import numpy as np
import streamlit as st

os.environ.setdefault("HF_HOME", "data/hf_cache")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sentence_transformers import SentenceTransformer

from data import load_split, query_window
from dense import device, encode
from fusion import rrf
from index import BM25, InvertedIndex, TfidfRanker
from preprocess import tokenize

st.set_page_config(page_title="CaseHOLD Legal Search", layout="wide")


@st.cache_resource(show_spinner="Building indexes over the test holdings...")
def load_everything():
    cfg = json.load(open("results/chosen_settings.json"))
    test = load_split("test")
    index = InvertedIndex([tokenize(d) for d in test.corpus])
    bm25 = BM25(index, cfg["bm25_k1"], cfg["bm25_b"])
    tfidf = TfidfRanker(test.corpus)
    models = {"Dense": cfg["dense_model"]}
    if os.path.isdir("models/finetuned-dense"):
        models["Dense (fine-tuned)"] = "models/finetuned-dense"
    dense = {}
    for label, name in models.items():
        m = SentenceTransformer(name, device=device())
        dense[label] = (m, encode(name, test.corpus, model=m))
    return cfg, test, index, bm25, tfidf, dense


def search(text, cfg, bm25, tfidf, dense, dense_label, k=10):
    sparse_q = query_window(text, cfg["query_window"])
    dense_q = query_window(text, cfg["dense_query_window"])
    tokens = tokenize(sparse_q)

    bm = bm25.score_one(tokens)
    bm_rank = sorted(bm, key=bm.get, reverse=True)[:1000]
    tf = tfidf.score_batch([sparse_q])[0]
    tf_rank = list(np.argsort(-tf)[:1000])
    model, emb = dense[dense_label]
    q = model.encode([dense_q], normalize_embeddings=True)[0]
    de = emb @ q
    de_rank = list(np.argsort(-de)[:1000])
    hybrid = rrf([tf_rank, bm_rank, de_rank], k=cfg["rrf_k"])
    return {
        "TF-IDF": [(d, tf[d]) for d in tf_rank[:k]],
        "BM25": [(d, bm[d]) for d in bm_rank[:k]],
        dense_label: [(d, de[d]) for d in de_rank[:k]],
        "Hybrid RRF": [(d, None) for d in hybrid[:k]],
    }, tokens


cfg, test, index, bm25, tfidf, dense = load_everything()

st.title("Legal holding search on CaseHOLD")
st.caption(f"{len(test.corpus):,} holdings from the CaseHOLD test split. "
           "The query is the passage that cites a case; the results are candidate holdings. "
           "Each result shows its document id (doc N), the holding's position in the collection.")

with st.sidebar:
    st.header("Query")
    # ?qid=296 or ?text=... in the URL pre-fills the inputs (handy for demos)
    qp = st.query_params
    mode = st.radio("Source", ["CaseHOLD test query", "Type my own"],
                    index=1 if "text" in qp else 0)
    dense_label = st.selectbox("Dense model", list(dense))
    per_page = st.slider("Results per page", 3, 20, 10)
    page = st.number_input("Page", 1, 50, int(st.query_params.get("page", 1)))

gold = None
if mode == "CaseHOLD test query":
    qid = st.number_input("Test query id (0-3599)", 0, len(test.queries) - 1,
                          int(qp.get("qid", 0)))
    text = test.queries[qid]
    gold = test.gold[qid]
    st.text_area("Citing context", text, height=150, disabled=True)
else:
    text = st.text_area("Type a passage", qp.get("text", "the anticipation of increased interference or potential "
                        "hazards on the land remaining after a taking can be considered in assessing "
                        "severance damages"), height=120)

if text.strip():
    # fetch everything up to the end of the chosen page, then show only that page
    k = page * per_page
    start = k - per_page
    results, tokens = search(text, cfg, bm25, tfidf, dense, dense_label, k)
    st.markdown(f"**Page {page}** (ranks {start + 1} to {k})")
    st.markdown("**Query terms after preprocessing:** " + ", ".join(sorted(set(tokens))[:40]))
    cols = st.columns(len(results))
    for col, (name, hits) in zip(cols, results.items()):
        with col:
            st.subheader(name)
            if gold is not None:
                pos = [d for d, _ in hits].index(gold) + 1 if gold in [d for d, _ in hits] else None
                st.caption(f"correct holding at rank {pos}" if pos else f"correct holding not in top {k}")
            for r, (d, s) in enumerate(hits[start:], start + 1):
                tag = " **[correct]**" if d == gold else ""
                score = f" ({s:.3f})" if s is not None else ""
                # `doc N` is the holding's id in the collection (0 to 13,296); the same id in
                # different columns means the same holding was returned by both methods
                st.markdown(f"{r}.{tag} `doc {d}`{score} {test.corpus[d]}")
