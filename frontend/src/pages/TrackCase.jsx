import { useState } from "react";
import { api } from "../api.js";

export default function TrackCase() {
  const [id, setId] = useState("");
  const [res, setRes] = useState(null);
  const [error, setError] = useState("");

  async function check(e) {
    e.preventDefault();
    setError(""); setRes(null);
    try { setRes(await api(`/cases/${encodeURIComponent(id.trim())}/status`)); } catch (ex) { setError(ex.message); }
  }

  return (
    <div className="wrap narrow">
      <h1>Track a case</h1>
      <form className="card" onSubmit={check}>
        <label>Case ID
          <input type="text" required placeholder="e.g. MP-2026-0001" value={id} onChange={(e) => setId(e.target.value)} />
        </label>
        <div className="error">{error}</div>
        <button className="btn" type="submit">Check status</button>
        {res && (
          <p>Case <strong>{res.id}</strong> is <span className={`pill ${res.status}`}>{res.status}</span><br />
            <small>Last updated {res.updated_at}</small></p>
        )}
      </form>
    </div>
  );
}
