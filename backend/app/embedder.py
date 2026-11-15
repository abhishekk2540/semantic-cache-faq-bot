import os
import zlib

import numpy as np

MODEL_NAME = os.getenv("EMBED_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
# "model" = real sentence-transformers model (use this for real numbers)
# "hash"  = tiny offline stand-in, ONLY for testing the plumbing without a model download
BACKEND = os.getenv("EMBEDDER", "model")
DIM = 384

_model = None


def load_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(MODEL_NAME)
    return _model


def warm_model():
    if BACKEND == "model":
        load_model().encode(["warm up"], normalize_embeddings=True, show_progress_bar=False)


def _hash_embed(texts):
    out = np.zeros((len(texts), DIM), dtype="float32")
    for i, text in enumerate(texts):
        t = " " + text.lower() + " "
        grams = [t[j : j + 3] for j in range(len(t) - 2)] + t.split()
        for g in grams:
            out[i, zlib.crc32(g.encode()) % DIM] += 1.0
        n = np.linalg.norm(out[i])
        if n > 0:
            out[i] /= n
    return out


def embed_many(texts):
    """List of strings -> (n, 384) float32 array, each row has length 1."""
    if BACKEND == "hash":
        return _hash_embed(texts)
    vecs = load_model().encode(
        texts, normalize_embeddings=True, batch_size=32, show_progress_bar=False
    )
    return np.asarray(vecs, dtype="float32")


def embed(text):
    """One string -> (1, 384) float32 array."""
    return embed_many([text])
