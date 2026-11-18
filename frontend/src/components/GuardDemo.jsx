import { useState } from "react";
import { useClerkApi } from "../api.js";

const PRESETS = [
  ["refund milega", "refund nahi milega"],
  ["Will I get a refund?", "Will I not get a refund?"],
  ["order cancel ho sakta hai", "order cancel nahi ho sakta"],
  ["refund kab milega?", "paisa wapas kab aayega?"],
];

export default function GuardDemo() {
  const api = useClerkApi();
  const [a, setA] = useState(PRESETS[0][0]);
  const [b, setB] = useState(PRESETS[0][1]);
  const [comparison, setComparison] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const run = async (x = a, y = b) => {
    setBusy(true);
    setError("");
    try {
      setComparison(await api("/demo/negation", { method: "POST", body: { a: x, b: y } }));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const pick = (x, y) => {
    setA(x);
    setB(y);
    run(x, y);
  };

  return (
    <div className="stack">
      <div>
        <h2>Negation Guard</h2>
        <p className="muted">
          Embedding models score "refund milega" and "refund nahi milega" as very similar even though they mean
          the opposite. The guard skips the cache when only one of the two has a negation word.
        </p>
      </div>
      <div className="card">
        <label>Cached question</label>
        <input value={a} onChange={(e) => setA(e.target.value)} />
        <label>New question</label>
        <input value={b} onChange={(e) => setB(e.target.value)} />
        <div className="row">
          <button className="primary" onClick={() => run()} disabled={busy}>Compare</button>
          {PRESETS.map(([x, y]) => (
            <button key={x} className="chip" onClick={() => pick(x, y)}>{x} / {y}</button>
          ))}
        </div>
        {error && <div className="error">{error}</div>}
      </div>

      {comparison && (
        <div className="card">
          <div className="grid4">
            <div className="stat"><div className="muted small">Similarity</div><div className="big">{comparison.similarity}</div>
              <div className="muted small">threshold {comparison.threshold}</div></div>
            <div className="stat"><div className="muted small">Cached has negation</div><div className="big">{comparison.a_has_negation ? "yes" : "no"}</div></div>
            <div className="stat"><div className="muted small">New has negation</div><div className="big">{comparison.b_has_negation ? "yes" : "no"}</div></div>
            <div className={"stat " + (comparison.blocked_by_guard ? "good" : "")}>
              <div className="muted small">Verdict</div>
              <div className="big" style={{ fontSize: 18 }}>
                {comparison.blocked_by_guard
                  ? "Guard blocked a wrong hit"
                  : comparison.would_hit_with_guard
                  ? "Cache hit (safe)"
                  : "Miss (not similar enough)"}
              </div>
            </div>
          </div>
          <p className="muted small">
            Without the guard this pair would {comparison.would_hit_without_guard ? "" : "not "}be a hit at the current threshold.
            Change the threshold in the Chat tab to see the guard matter.
          </p>
        </div>
      )}
    </div>
  );
}
