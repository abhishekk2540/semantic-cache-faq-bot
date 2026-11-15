"""Threshold sweep over the labelled test set.

Embeds everything once, then every (threshold, guard, multi-phrasing) combination is just
array maths, so the UI slider can call this repeatedly and stay instant.
"""
import csv
import json
import time
from functools import lru_cache

import faiss
import numpy as np

from .config import DATA_DIR, MOCK_LLM_MS
from .embedder import embed, embed_many
from .guards import negation_mismatch


def load_faqs():
    return json.loads((DATA_DIR / "faqs.json").read_text(encoding="utf-8"))


def load_tests():
    return json.loads((DATA_DIR / "test_set.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _prepare():
    faqs, tests = load_faqs(), load_tests()

    phrasings = []  # (faq_id, text, position inside that FAQ)
    for faq in faqs:
        for pos, q in enumerate(faq["questions"]):
            phrasings.append((faq["id"], q, pos))

    P = embed_many([p[1] for p in phrasings])
    Q = embed_many([t["question"] for t in tests])

    # Measure real lookup latency per question: embed + FAISS search, one by one.
    index = faiss.IndexFlatIP(P.shape[1])
    index.add(P)
    lookup_ms = []
    for t in tests:
        s = time.perf_counter()
        index.search(embed(t["question"]), 1)
        lookup_ms.append((time.perf_counter() - s) * 1000)

    labels = np.array([t["label"] if t["label"] != "none" else -1 for t in tests])
    langs = np.array([t["lang"] for t in tests])

    configs = {}
    for multi in (True, False):
        keep = [i for i, p in enumerate(phrasings) if multi or p[2] == 0]
        sims = Q @ P[keep].T
        best = sims.argmax(axis=1)
        configs[multi] = {
            "score": sims.max(axis=1),
            "faq": np.array([phrasings[keep[b]][0] for b in best]),
            "matched": [phrasings[keep[b]][1] for b in best],
            "neg": np.array(
                [negation_mismatch(tests[i]["question"], phrasings[keep[b]][1]) for i, b in enumerate(best)]
            ),
        }

    return {
        "tests": tests,
        "labels": labels,
        "langs": langs,
        "lookup_ms": float(np.mean(lookup_ms)),
        "configs": configs,
        "n_faqs": len(faqs),
        "n_phrasings": len(phrasings),
    }


def _row(t, c, d, guard):
    labels, langs = d["labels"], d["langs"]
    would_hit = c["score"] >= t
    blocked = would_hit & c["neg"] & guard
    hit = would_hit & ~blocked
    correct = hit & (c["faq"] == labels)
    false = hit & ~correct

    para = labels != -1
    n_total = len(labels)
    cache_rate = hit.sum() / n_total
    avg_latency = d["lookup_ms"] + (1 - cache_rate) * MOCK_LLM_MS

    def lang_rate(lang):
        m = para & (langs == lang)
        return round(float(correct[m].sum() / m.sum() * 100), 1) if m.sum() else 0.0

    return {
        "threshold": round(float(t), 2),
        "hit_rate": round(float(correct.sum() / para.sum() * 100), 1),  # correct hits / paraphrases
        "false_hits": int(false.sum()),
        "cache_rate": round(float(cache_rate * 100), 1),  # share of ALL requests served from cache
        "llm_calls_reduced": round(float(cache_rate * 100), 1),
        "avg_latency_ms": round(float(avg_latency), 1),
        "hit_rate_en": lang_rate("en"),
        "hit_rate_hinglish": lang_rate("hinglish"),
        "guard_saves": int((blocked & (c["faq"] != labels)).sum()),  # false hits the guard stopped
        "guard_wrong_blocks": int((blocked & (c["faq"] == labels)).sum()),  # good hits it blocked
    }


def pick_best(rows, max_false=0):
    ok = [r for r in rows if r["false_hits"] <= max_false]
    if ok:
        return max(ok, key=lambda r: (r["hit_rate"], -r["threshold"]))
    return min(rows, key=lambda r: (r["false_hits"], -r["hit_rate"]))


def run_sweep(thresholds, multi=True, guard=True):
    d = _prepare()
    c = d["configs"][bool(multi)]
    rows = [_row(t, c, d, guard) for t in thresholds]
    return {
        "rows": rows,
        "best": pick_best(rows),
        "meta": {
            "n_tests": len(d["tests"]),
            "n_paraphrases": int((d["labels"] != -1).sum()),
            "n_none": int((d["labels"] == -1).sum()),
            "n_faqs": d["n_faqs"],
            "n_phrasings": d["n_phrasings"] if multi else d["n_faqs"],
            "lookup_ms": round(d["lookup_ms"], 1),
            "llm_ms_assumed": MOCK_LLM_MS,
        },
    }


def guard_examples(threshold, multi=True, limit=5):
    """Questions that would have been false hits at this threshold but the guard stopped."""
    d = _prepare()
    c = d["configs"][bool(multi)]
    out = []
    for i, t in enumerate(d["tests"]):
        if c["score"][i] >= threshold and c["neg"][i] and c["faq"][i] != d["labels"][i]:
            out.append(
                {"question": t["question"], "matched": c["matched"][i], "similarity": round(float(c["score"][i]), 3)}
            )
    return out[:limit]


def frange(start, stop, step):
    n = int(round((stop - start) / step))
    return [round(start + i * step, 4) for i in range(n + 1)]


def write_reports(out_dir):
    """Writes results/sweep.csv and results/sweep.md and returns the markdown text."""
    out_dir.mkdir(parents=True, exist_ok=True)
    # The brief says 0.75-0.95, but MiniLM often scores real paraphrases below 0.75
    # (especially Hinglish), so the sweep starts lower to show where hits actually begin.
    ths = frange(0.50, 0.95, 0.05)
    main = run_sweep(ths, multi=True, guard=True)
    single = run_sweep(ths, multi=False, guard=True)
    noguard = run_sweep(ths, multi=True, guard=False)

    cols = ["threshold", "hit_rate", "false_hits", "cache_rate", "avg_latency_ms",
            "hit_rate_en", "hit_rate_hinglish", "guard_saves", "guard_wrong_blocks"]
    with open(out_dir / "sweep.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["config"] + cols)
        for name, res in (("multi+guard", main), ("single+guard", single), ("multi_noguard", noguard)):
            for r in res["rows"]:
                w.writerow([name] + [r[c] for c in cols])

    m = main["meta"]
    lines = [
        "# Threshold sweep",
        "",
        f"{m['n_tests']} labelled questions ({m['n_paraphrases']} paraphrases, {m['n_none']} that must NOT hit), "
        f"{m['n_faqs']} FAQs, {main['meta']['n_phrasings']} stored phrasings.",
        f"Measured lookup (embed + search): {m['lookup_ms']} ms. LLM latency assumed: {m['llm_ms_assumed']} ms.",
        "",
        "## Main config: multiple phrasings per FAQ + negation guard",
        "",
        "| threshold | hit rate % | false hits | served from cache % | avg latency ms | EN hit % | Hinglish hit % |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in main["rows"]:
        lines.append(
            f"| {r['threshold']:.2f} | {r['hit_rate']} | {r['false_hits']} | {r['cache_rate']} | "
            f"{r['avg_latency_ms']} | {r['hit_rate_en']} | {r['hit_rate_hinglish']} |"
        )
    b = main["best"]
    lines += [
        "",
        f"**Chosen threshold: {b['threshold']:.2f}** (best hit rate with {b['false_hits']} false hits): "
        f"hit rate {b['hit_rate']}%, LLM calls down {b['llm_calls_reduced']}%, "
        f"avg latency {m['llm_ms_assumed']} ms -> {b['avg_latency_ms']} ms.",
        "",
        "## Ablation at each config's own best threshold",
        "",
        "| config | threshold | hit rate % | false hits | Hinglish hit % |",
        "|---|---|---|---|---|",
    ]
    for name, res in (("1 phrasing per FAQ", single), ("multi phrasing, guard OFF", noguard), ("multi phrasing + guard", main)):
        r = res["best"]
        lines.append(f"| {name} | {r['threshold']:.2f} | {r['hit_rate']} | {r['false_hits']} | {r['hit_rate_hinglish']} |")

    lines += ["", "## Negation guard: false hits it stopped", ""]
    gt = max(b["threshold"] - 0.1, 0.5)
    ex = guard_examples(gt, multi=True)
    if ex:
        for e in ex:
            lines.append(f"- `{e['question']}` was {e['similarity']} similar to `{e['matched']}` -> skipped cache")
    else:
        lines.append(f"- none at threshold {gt:.2f} on this test set")

    text = "\n".join(lines) + "\n"
    (out_dir / "sweep.md").write_text(text, encoding="utf-8")
    return text
