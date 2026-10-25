"""Runs every model on the CaseHOLD TEST split using the settings picked on
validation (results/chosen_settings.json).

Two evaluation settings:
  full pool  : rank all unique holdings of the test split for every query
  5-choice   : rank only the 5 candidates CaseHOLD gives for that query
Outputs go to results/.
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

os.environ.setdefault("HF_HOME", "data/hf_cache")
sys.path.insert(0, os.path.dirname(__file__))

from data import load_split, query_window
from dense import cross_encoder_scores, dense_scores
from fusion import rrf, rrf_batch, top_k
from index import BM25, InvertedIndex, TfidfRanker
from metrics import rank_of_gold, ranks_from_lists, summarize
from preprocess import tokenize

CROSS_ENCODER = "cross-encoder/ms-marco-MiniLM-L6-v2"
FINETUNED = "models/finetuned-dense"
RERANK_DEPTH = 20


def five_choice_ranks(scores, split):
    cand = np.asarray(split.candidates)
    sub = np.take_along_axis(scores, cand, axis=1)
    return rank_of_gold(sub, np.asarray(split.labels)), sub


def main():
    cfg = json.load(open("results/chosen_settings.json"))
    test = load_split("test")
    gold = np.asarray(test.gold)
    print(len(test.queries), "test queries,", len(test.corpus), "holdings")
    sparse_q = [query_window(q, cfg["query_window"]) for q in test.queries]
    dense_q = [query_window(q, cfg["dense_query_window"]) for q in test.queries]

    scores, timing = {}, {}

    t = time.time()
    tfidf = TfidfRanker(test.corpus)
    timing["TF-IDF index"] = time.time() - t
    t = time.time()
    scores["TF-IDF"] = tfidf.score_batch(sparse_q)
    timing["TF-IDF search"] = time.time() - t

    t = time.time()
    index = InvertedIndex([tokenize(d) for d in test.corpus])
    bm25 = BM25(index, cfg["bm25_k1"], cfg["bm25_b"])
    timing["BM25 index"] = time.time() - t
    t = time.time()
    scores["BM25"] = bm25.score_batch([tokenize(q) for q in sparse_q])
    timing["BM25 search"] = time.time() - t
    json.dump(index.stats(), open("results/index_stats.json", "w"), indent=2)

    t = time.time()
    scores["Dense"] = dense_scores(cfg["dense_model"], dense_q, test.corpus)
    timing["Dense encode+search"] = time.time() - t
    if os.path.isdir(FINETUNED):
        t = time.time()
        scores["Dense (fine-tuned)"] = dense_scores(FINETUNED, dense_q, test.corpus)
        timing["Dense fine-tuned encode+search"] = time.time() - t

    full_ranks, five_ranks, five_sub = {}, {}, {}
    for name, s in scores.items():
        full_ranks[name] = rank_of_gold(s, gold)
        five_ranks[name], five_sub[name] = five_choice_ranks(s, test)

    # hybrids: RRF over top-1000 lists (full pool) and over the 5 candidates
    tops = {name: top_k(s, 1000) for name, s in scores.items()}
    # main runs use the standard k = 60 from the brief; one extra run uses the k picked on validation
    tuned_k = cfg["rrf_k"]
    hybrids = {"Hybrid RRF (TF-IDF+BM25+Dense)": (["TF-IDF", "BM25", "Dense"], 60),
               f"Hybrid RRF (TF-IDF+BM25+Dense, k={tuned_k})": (["TF-IDF", "BM25", "Dense"], tuned_k),
               "Hybrid RRF (BM25+Dense)": (["BM25", "Dense"], 60)}
    if "Dense (fine-tuned)" in scores:
        hybrids["Hybrid RRF (BM25+Dense fine-tuned)"] = (["BM25", "Dense (fine-tuned)"], 60)
    hybrid_lists = {}
    for hname, (parts, k) in hybrids.items():
        hybrid_lists[hname] = rrf_batch([tops[p] for p in parts], k=k)
        full_ranks[hname] = ranks_from_lists(hybrid_lists[hname], gold)
        r5 = []
        for i in range(len(gold)):
            per_model = [list(np.argsort(-five_sub[p][i])) for p in parts]
            fused = rrf(per_model, k=k)
            r5.append(fused.index(test.labels[i]) + 1)
        five_ranks[hname] = np.asarray(r5)

    # cross-encoder: re-rank the top 20 of the 3-way hybrid, and score the 5 choices
    base = "Hybrid RRF (TF-IDF+BM25+Dense)"
    t = time.time()
    pairs = [(dense_q[i], test.corpus[d]) for i in range(len(gold)) for d in hybrid_lists[base][i][:RERANK_DEPTH]]
    ce = cross_encoder_scores(CROSS_ENCODER, pairs).reshape(len(gold), RERANK_DEPTH)
    reranked = []
    for i in range(len(gold)):
        head = [hybrid_lists[base][i][j] for j in np.argsort(-ce[i])]
        reranked.append(head + hybrid_lists[base][i][RERANK_DEPTH:])
    full_ranks["Hybrid + cross-encoder re-rank"] = ranks_from_lists(reranked, gold)
    timing["Cross-encoder re-rank top-20"] = time.time() - t
    pairs5 = [(dense_q[i], test.corpus[d]) for i in range(len(gold)) for d in test.candidates[i]]
    ce5 = cross_encoder_scores(CROSS_ENCODER, pairs5).reshape(len(gold), 5)
    five_ranks["Cross-encoder (ms-marco)"] = rank_of_gold(ce5, np.asarray(test.labels))

    # tables
    full_rows = [{"model": n, **summarize(r)} for n, r in full_ranks.items()]
    pd.DataFrame(full_rows).round(4).to_csv("results/test_full_pool.csv", index=False)
    five_rows = []
    for n, r in five_ranks.items():
        m = summarize(r, ks=(1, 2, 3))
        five_rows.append({"model": n, "accuracy": m["R@1"], "MRR": m["MRR"],
                          "R@2": m["R@2"], "R@3": m["R@3"], "nDCG@5": m["nDCG@10"]})
    pd.DataFrame(five_rows).round(4).to_csv("results/test_five_choice.csv", index=False)
    pd.Series(timing).round(2).to_csv("results/timing_seconds.csv", header=["seconds"])

    # paired significance: reciprocal ranks of each model vs BM25 (Wilcoxon signed-rank)
    sig = []
    for n, r in full_ranks.items():
        if n == "BM25":
            continue
        a = np.where(np.isfinite(r), 1 / r, 0)
        b = 1 / full_ranks["BM25"]
        stat = wilcoxon(a, b)
        sig.append({"model": n, "vs": "BM25", "mean_RR_diff": round(float((a - b).mean()), 4),
                    "p_value": float(stat.pvalue)})
    pd.DataFrame(sig).to_csv("results/significance_vs_bm25.csv", index=False)

    # keep ranks and top-10 lists for figures and error analysis
    np.savez("results/ranks.npz", **{f"full|{k}": v for k, v in full_ranks.items()},
             **{f"five|{k}": v for k, v in five_ranks.items()})
    top10 = {n: tops[n][:, :10] for n in scores}
    for h, lists in hybrid_lists.items():
        top10[h] = np.asarray([l[:10] for l in lists])
    top10["Hybrid + cross-encoder re-rank"] = np.asarray([l[:10] for l in reranked])
    np.savez("results/top10.npz", **top10)

    print(pd.DataFrame(full_rows).round(4).to_string())
    print(pd.DataFrame(five_rows).round(4).to_string())
    print(timing)


if __name__ == "__main__":
    main()
