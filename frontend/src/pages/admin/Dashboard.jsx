import { useEffect, useState } from "react";
import { api, postJSON } from "../../api.js";
import MatchesPane from "./MatchesPane.jsx";
import CasesPane from "./CasesPane.jsx";
import SightingsPane from "./SightingsPane.jsx";
import AlertsPane from "./AlertsPane.jsx";

const TABS = [["matches", "Match review"], ["cases", "Cases"], ["sightings", "Sightings"], ["alerts", "Alerts"]];

export default function Dashboard({ user, onLogout }) {
  const [tab, setTab] = useState("matches");
  const [overview, setOverview] = useState(null);
  const [tick, setTick] = useState(0);              // bump to refresh the numbers
  const refresh = () => setTick((t) => t + 1);

  useEffect(() => {
    api("/admin/overview").then(setOverview).catch((e) => { if (e.status === 401) onLogout(); });
  }, [tick]);

  async function logout() { await postJSON("/logout"); onLogout(); }

  const total = overview ? Object.values(overview.by_status).reduce((a, b) => a + b, 0) : 0;

  return (
    <div className="wrap">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
        <h1>Dashboard</h1>
        <div>Signed in as <strong>{user}</strong> <button className="btn ghost small" onClick={logout}>Log out</button></div>
      </div>

      {overview && overview.pending_matches > 0 && (
        <div className="notice" style={{ marginBottom: 18, borderLeftColor: "var(--accent)", background: "rgba(232,116,59,.12)", display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <div>
            <strong>Match alert:</strong> {overview.pending_matches} probable face {overview.pending_matches === 1 ? "match" : "matches"} detected and awaiting admin verification.
          </div>
          {tab !== "matches" && (
            <button className="btn accent small" onClick={() => setTab("matches")}>Review matches</button>
          )}
        </div>
      )}

      {overview && (
        <div className="grid" style={{ marginBottom: 22 }}>
          <div className="stat"><b>{overview.pending_matches}</b><span>Matches awaiting review</span></div>
          <div className="stat"><b>{total}</b><span>Total cases</span></div>
          <div className="stat"><b>{overview.by_status["Active"]}</b><span>Active cases</span></div>
          <div className="stat"><b>{overview.sightings}</b><span>Sightings</span></div>
        </div>
      )}

      <div className="tabs">
        {TABS.map(([key, label]) => (
          <button key={key} className={key === tab ? "on" : ""} onClick={() => setTab(key)}>
            {label}
            {key === "alerts" && overview && overview.pending_matches > 0 ? ` (${overview.pending_matches})` : ""}
          </button>
        ))}
      </div>

      {tab === "matches" && <MatchesPane onChange={refresh} />}
      {tab === "cases" && <CasesPane onChange={refresh} />}
      {tab === "sightings" && <SightingsPane />}
      {tab === "alerts" && <AlertsPane onReview={() => setTab("matches")} />}
    </div>
  );
}
