import { Gauge, History } from "lucide-react";
import { useState } from "react";

import { LivePage } from "./pages/LivePage";
import { SessionsPage } from "./pages/SessionsPage";

type View = "live" | "sessions";

export function App() {
  const [view, setView] = useState<View>("live");

  return (
    <div className="app-shell">
      <nav className="nav">
        <div className="brand">F1 25 Telemetry</div>
        <button className={view === "live" ? "nav-button active" : "nav-button"} onClick={() => setView("live")}>
          <Gauge size={18} />
          Live
        </button>
        <button
          className={view === "sessions" ? "nav-button active" : "nav-button"}
          onClick={() => setView("sessions")}
        >
          <History size={18} />
          Sessions
        </button>
      </nav>
      {view === "live" ? <LivePage /> : <SessionsPage />}
    </div>
  );
}
