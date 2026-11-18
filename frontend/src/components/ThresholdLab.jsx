import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { useClerkApi } from "../api.js";

function Stat({ label, value, sub, tone }) {
  return (
    <div className={"stat " + (tone || "")}>
      <div className="muted small">{label}</div>
      <div className="big">{value}</div>
      {sub && <div className="muted small">{sub}</div>}
    </div>
  );
}

export default function ThresholdLab() {
  const api = useClerkApi();
  const [multi, setMulti] = useState(true);
  const [guard, setGuard] = useState(true);
  const [sweep, setSweep] = useState(null);
  const [slider, setSlider] = useState(0.85);
  const [error, setError] = useState("");

  useEffect(() => {
    setSweep(null);
    api(`/eval/sweep?start=0.5&end=0.99&step=0.01&multi=${multi}&guard=${guard}`)
      .then((result) => { setSweep(result); setError(""); })
      .catch((e) => setError(e.message));
  }, [multi, guard]);

  const current = useMemo(() => {
    if (!sweep) return null;
    return sweep.rows.reduce((closest, row) => (
      Math.abs(row.threshold - slider) < Math.abs(closest.threshold - slider) ? row : closest
    ));
  }, [sweep, slider]);

  const table = useMemo(
    () => (sweep ? sweep.rows.filter((row) => (
      Math.round(row.threshold * 100) % 5 === 0 && row.threshold >= 0.5 && row.threshold <= 0.95
    )) : []),
    [sweep]
  );

  if (error) return <div className="card error">{error}</div>;
  if (!sweep || !current) return <div className="card muted">Preparing the test set. The first run takes a few seconds.</div>;

  const best = sweep.best;
  const summary = sweep.meta;

  return (
    <div className="stack">
      <div>
        <h2>Threshold Lab</h2>
        <p className="muted">
          Sweep {summary.n_tests} labelled questions: {summary.n_paraphrases} should hit and {summary.n_none} should miss.
          Move the slider to compare correct hits with wrong answers.
        </p>
      </div>

      <div className="card">
        <div className="row between wrap">
          <label className="check">
            <input type="checkbox" checked={multi} onChange={(e) => setMulti(e.target.checked)} />
            Multiple phrasings per FAQ ({summary.n_phrasings} stored)
          </label>
          <label className="check">
            <input type="checkbox" checked={guard} onChange={(e) => setGuard(e.target.checked)} />
            Negation guard
          </label>
        </div>
        <h3>Threshold: {current.threshold.toFixed(2)}</h3>
        <input type="range" min="0.5" max="0.99" step="0.01" value={slider}
          onChange={(e) => setSlider(parseFloat(e.target.value))} style={{ width: "100%" }} />

        <div className="grid4">
          <Stat label="Hit rate" value={current.hit_rate + "%"} sub="paraphrases answered correctly" />
          <Stat label="False hits" value={current.false_hits}
            sub="wrong answer served" tone={current.false_hits === 0 ? "good" : "bad"} />
          <Stat label="LLM calls saved" value={current.llm_calls_reduced + "%"} sub="of all test requests" />
          <Stat label="Avg latency" value={current.avg_latency_ms + " ms"} sub={`vs ${summary.llm_ms_assumed} ms with no cache`} />
        </div>
        <div className="muted small">
          English hit rate {current.hit_rate_en}% · Hinglish hit rate {current.hit_rate_hinglish}% ·
          guard stopped {current.guard_saves} wrong answers, wrongly blocked {current.guard_wrong_blocks} good ones
        </div>
      </div>

      <div className="card">
        <h3>Hit rate vs false hits</h3>
        <div style={{ height: 300 }}>
          <ResponsiveContainer>
            <LineChart data={sweep.rows}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
              <XAxis dataKey="threshold" stroke="var(--muted)" />
              <YAxis yAxisId="l" stroke="var(--green)" unit="%" domain={[0, 100]} />
              <YAxis yAxisId="r" orientation="right" stroke="var(--error)" allowDecimals={false} />
              <Tooltip contentStyle={{ background: "var(--panel)", border: "1px solid var(--line)" }} />
              <Legend />
              <ReferenceLine yAxisId="l" x={current.threshold} stroke="var(--text)" strokeDasharray="4 4" />
              <Line yAxisId="l" type="monotone" dataKey="hit_rate" name="Hit rate %" stroke="var(--green)" dot={false} strokeWidth={2} />
              <Line yAxisId="r" type="stepAfter" dataKey="false_hits" name="False hits" stroke="var(--error)" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <p>
          <b>Chosen threshold: {best.threshold.toFixed(2)}</b>: best hit rate ({best.hit_rate}%) with{" "}
          {best.false_hits} false hits, LLM calls down {best.llm_calls_reduced}%, average latency{" "}
          {summary.llm_ms_assumed} ms to {best.avg_latency_ms} ms.
        </p>
        <button onClick={() => setSlider(best.threshold)}>Jump slider to chosen threshold</button>
      </div>

      <div className="card">
        <h3>README table (0.50 to 0.95)</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Threshold</th><th>Hit rate %</th><th>False hits</th><th>From cache %</th><th>Avg latency</th><th>EN %</th><th>Hinglish %</th></tr>
            </thead>
            <tbody>
              {table.map((r) => (
                <tr key={r.threshold} className={r.threshold === best.threshold ? "best" : ""}>
                  <td>{r.threshold.toFixed(2)}</td><td>{r.hit_rate}</td><td>{r.false_hits}</td>
                  <td>{r.cache_rate}</td><td>{r.avg_latency_ms} ms</td><td>{r.hit_rate_en}</td><td>{r.hit_rate_hinglish}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="muted small">
          Latency = measured lookup time ({summary.lookup_ms} ms) + share of misses x {summary.llm_ms_assumed} ms assumed LLM time.
          Turn the checkboxes on and off to get the before/after numbers for your README.
        </p>
      </div>

      {sweep.guard_examples.length > 0 && (
        <div className="card">
          <h3>Caught by the negation guard</h3>
          <ul>
            {sweep.guard_examples.map((example, i) => (
              <li key={i}>
                <code>{example.question}</code> was {example.similarity} similar to <code>{example.matched}</code> and was
                sent to the LLM instead.
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
