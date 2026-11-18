import { lazy, Suspense, useState } from "react";
import { Show, SignInButton, UserButton, useUser } from "@clerk/react";
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

function AuthenticatedApp() {
  const { user } = useUser();
  const [tab, setTab] = useState("chat");

  const displayName =
    user?.username ||
    user?.firstName ||
    user?.primaryEmailAddress?.emailAddress ||
    user?.emailAddresses?.[0]?.emailAddress ||
    "User";

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">Semantic Cache</div>
        <nav>
          {TABS.map(([id, label]) => (
            <button
              key={id}
              className={tab === id ? "tab active" : "tab"}
              onClick={() => setTab(id)}
            >
              {label}
            </button>
          ))}
        </nav>
        <div className="who">
          <span>{displayName}</span>
          <UserButton afterSignOutUrl="/" />
        </div>
      </header>
      <main>
        <Suspense
          fallback={<div className="card muted">Loading this view...</div>}
        >
          {tab === "chat" && <Chat />}
          {tab === "dashboard" && <Dashboard />}
          {tab === "lab" && <ThresholdLab />}
          {tab === "guard" && <GuardDemo />}
        </Suspense>
      </main>
    </div>
  );
}

function LandingPage() {
  return (
    <div className="login-wrap">
      <div className="card login">
        <h1>Semantic Cache</h1>
        <p className="muted">
          This FAQ bot reuses answers when a new question has the same meaning.
          Your account has its own cache.
        </p>
        <SignInButton mode="modal">
          <button className="primary" style={{ width: "100%", marginTop: 16 }}>
            Sign in to get started
          </button>
        </SignInButton>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <>
      <Show when="signed-in">
        <AuthenticatedApp />
      </Show>
      <Show when="signed-out">
        <LandingPage />
      </Show>
    </>
  );
}
