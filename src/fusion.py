"""Reciprocal Rank Fusion (Cormack et al., 2009)."""
from collections import defaultdict

import numpy as np


def top_k(scores, k):
    """Indices of the k highest scores in each row, best first."""
    k = min(k, scores.shape[1])
    part = np.argpartition(-scores, k - 1, axis=1)[:, :k]
    order = np.argsort(-np.take_along_axis(scores, part, axis=1), axis=1)
    return np.take_along_axis(part, order, axis=1)


def rrf(ranked_lists_per_model, k=60, depth=None):
    """ranked_lists_per_model: list of rankings (doc ids, best first), one per model,
    all for the same query. Returns doc ids sorted by RRF score."""
    score = defaultdict(float)
    for ranking in ranked_lists_per_model:
        for r, doc in enumerate(ranking[:depth], start=1):
            score[doc] += 1.0 / (k + r)
    return sorted(score, key=score.get, reverse=True)


def rrf_batch(model_topk, k=60):
    """model_topk: list of (n_queries x depth) arrays, one per model."""
    n = model_topk[0].shape[0]
    return [rrf([m[i] for m in model_topk], k=k) for i in range(n)]
