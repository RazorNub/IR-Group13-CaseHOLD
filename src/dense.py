"""Dense retrieval with sentence-transformers. Embeddings are cached to disk."""
import hashlib
import os

import numpy as np
import torch
from sentence_transformers import CrossEncoder, SentenceTransformer

CACHE_DIR = "data/emb_cache"


def device():
    return "mps" if torch.backends.mps.is_available() else "cpu"


def _cache_path(model_name, texts):
    h = hashlib.md5(("\n".join(texts)).encode()).hexdigest()[:12]
    return os.path.join(CACHE_DIR, f"{os.path.basename(model_name)}_{len(texts)}_{h}.npy")


def encode(model_name, texts, batch_size=64, model=None):
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = _cache_path(model_name, texts)
    if os.path.exists(path):
        return np.load(path)
    model = model or SentenceTransformer(model_name, device=device())
    emb = model.encode(texts, batch_size=batch_size, normalize_embeddings=True,
                       show_progress_bar=True, convert_to_numpy=True)
    np.save(path, emb.astype(np.float32))
    return emb


# BGE models are trained with this instruction in front of every query
QUERY_PREFIX = {"BAAI/bge-small-en-v1.5": "Represent this sentence for searching relevant passages: "}


def dense_scores(model_name, queries, corpus):
    model = SentenceTransformer(model_name, device=device())
    prefix = QUERY_PREFIX.get(model_name, "")
    q = encode(model_name, [prefix + x for x in queries], model=model)
    d = encode(model_name, corpus, model=model)
    return q @ d.T   # cosine, since the vectors are normalised


def cross_encoder_scores(model_name, pairs, batch_size=64):
    model = CrossEncoder(model_name, device=device())
    return np.asarray(model.predict(pairs, batch_size=batch_size, show_progress_bar=True))
