"""Picks settings on the VALIDATION split only, so the test numbers stay clean.

Tunes: how much of the context to use as the query, BM25 k1/b, which
sentence-transformer to use, and the RRF constant k.
Writes results/validation_tuning.csv and results/chosen_settings.json.
"""
import json
import os
import sys

import pandas as pd

os.environ.setdefault("HF_HOME", "data/hf_cache")
sys.path.insert(0, os.path.dirname(__file__))

from data import load_split, query_window
from dense import dense_scores
from fusion import rrf_batch, top_k
from index import BM25, InvertedIndex, TfidfRanker
from metrics import rank_of_gold, ranks_from_lists, summarize
from preprocess import tokenize

DENSE_MODELS = ["sentence-transformers/all-MiniLM-L6-v2", "BAAI/bge-small-en-v1.5"]
WINDOWS = [None, 96, 64, 32]

rows = []


def log(group, setting, ranks):
    m = summarize(ranks)
    rows.append({"group": group, "setting": setting, **{k: round(v, 4) for k, v in m.items()}})
    print(f"{group:10s} {setting:40s} MRR={m['MRR']:.4f} R@10={m['R@10']:.4f}")


def main():
    val = load_split("validation")
    print(len(val.queries), "validation queries,", len(val.corpus), "holdings")
    index = InvertedIndex([tokenize(d) for d in val.corpus])

    # 1. query window, with default BM25
    bm25 = BM25(index)
    for w in WINDOWS:
        q_tok = [tokenize(query_window(q, w)) for q in val.queries]
        log("window", f"BM25 last {w or 'all'} words", rank_of_gold(bm25.score_batch(q_tok), val.gold))
    best_w = min(WINDOWS, key=lambda w: -next(r["MRR"] for r in rows
                                                 if r["setting"] == f"BM25 last {w or 'all'} words"))

    # 2. BM25 parameters
    q_tok = [tokenize(query_window(q, best_w)) for q in val.queries]
    best_bm25, best_mrr = None, -1
    for k1 in [0.3, 0.6, 0.9, 1.2, 1.5, 2.0]:
        for b in [0.3, 0.5, 0.75, 0.9, 1.0]:
            ranks = rank_of_gold(BM25(index, k1, b).score_batch(q_tok), val.gold)
            log("bm25", f"k1={k1} b={b}", ranks)
            if rows[-1]["MRR"] > best_mrr:
                best_mrr, best_bm25 = rows[-1]["MRR"], (k1, b)

    # 3. preprocessing ablation for TF-IDF (stop words / stemming)
    queries = [query_window(q, best_w) for q in val.queries]
    for sw, st in [(False, False), (True, False), (True, True)]:
        tf = TfidfRanker(val.corpus, remove_stopwords=sw, use_stemming=st)
        log("prep", f"TF-IDF stopwords={sw} stemming={st}", rank_of_gold(tf.score_batch(queries), val.gold))

    # 4. dense models, full context vs window (the models cut input at 256-512
    # word pieces, so the end of a long context, next to the citation, can get lost)
    for model in DENSE_MODELS:
        for w in [None, 96, 64]:
            qs = [query_window(q, w) for q in val.queries]
            log("dense", f"{model.split('/')[-1]} last {w or 'all'} words",
                rank_of_gold(dense_scores(model, qs, val.corpus), val.gold))
    dense_rows = [r for r in rows if r["group"] == "dense"]
    best_dense = max(dense_rows, key=lambda r: r["MRR"])["setting"]
    dense_name = next(m for m in DENSE_MODELS if m.split("/")[-1] == best_dense.split()[0])
    dense_w = None if "last all" in best_dense else int(best_dense.split("last ")[1].split()[0])

    # 5. RRF constant
    s_bm25 = BM25(index, *best_bm25).score_batch(q_tok)
    s_tfidf = TfidfRanker(val.corpus).score_batch(queries)
    s_dense = dense_scores(dense_name, [query_window(q, dense_w) for q in val.queries], val.corpus)
    tops = [top_k(s, 1000) for s in (s_tfidf, s_bm25, s_dense)]
    best_k, best_rrf = 60, -1
    for k in [1, 5, 10, 30, 60, 100]:
        ranks = ranks_from_lists(rrf_batch(tops, k=k), val.gold)
        log("rrf", f"k={k}", ranks)
        if rows[-1]["MRR"] > best_rrf:
            best_rrf, best_k = rows[-1]["MRR"], k

    os.makedirs("results", exist_ok=True)
    pd.DataFrame(rows).to_csv("results/validation_tuning.csv", index=False)
    chosen = {"query_window": best_w, "bm25_k1": best_bm25[0], "bm25_b": best_bm25[1],
              "dense_model": dense_name, "dense_query_window": dense_w, "rrf_k": best_k}
    json.dump(chosen, open("results/chosen_settings.json", "w"), indent=2)
    print(chosen)


if __name__ == "__main__":
    main()
