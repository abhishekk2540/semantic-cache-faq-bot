import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api.js";

const fmt = (v, unit = "") => (v === null || v === undefined ? "-" : v + unit);

function Stat({ label, value, sub }) {
  return (
    <div className="stat">
      <div className="muted small">{label}</div>
      <div className="big">{value}</div>
      {sub && <div className="muted small">{sub}</div>}
    </div>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [logs, setLogs] = useState([]);
  const [entries, setEntries] = useState([]);
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const [s, l, e] = await Promise.all([api("/stats"), api("/logs?limit=40"), api("/cache/entries")]);
      setStats(s);
      setLogs(l.slice().reverse().map((x, i) => ({ ...x, n: i + 1, ms: Math.max(x.latency_ms, 0.1) })));
      setEntries(e);
      setError("");
    } catch (err) {
      setError(err.message);
    }
  };
  useEffect(() => { load(); }, []);

  const resetStats = async () => {
    await api("/stats/reset", { method: "POST" });
    load();
  };

  if (error) return <div className="card error">{error}</div>;
  if (!stats) return <div className="card muted">Loading...</div>;

  return (
    <div className="stack">
      <div className="row between">
        <h2>Your cache performance</h2>
        <div className="row">
          <button onClick={load}>Refresh</button>
          <button className="ghost" onClick={resetStats}>Reset stats</button>
        </div>
      </div>

      {stats.requests === 0 ? (
        <div className="card muted">No requests yet. Ask a few questions in the Chat tab, then come back.</div>
      ) : (
        <>
          <div className="grid4">
            <Stat label="Requests" value={stats.requests} />
            <Stat label="Cache hit rate" value={stats.hit_rate + "%"} sub={`${stats.hits} served from cache`} />
            <Stat label="LLM calls" value={`${stats.llm_calls} / ${stats.llm_calls_without_cache}`}
              sub={`${stats.llm_calls_reduced_pct}% fewer calls`} />
            <Stat label="Tokens used" value={stats.tokens_used} />
            <Stat label="Avg latency (with cache)" value={fmt(stats.avg_latency_ms, " ms")}
              sub={`without cache: ${fmt(stats.avg_latency_miss_ms, " ms")}`} />
            <Stat label="p50 / p95 latency" value={`${fmt(stats.p50_ms)} / ${fmt(stats.p95_ms)} ms`} />
            <Stat label="Avg hit latency" value={fmt(stats.avg_latency_hit_ms, " ms")} />
            <Stat label="Estimated saving" value={"₹" + stats.cost_saved_inr}
              sub={`₹${stats.cost_with_cache_inr} vs ₹${stats.cost_without_cache_inr} (assumed ₹${stats.cost_per_call_inr_assumed}/call)`} />
          </div>

          <div className="card">
            <h3>Latency of the last {logs.length} requests (log scale)</h3>
            <div className="legend">
              <span><i className="sw hit" /> cache hit</span>
              <span><i className="sw miss" /> LLM call</span>
            </div>
            <div style={{ height: 260 }}>
              <ResponsiveContainer>
                <BarChart data={logs}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
                  <XAxis dataKey="n" stroke="var(--muted)" />
                  <YAxis scale="log" domain={[0.1, "auto"]} allowDataOverflow stroke="var(--muted)" unit=" ms" width={70} />
                  <Tooltip
                    contentStyle={{ background: "var(--panel)", border: "1px solid var(--line)" }}
                    formatter={(v) => [v + " ms", "latency"]}
                    labelFormatter={(n) => logs[n - 1]?.question}
                  />
                  <Bar dataKey="ms" radius={[3, 3, 0, 0]}>
                    {logs.map((l) => (
                      <Cell key={l.id} fill={l.hit ? "var(--green)" : "var(--orange)"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="card">
            <h3>Why requests missed</h3>
            <div className="chips">
              {Object.entries(stats.reasons).map(([r, n]) => (
                <span key={r} className="badge">{r}: {n}</span>
              ))}
            </div>
          </div>
        </>
      )}

      <div className="card">
        <h3>Cache contents ({entries.length}, newest first)</h3>
        {entries.length === 0 ? (
          <div className="muted">Empty.</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>Question</th><th>Answer</th><th>FAQ</th><th>Expires in</th></tr>
              </thead>
              <tbody>
                {entries.slice(0, 60).map((e, i) => (
                  <tr key={i}>
                    <td>{e.question}</td>
                    <td className="clip">{e.answer}</td>
                    <td>{e.faq_id ?? "LLM"}</td>
                    <td>{e.expires_in_days} d</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
