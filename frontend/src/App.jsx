import { lazy, Suspense, useState } from "react";
import { clearSession, getToken } from "./api.js";
import Login from "./components/Login.jsx";
import Chat from "./components/Chat.jsx";
const Dashboard = lazy(() => import("./components/Dashboard.jsx"));
const ThresholdLab = lazy(() => import("./components/ThresholdLab.jsx"));
const GuardDemo = lazy(() => import("./components/GuardDemo.jsx"));

const TABS = [
  ["chat", "Chat"],
  ["dashboard", "Dashboard"],
  ["lab", "Threshold Lab"],
  ["guard", "Negation Guard"],
];

export default function App() {
  const [authed, setAuthed] = useState(!!getToken());
  const [tab, setTab] = useState("chat");

  if (!authed) return <Login onDone={() => setAuthed(true)} />;

  const logout = () => {
    clearSession();
    setAuthed(false);
  };

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          Semantic Cache
        </div>
        <nav>
          {TABS.map(([id, label]) => (
            <button key={id} className={tab === id ? "tab active" : "tab"} onClick={() => setTab(id)}>
              {label}
            </button>
          ))}
        </nav>
        <div className="who">
          {localStorage.getItem("username")}
          <button className="ghost" onClick={logout}>Log out</button>
        </div>
      </header>
      <main>
        <Suspense fallback={<div className="card muted">Loading this view...</div>}>
          {tab === "chat" && <Chat />}
          {tab === "dashboard" && <Dashboard />}
          {tab === "lab" && <ThresholdLab />}
          {tab === "guard" && <GuardDemo />}
        </Suspense>
      </main>
    </div>
  );
}
