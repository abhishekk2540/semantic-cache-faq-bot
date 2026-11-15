"""Quick end-to-end check without starting a server.

    uv run python smoke_test.py

Uses a throw-away database. Set EMBEDDER=hash only if you have no model downloaded
(the numbers are then meaningless, it just proves the plumbing works).
"""
import os
import tempfile
from pathlib import Path

import app.config as config

config.DB_PATH = Path(tempfile.mkdtemp()) / "smoke.db"
import app.db as dbmod  # noqa: E402

dbmod.DB_PATH = config.DB_PATH

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

with TestClient(app) as client:
    r = client.post("/auth/register", json={"username": "demo", "password": "demo1234"})
    assert r.status_code == 200, r.text
    H = {"Authorization": "Bearer " + r.json()["token"]}

    assert client.post("/ask", json={"question": "hi"}).status_code == 401  # no token -> blocked

    print("seed:", client.post("/cache/seed", headers=H).json())

    for q in ["refund kab milega?", "How long does a refund take?", "Will I not get a refund?"]:
        a = client.post("/ask", json={"question": q}, headers=H).json()
        print(f"{'HIT ' if a['hit'] else 'MISS'} {a['reason']:<15} sim={a['similarity']:<6} {a['latency_ms']:>7} ms | {q}")

    pii = client.post("/ask", json={"question": "order 123456789 kahan hai"}, headers=H).json()
    print("PII question ->", pii["reason"], "| cached_now =", pii["cached_now"])

    # a second tenant must NOT see the first tenant's cache
    r2 = client.post("/auth/register", json={"username": "other", "password": "other1234"})
    H2 = {"Authorization": "Bearer " + r2.json()["token"]}
    a2 = client.post("/ask", json={"question": "refund kab milega?"}, headers=H2).json()
    print("other tenant, same question -> hit =", a2["hit"], "(must be False)")

    print("stats:", client.get("/stats", headers=H).json())
    print("negation demo:", client.post("/demo/negation", json={"a": "refund milega", "b": "refund nahi milega"}, headers=H).json())
    print("sweep best:", client.get("/eval/sweep?step=0.05&start=0.75&end=0.95", headers=H).json()["best"])
    print("OK")
