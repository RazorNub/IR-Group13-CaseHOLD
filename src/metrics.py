"""IR metrics. Every query in our setup has exactly one relevant holding,
so most metrics reduce to simple functions of the rank of that holding."""
import numpy as np


def rank_of_gold(scores, gold):
    """1-based rank of the gold document for each query (ties count against us)."""
    gold_scores = scores[np.arange(len(gold)), gold]
    return 1 + (scores > gold_scores[:, None]).sum(axis=1)


def ranks_from_lists(ranked_lists, gold):
    """Same as above but for top-k lists; gold missing from the list -> inf."""
    out = []
    for lst, g in zip(ranked_lists, gold):
        pos = np.where(np.asarray(lst) == g)[0]
        out.append(pos[0] + 1 if len(pos) else np.inf)
    return np.asarray(out, dtype=float)


def summarize(ranks, ks=(1, 5, 10, 100)):
    r = np.asarray(ranks, dtype=float)
    res = {}
    res["MRR"] = float(np.mean(np.where(np.isfinite(r), 1.0 / r, 0.0)))
    # with one relevant doc, AP of a query = 1/rank, so MAP equals MRR
    res["MAP"] = res["MRR"]
    for k in ks:
        res[f"P@{k}"] = float(np.mean((r <= k) / k))
        res[f"R@{k}"] = float(np.mean(r <= k))
    # nDCG@10 with binary gain: ideal DCG is 1, so nDCG = 1/log2(rank+1) inside top 10
    res["nDCG@10"] = float(np.mean(np.where(r <= 10, 1.0 / np.log2(r + 1), 0.0)))
    res["median_rank"] = float(np.median(r))
    return res


def pr_points(ranks, max_k=100):
    """Mean precision@k and recall@k for k = 1..max_k, for the PR graph."""
    r = np.asarray(ranks, dtype=float)
    ks = np.arange(1, max_k + 1)
    recall = np.array([np.mean(r <= k) for k in ks])
    precision = np.array([np.mean((r <= k) / k) for k in ks])
    return ks, precision, recall


def interpolated_pr(ranks, levels=np.linspace(0, 1, 11)):
    """Standard 11-point interpolated precision. With one relevant document per
    query the interpolated precision is 1/rank at every recall level, so each
    query's curve is flat; we report it anyway because the brief asks for it."""
    r = np.asarray(ranks, dtype=float)
    p = np.where(np.isfinite(r), 1.0 / r, 0.0)
    return levels, np.full(len(levels), p.mean())
