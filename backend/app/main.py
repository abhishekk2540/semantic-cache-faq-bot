import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import db
from .auth import current_user
from .cache import SemanticCache
from .config import (
    COST_PER_CALL_INR, CORS_ORIGINS, DEFAULT_THRESHOLD, LLM_MODE, MOCK_LLM_MS,
)
from .embedder import embed_many, warm_model
from .evaluate import frange, guard_examples, load_faqs, run_sweep
from .guards import has_negation, negation_mismatch
from .llm import ask_llm


@asynccontextmanager
async def lifespan(app):
    db.init_db()
    warm_model()
    yield


app = FastAPI(title="Semantic Cache FAQ Bot", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# tenant (user id) -> that tenant's own cache. Nobody can ever see another tenant's answers.
CACHES = {}


def get_cache(user_id):
    cache = CACHES.get(user_id)
    if cache is None:
        row = db.get_user(user_id)
        if row is None:
            cache = SemanticCache()
        else:
            cache = SemanticCache(threshold=row["threshold"], use_guard=bool(row["use_guard"]))
        cache.bulk_load(db.load_entries(user_id))  # restore after a server restart
        cache.purge_expired()
        CACHES[user_id] = cache
    return cache


# ---------------------------------------------------------------- auth (Clerk)
# No /auth/register or /auth/login endpoints — Clerk handles all of that.
# The frontend sends the Clerk session token as a Bearer header.


@app.get("/auth/me")
def me(user=Depends(current_user)):
    row = db.ensure_user(user["id"], user["username"])
    return {
        "username": row["username"],
        "threshold": row["threshold"],
        "use_guard": bool(row["use_guard"]),
        "cache_size": len(get_cache(user["id"])),
        "llm_mode": LLM_MODE,
    }


# ---------------------------------------------------------------- ask
class AskBody(BaseModel):
    question: str = Field(min_length=1, max_length=500)


@app.post("/ask")
def ask(body: AskBody, user=Depends(current_user)):
    db.ensure_user(user["id"], user["username"])
    question = body.question.strip()
    if not question:
        raise HTTPException(400, "Empty question")
    cache = get_cache(user["id"])

    start = time.perf_counter()
    entry, score, reason = cache.lookup(question)

    cached_now = False
    if entry:
        hit, answer, tokens, matched = True, entry["answer"], 0, entry["question"]
    else:
        hit, matched = False, None
        try:
            answer, tokens = ask_llm(question)
        except Exception as exc:  # network error, missing key, etc.
            raise HTTPException(502, f"LLM call failed: {exc}")
        saved, why = cache.add(question, answer)
        if saved:
            cached_now = True
            db.save_entry(
                user["id"], question, answer, None, time.time(), cache.ttl_days,
                cache.entries[-1]["vec"],
            )
        else:
            reason = why  # not_cached_pii

    latency_ms = round((time.perf_counter() - start) * 1000, 1)
    similarity = round(score, 3)
    db.add_log(user["id"], question, hit, reason, similarity, latency_ms, tokens)
    return {
        "answer": answer,
        "hit": hit,
        "reason": reason,
        "similarity": similarity,
        "latency_ms": latency_ms,
        "tokens": tokens,
        "matched_question": matched,
        "cached_now": cached_now,
        "threshold": cache.threshold,
    }


# ---------------------------------------------------------------- settings + cache control
class SettingsBody(BaseModel):
    threshold: float = Field(ge=0.3, le=0.99)
    use_guard: bool = True


@app.put("/settings")
def update_settings(body: SettingsBody, user=Depends(current_user)):
    db.ensure_user(user["id"], user["username"])
    cache = get_cache(user["id"])
    cache.threshold = body.threshold
    cache.use_guard = body.use_guard
    db.update_settings(user["id"], body.threshold, body.use_guard)
    return {"threshold": cache.threshold, "use_guard": cache.use_guard}


@app.post("/cache/seed")
def seed(user=Depends(current_user)):
    """Preload all FAQ phrasings into this tenant's cache."""
    db.ensure_user(user["id"], user["username"])
    cache = get_cache(user["id"])
    have = {e["question"] for e in cache.entries}
    now = time.time()
    rows = []
    for faq in load_faqs():
        for q in faq["questions"]:
            if q not in have:
                rows.append(
                    {"question": q, "answer": faq["answer"], "faq_id": faq["id"],
                     "created": now, "ttl_days": faq.get("ttl_days", cache.ttl_days)}
                )
    cache.bulk_load(rows)
    for r in rows:
        entry = next(item for item in cache.entries if item["question"] == r["question"])
        db.save_entry(
            user["id"], r["question"], r["answer"], r["faq_id"], r["created"], r["ttl_days"],
            entry["vec"],
        )
    return {"added": len(rows), "cache_size": len(cache)}


@app.post("/cache/clear")
def clear(user=Depends(current_user)):
    db.ensure_user(user["id"], user["username"])
    get_cache(user["id"]).clear()
    db.clear_entries(user["id"])
    return {"cache_size": 0}


@app.post("/stats/reset")
def reset_stats(user=Depends(current_user)):
    db.ensure_user(user["id"], user["username"])
    db.clear_logs(user["id"])
    return {"ok": True}


@app.get("/cache/entries")
def entries(user=Depends(current_user)):
    db.ensure_user(user["id"], user["username"])
    return get_cache(user["id"]).snapshot()


# ---------------------------------------------------------------- stats
def _pct(sorted_vals, p):
    if not sorted_vals:
        return None
    k = min(len(sorted_vals) - 1, max(0, int(round(p / 100 * (len(sorted_vals) - 1)))))
    return round(sorted_vals[k], 1)


@app.get("/stats")
def stats(user=Depends(current_user)):
    db.ensure_user(user["id"], user["username"])
    logs = db.get_logs(user["id"])
    total = len(logs)
    hits = [l for l in logs if l["hit"]]
    misses = [l for l in logs if not l["hit"]]
    all_ms = sorted(l["latency_ms"] for l in logs)
    avg = lambda xs: round(sum(xs) / len(xs), 1) if xs else None

    avg_miss_ms = avg([l["latency_ms"] for l in misses])
    avg_all_ms = avg(all_ms)
    llm_calls = len(misses)
    return {
        "requests": total,
        "hits": len(hits),
        "hit_rate": round(len(hits) / total * 100, 1) if total else 0,
        "llm_calls": llm_calls,
        "llm_calls_without_cache": total,
        "llm_calls_reduced_pct": round(len(hits) / total * 100, 1) if total else 0,
        "tokens_used": sum(l["tokens"] for l in logs),
        "avg_latency_hit_ms": avg([l["latency_ms"] for l in hits]),
        "avg_latency_miss_ms": avg_miss_ms,
        "avg_latency_ms": avg_all_ms,
        "p50_ms": _pct(all_ms, 50),
        "p95_ms": _pct(all_ms, 95),
        "cost_with_cache_inr": round(llm_calls * COST_PER_CALL_INR, 2),
        "cost_without_cache_inr": round(total * COST_PER_CALL_INR, 2),
        "cost_saved_inr": round(len(hits) * COST_PER_CALL_INR, 2),
        "cost_per_call_inr_assumed": COST_PER_CALL_INR,
        "reasons": {r: sum(1 for l in logs if l["reason"] == r) for r in {l["reason"] for l in logs}},
    }


@app.get("/logs")
def logs(limit: int = 50, user=Depends(current_user)):
    db.ensure_user(user["id"], user["username"])
    return db.get_logs(user["id"], limit=min(max(limit, 1), 500))


# ---------------------------------------------------------------- evaluation (the Threshold Lab)
@app.get("/eval/sweep")
def eval_sweep(
    start: float = 0.5, end: float = 0.99, step: float = 0.01,
    multi: bool = True, guard: bool = True, user=Depends(current_user),
):
    if step < 0.005 or end < start:
        raise HTTPException(400, "Bad range")
    result = run_sweep(frange(start, end, step), multi=multi, guard=guard)
    result["guard_examples"] = guard_examples(result["best"]["threshold"] - 0.1, multi=multi)
    return result


@app.get("/eval/guard-examples")
def eval_guard_examples(threshold: float = 0.75, multi: bool = True, user=Depends(current_user)):
    return guard_examples(threshold, multi=multi, limit=10)


# ---------------------------------------------------------------- negation demo
class PairBody(BaseModel):
    a: str = Field(min_length=1, max_length=300)
    b: str = Field(min_length=1, max_length=300)


@app.post("/demo/negation")
def demo_negation(body: PairBody, user=Depends(current_user)):
    db.ensure_user(user["id"], user["username"])
    va, vb = embed_many([body.a, body.b])
    score = round(float(va @ vb), 3)
    cache = get_cache(user["id"])
    mismatch = negation_mismatch(body.a, body.b)
    return {
        "similarity": score,
        "a_has_negation": has_negation(body.a),
        "b_has_negation": has_negation(body.b),
        "threshold": cache.threshold,
        "would_hit_without_guard": score >= cache.threshold,
        "blocked_by_guard": mismatch and score >= cache.threshold,
        "would_hit_with_guard": score >= cache.threshold and not mismatch,
    }


@app.get("/health")
def health():
    return {"ok": True, "llm_mode": LLM_MODE, "mock_llm_ms": MOCK_LLM_MS, "default_threshold": DEFAULT_THRESHOLD}
