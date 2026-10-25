"""Looks at where the models fail. Writes results/error_analysis.json and
results/error_examples.md (a few hand-readable examples)."""
import json
import os
import sys

import numpy as np

os.environ.setdefault("HF_HOME", "data/hf_cache")
sys.path.insert(0, os.path.dirname(__file__))

from data import load_split, query_window
from preprocess import tokenize

HYBRID = "Hybrid RRF (TF-IDF+BM25+Dense)"


def jaccard(a, b):
    a, b = set(tokenize(a)), set(tokenize(b))
    return len(a & b) / max(1, len(a | b))


def main():
    test = load_split("test")
    ranks = dict(np.load("results/ranks.npz"))
    top10 = dict(np.load("results/top10.npz"))
    gold = np.asarray(test.gold)
    out = {}

    bm, de, hy = ranks["full|BM25"], ranks["full|Dense"], ranks[f"full|{HYBRID}"]
    out["bm25_top1_dense_not"] = int(np.sum((bm == 1) & (de > 1)))
    out["dense_top1_bm25_not"] = int(np.sum((de == 1) & (bm > 1)))
    out["both_top1"] = int(np.sum((bm == 1) & (de == 1)))
    out["neither_top10"] = int(np.sum((bm > 10) & (de > 10)))
    out["hybrid_top1"] = int(np.sum(hy == 1))

    # when the hybrid misses rank 1, what did it put first?
    miss = np.where(hy > 1)[0]
    first = top10[HYBRID][miss, 0]
    own_distractor = [first[j] in test.candidates[i] for j, i in enumerate(miss)]
    out["hybrid_misses"] = int(len(miss))
    out["miss_top1_is_own_distractor"] = round(float(np.mean(own_distractor)), 4)
    out["miss_top1_vs_gold_jaccard"] = round(float(np.mean(
        [jaccard(test.corpus[first[j]], test.corpus[gold[i]]) for j, i in enumerate(miss)])), 4)
    hits = np.where(hy == 1)[0]
    out["note"] = ("own_distractor = the wrong top result is one of the 4 CaseHOLD distractors "
                   "chosen for that same query, i.e. a holding on the same legal issue")

    # MRR by length of the gold holding
    glen = np.array([len(test.corpus[g].split()) for g in gold])
    by_len = {}
    for lo, hi in [(0, 15), (16, 25), (26, 40), (41, 1000)]:
        m = (glen >= lo) & (glen <= hi)
        by_len[f"{lo}-{hi} words"] = {
            "queries": int(m.sum()),
            **{name: round(float(np.mean(1 / ranks[f"full|{name}"][m])), 4)
               for name in ["BM25", "Dense", HYBRID]}}
    out["mrr_by_gold_length"] = by_len
    json.dump(out, open("results/error_analysis.json", "w"), indent=2)
    print(json.dumps(out, indent=2))

    # a few concrete examples, picked by rule (no cherry-picking by hand)
    rng = np.random.default_rng(13)

    def pick(mask, n=2):
        idx = np.where(mask)[0]
        return list(rng.choice(idx, size=min(n, len(idx)), replace=False)) if len(idx) else []

    cases = [("BM25 finds it, dense model does not", pick((bm == 1) & (de > 5))),
             ("Dense model finds it, BM25 does not", pick((de == 1) & (bm > 5))),
             ("Hybrid fixes both", pick((hy == 1) & (bm > 1) & (de > 1))),
             ("Everything fails", pick((hy > 10) & (bm > 10) & (de > 10)))]
    lines = ["# Error analysis examples (test split, chosen with a fixed random seed)\n"]
    for title, idxs in cases:
        lines.append(f"## {title}\n")
        for i in idxs:
            q = query_window(test.queries[i], 60)
            lines.append(f"**Query {i}** (ranks: BM25 {int(bm[i])}, Dense {int(de[i])}, Hybrid {hy[i]:.0f})\n")
            lines.append(f"> ...{q}\n")
            lines.append(f"- Correct holding: {test.corpus[gold[i]]}")
            lines.append(f"- BM25 top 1: {test.corpus[top10['BM25'][i, 0]]}")
            lines.append(f"- Dense top 1: {test.corpus[top10['Dense'][i, 0]]}\n")
    open("results/error_examples.md", "w").write("\n".join(lines))


if __name__ == "__main__":
    main()
