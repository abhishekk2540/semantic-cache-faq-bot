import threading
import time

import faiss
import numpy as np

from .config import DEFAULT_THRESHOLD, DEFAULT_TTL_DAYS
from .embedder import DIM, embed, embed_many
from .guards import contains_pii, negation_mismatch


class SemanticCache:
    """One instance per tenant. Index position == position in self.entries."""

    def __init__(self, threshold=DEFAULT_THRESHOLD, ttl_days=DEFAULT_TTL_DAYS, use_guard=True, max_entries=1000):
        self.threshold = threshold
        self.ttl_days = ttl_days
        self.use_guard = use_guard
        self.max_entries = max_entries
        self.lock = threading.RLock()
        self._reset_index()

    def _reset_index(self):
        # IndexFlatIP = inner product. Vectors are normalised, so inner product == cosine.
        self.index = faiss.IndexFlatIP(DIM)
        self.entries = []

    def __len__(self):
        return len(self.entries)

    def lookup(self, question, threshold=None, use_guard=None):
        """Returns (entry or None, best_score, reason).

        reason is one of: hit, miss, empty, expired, negation_guard
        """
        t = self.threshold if threshold is None else threshold
        guard = self.use_guard if use_guard is None else use_guard

        with self.lock:
            if self.index.ntotal == 0:
                return None, 0.0, "empty"
            scores, ids = self.index.search(embed(question), 1)
            score = float(scores[0][0])
            entry = self.entries[int(ids[0][0])]

            if time.time() > entry["expires"]:
                return None, score, "expired"
            if score < t:
                return None, score, "miss"
            # similar enough, but is the meaning flipped? ("milega" vs "nahi milega")
            if guard and negation_mismatch(question, entry["question"]):
                return None, score, "negation_guard"
            return entry, score, "hit"

    def add(self, question, answer, faq_id=None, ttl_days=None, vec=None, created=None):
        """Returns (saved: bool, reason). Never stores user-specific data."""
        if contains_pii(question) or contains_pii(answer):
            return False, "not_cached_pii"
        ttl = self.ttl_days if ttl_days is None else ttl_days
        created = created or time.time()
        with self.lock:
            vector = embed(question) if vec is None else vec
            self.index.add(vector)
            self.entries.append(
                {
                    "question": question,
                    "answer": answer,
                    "faq_id": faq_id,
                    "created": created,
                    "expires": created + ttl * 86400,
                    "ttl_days": ttl,
                    "vec": vector,
                }
            )
            if len(self.entries) > self.max_entries:
                self.entries.pop(0)
                self.index = faiss.IndexFlatIP(DIM)
                self.index.add(np.asarray([entry["vec"][0] for entry in self.entries], dtype="float32"))
        return True, "saved"

    def bulk_load(self, rows):
        """rows: dicts with question, answer, faq_id, created, ttl_days. Embeds in one batch."""
        if not rows:
            return
        missing = [r for r in rows if r.get("vector") is None]
        vecs = iter(embed_many([r["question"] for r in missing])) if missing else iter(())
        for r in rows:
            v = r.get("vector")
            if v is None:
                v = next(vecs)
            self.add(
                r["question"], r["answer"], r.get("faq_id"),
                ttl_days=r.get("ttl_days"), vec=v.reshape(1, -1), created=r.get("created"),
            )

    def clear(self):
        with self.lock:
            self._reset_index()

    def purge_expired(self):
        """FAISS flat index can't delete cheaply, so rebuild it from live entries."""
        now = time.time()
        with self.lock:
            live = [e for e in self.entries if e["expires"] > now]
            removed = len(self.entries) - len(live)
            if removed:
                self._reset_index()
                vecs = embed_many([e["question"] for e in live]) if live else None
                for e, v in zip(live, vecs if live else []):
                    self.index.add(v.reshape(1, -1))
                    self.entries.append(e)
        return removed

    def snapshot(self, limit=200):
        now = time.time()
        out = []
        for e in self.entries[-limit:][::-1]:
            out.append(
                {
                    "question": e["question"],
                    "answer": e["answer"],
                    "faq_id": e["faq_id"],
                    "age_min": round((now - e["created"]) / 60, 1),
                    "expires_in_days": round((e["expires"] - now) / 86400, 2),
                }
            )
        return out
