import { useEffect, useRef, useState } from "react";
import { useClerkApi } from "../api.js";

const DEMO = [
  "Do you have a store in Mumbai?",
  "Is there a shop in Mumbai I can visit?",
  "mumbai mein aapki dukaan hai kya?",
];

const REASONS = {
  hit: "served from cache",
  miss: "no similar question cached, called the LLM",
  empty: "cache was empty, called the LLM",
  expired: "cached answer expired (TTL), called the LLM",
  negation_guard: "looked similar but meaning is flipped (negation guard), called the LLM",
  not_cached_pii: "contains personal data, called the LLM and did NOT cache it",
};

export default function Chat() {
  const api = useClerkApi();
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState(null);
  const [threshold, setThreshold] = useState(0.85);
  const [guard, setGuard] = useState(true);
  const endRef = useRef(null);

  const loadInfo = async () => {
    try {
      const me = await api("/auth/me");
      setInfo(me);
      setThreshold(me.threshold);
      setGuard(me.use_guard);
    } catch (e) {
      setError(e.message);
    }
  };
  useEffect(() => { loadInfo(); }, []);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, busy]);

  const send = async (q) => {
    const question = (q ?? text).trim();
    if (!question || busy) return;
    setText("");
    setError("");
    setBusy(true);
    setMessages((m) => [...m, { role: "user", text: question }]);
    try {
      const r = await api("/ask", { method: "POST", body: { question } });
      setMessages((m) => [...m, { role: "bot", ...r }]);
      setInfo((i) => (i ? { ...i, cache_size: i.cache_size + (r.cached_now ? 1 : 0) } : i));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const runDemo = async () => {
    for (const q of DEMO) {
      await send(q);
    }
  };

  const saveSettings = async (t, g) => {
    try {
      await api("/settings", { method: "PUT", body: { threshold: t, use_guard: g } });
    } catch (e) {
      setError(e.message);
    }
  };

  const saveSettingsLater = useRef(null);
  const queueSettingsSave = (nextThreshold, nextGuard) => {
    clearTimeout(saveSettingsLater.current);
    saveSettingsLater.current = setTimeout(() => saveSettings(nextThreshold, nextGuard), 250);
  };

  const seed = async () => {
    try {
      await api("/cache/seed", { method: "POST" });
      await loadInfo();
    } catch (e) { setError(e.message); }
  };

  const clear = async () => {
    try {
      await api("/cache/clear", { method: "POST" });
      await loadInfo();
    } catch (e) { setError(e.message); }
  };

  return (
    <div className="chat-layout">
      <section className="card chat">
        <div className="messages">
          {messages.length === 0 && (
            <div className="empty">
              <p><b>Start here:</b> run the three-question example. The first request calls the LLM; later questions can use the cache.</p>
              <p className="muted">You can also load the FAQ examples and ask a support question.</p>
            </div>
          )}
          {messages.map((m, i) =>
            m.role === "user" ? (
              <div key={i} className="bubble user">{m.text}</div>
            ) : (
              <div key={i} className="bubble bot">
                <div className="meta">
                  <span className={m.hit ? "badge hit" : "badge miss"}>{m.hit ? "CACHE HIT" : "LLM CALL"}</span>
                  <span className="badge">{m.latency_ms} ms</span>
                  <span className="badge">similarity {m.similarity}</span>
                  {m.tokens > 0 && <span className="badge">{m.tokens} tokens</span>}
                </div>
                <div>{m.answer}</div>
                <div className="why">
                  {REASONS[m.reason] || m.reason}
                  {m.matched_question && <> · matched: <i>"{m.matched_question}"</i></>}
                </div>
              </div>
            )
          )}
          {busy && <div className="bubble bot muted">Waiting for the answer...</div>}
          <div ref={endRef} />
        </div>
        {error && <div className="error">{error}</div>}
        <form className="composer" onSubmit={(e) => { e.preventDefault(); send(); }}>
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Ask a support question"
            maxLength={500}
          />
          <button className="primary" disabled={busy || !text.trim()}>Send</button>
        </form>
      </section>

      <aside className="card side">
        <h3>Your private cache</h3>
        <div className="big">{info ? info.cache_size : "-"} <span className="muted">entries</span></div>
        <div className="muted small">LLM mode: {info?.llm_mode}</div>
        <div className="row">
          <button onClick={runDemo} disabled={busy}>Run example</button>
          <button onClick={seed} disabled={busy}>Load FAQ examples</button>
          <button className="ghost" onClick={clear} disabled={busy}>Clear cache</button>
        </div>

        <h3>Similarity threshold: {threshold.toFixed(2)}</h3>
        <input
          type="range" min="0.5" max="0.99" step="0.01" value={threshold}
          onChange={(e) => setThreshold(parseFloat(e.target.value))}
          onMouseUp={() => queueSettingsSave(threshold, guard)}
          onTouchEnd={() => queueSettingsSave(threshold, guard)}
          onKeyUp={() => queueSettingsSave(threshold, guard)}
        />
        <div className="muted small">
          Lower = more hits but more wrong answers. Higher = safer but more LLM calls.
          Find the sweet spot in the Threshold Lab tab.
        </div>

        <label className="check">
          <input
            type="checkbox" checked={guard}
            onChange={(e) => { setGuard(e.target.checked); saveSettings(threshold, e.target.checked); }}
          />
          Negation guard
        </label>
        <div className="muted small">Skips the cache if only one question has "not / nahi / mat".</div>

        <h3>Quick questions</h3>
        <div className="chips">
          {["refund kab milega?", "How do I track my order?", "order cancel kaise karu?", "Will I not get a refund?",
            "mera order 123456789 kahan hai"].map((q) => (
            <button key={q} className="chip" onClick={() => send(q)} disabled={busy}>{q}</button>
          ))}
        </div>
      </aside>
    </div>
  );
}
