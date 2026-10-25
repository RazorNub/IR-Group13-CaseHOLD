"""Loads CaseHOLD and turns it into a retrieval task.

Each CaseHOLD example has a citing context (with a <HOLDING> placeholder),
5 candidate holdings and the index of the correct one. We use:
  query    = the citing context
  corpus   = every unique holding text in the split (correct ones + distractors)
  relevant = the correct holding for that query (exactly one per query)
"""
import os
from dataclasses import dataclass

from datasets import load_dataset

DATASET = "coastalcph/lex_glue"
CONFIG = "case_hold"


@dataclass
class RetrievalSplit:
    name: str
    queries: list          # query text, one per example
    corpus: list           # unique holding texts
    gold: list             # corpus index of the correct holding, per query
    candidates: list       # corpus indices of the 5 choices, per query
    labels: list           # position (0-4) of the correct choice, per query


def load_split(split="test", limit=None):
    ds = load_dataset(DATASET, CONFIG, split=split)
    if limit:
        ds = ds.select(range(limit))

    corpus, doc_id = [], {}
    queries, gold, candidates, labels = [], [], [], []
    for ex in ds:
        ids = []
        for text in ex["endings"]:
            if text not in doc_id:
                doc_id[text] = len(corpus)
                corpus.append(text)
            ids.append(doc_id[text])
        label = int(ex["label"])
        queries.append(ex["context"])
        candidates.append(ids)
        gold.append(ids[label])
        labels.append(label)
    return RetrievalSplit(split, queries, corpus, gold, candidates, labels)


def query_window(context, n_words=None):
    """Removes the <HOLDING> marker. If n_words is set, keeps only the last
    n_words before the marker (the sentence that actually cites the case)."""
    before = context.split("<HOLDING>")[0]
    if n_words:
        before = " ".join(before.split()[-n_words:])
    return before.replace("(", " ").replace(")", " ").strip()


if __name__ == "__main__":
    os.environ.setdefault("HF_HOME", "data/hf_cache")
    s = load_split("test")
    print(len(s.queries), "queries,", len(s.corpus), "unique holdings")
