"""Inverted index plus the two sparse rankers (BM25 and TF-IDF cosine)."""
import math
from collections import Counter, defaultdict

import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer

from preprocess import tokenize


class InvertedIndex:
    """term -> {doc_id: term frequency}, plus document lengths."""

    def __init__(self, docs_tokens):
        self.postings = defaultdict(dict)
        self.doc_len = np.zeros(len(docs_tokens), dtype=np.float32)
        for doc_id, tokens in enumerate(docs_tokens):
            self.doc_len[doc_id] = len(tokens)
            for term, tf in Counter(tokens).items():
                self.postings[term][doc_id] = tf
        self.n_docs = len(docs_tokens)
        self.avg_len = float(self.doc_len.mean())
        self.terms = sorted(self.postings)
        self.term_id = {t: i for i, t in enumerate(self.terms)}

    def df(self, term):
        return len(self.postings.get(term, {}))

    def idf(self, term):
        # BM25 idf with +1 inside the log so it never goes negative
        n = self.df(term)
        return math.log((self.n_docs - n + 0.5) / (n + 0.5) + 1.0)

    def stats(self):
        lengths = [len(p) for p in self.postings.values()]
        return {
            "documents": self.n_docs,
            "vocabulary": len(self.terms),
            "postings": int(sum(lengths)),
            "avg_doc_length": round(self.avg_len, 2),
            "avg_postings_length": round(float(np.mean(lengths)), 2),
        }


class BM25:
    def __init__(self, index, k1=1.2, b=0.75):
        self.index, self.k1, self.b = index, k1, b
        self._build_matrix()

    def _build_matrix(self):
        # term x doc matrix of BM25 weights, built straight from the postings
        # lists. Scoring a whole batch of queries is then one sparse product.
        ix = self.index
        rows, cols, vals = [], [], []
        for term, plist in ix.postings.items():
            idf = ix.idf(term)
            t = ix.term_id[term]
            for doc_id, tf in plist.items():
                norm = self.k1 * (1 - self.b + self.b * ix.doc_len[doc_id] / ix.avg_len)
                rows.append(t)
                cols.append(doc_id)
                vals.append(idf * tf * (self.k1 + 1) / (tf + norm))
        self.weights = sparse.csr_matrix(
            (vals, (rows, cols)), shape=(len(ix.terms), ix.n_docs), dtype=np.float32)

    def query_vector(self, tokens):
        counts = Counter(t for t in tokens if t in self.index.term_id)
        vec = np.zeros(len(self.index.terms), dtype=np.float32)
        for term, c in counts.items():
            vec[self.index.term_id[term]] = c
        return vec

    def score_batch(self, queries_tokens):
        q = sparse.csr_matrix(np.vstack([self.query_vector(t) for t in queries_tokens]))
        return (q @ self.weights).toarray()

    def score_one(self, tokens):
        """Plain term-at-a-time scoring that walks the postings lists.
        Used by the search app and to check score_batch gives the same numbers."""
        ix = self.index
        scores = defaultdict(float)
        for term, qtf in Counter(tokens).items():
            if term not in ix.postings:
                continue
            idf = ix.idf(term)
            for doc_id, tf in ix.postings[term].items():
                norm = self.k1 * (1 - self.b + self.b * ix.doc_len[doc_id] / ix.avg_len)
                scores[doc_id] += qtf * idf * tf * (self.k1 + 1) / (tf + norm)
        return scores


class TfidfRanker:
    """TF-IDF vectors (log tf, smoothed idf, L2 norm) compared with cosine."""

    def __init__(self, corpus, **tok_args):
        self.vectorizer = TfidfVectorizer(
            analyzer=lambda text: tokenize(text, **tok_args), sublinear_tf=True)
        self.doc_matrix = self.vectorizer.fit_transform(corpus)

    def score_batch(self, queries):
        q = self.vectorizer.transform(queries)
        return (q @ self.doc_matrix.T).toarray()
