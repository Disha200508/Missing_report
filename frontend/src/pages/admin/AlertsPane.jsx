import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api.js";

export default function AlertsPane() {
  const [data, setData] = useState(null);
  useEffect(() => {
    Promise.all([
      api("/admin/matches?status=pending"),
      api("/admin/notifications"),
    ]).then(([pendingMatches, notifications]) => setData({ pendingMatches, notifications }));
  }, []);

  if (!data) return <div className="empty">Loading…</div>;
  const { pendingMatches, notifications } = data;

  return (
    <>
      <h3 style={{ marginBottom: 10 }}>Admin Match Alerts</h3>
      {!pendingMatches.length ? (
        <div className="empty" style={{ padding: "18px 0" }}>No pending probable-match alerts.</div>
      ) : (
        <div className="tablewrap" style={{ marginBottom: 24 }}>
          <table>
            <thead><tr><th>Detected</th><th>Case</th><th>Sighting</th><th>Confidence</th><th>Action</th></tr></thead>
            <tbody>
              {pendingMatches.map((m) => (
                <tr key={m.id}>
                  <td>{m.created_at}</td>
                  <td><strong>{m.case_code || `#${m.case_id}`} {m.name}</strong><br /><small>{m.last_seen_location || "-"}</small></td>
                  <td><strong>{m.sighting_code || `#${m.sighting_id}`}</strong> {m.sighting_location}</td>
                  <td><span className="pill pending">{m.score}% match</span></td>
                  <td><Link className="btn small" to={`/admin/report/${m.id}`}>View full report</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h3 style={{ marginBottom: 10 }}>Family Notifications Sent</h3>
      {!notifications.length ? (
        <div className="empty" style={{ padding: "18px 0" }}>No family alerts sent yet.</div>
      ) : (
        <div className="tablewrap">
          <table>
            <thead><tr><th>Time</th><th>Channel</th><th>To</th><th>Status</th><th>Match</th><th>Message</th><th>Report</th></tr></thead>
            <tbody>
              {notifications.map((n) => (
                <tr key={n.id}>
                  <td>{n.created_at}</td>
                  <td>{n.channel}</td>
                  <td>{n.recipient}</td>
                  <td>
                    <span className={"pill " + (n.status === "sent" ? "Verified" : n.status === "failed" ? "rejected" : "pending")}>
                      {n.status || "logged"}
                    </span>
                    {n.error && <><br /><small>{n.error}</small></>}
                  </td>
                  <td>
                    {n.match_id ? (
                      <>
                        <strong>{n.case_code || `#${n.case_id ?? "?"}`}</strong> {n.case_name || ""} ↔ <strong>{n.sighting_code || `#${n.sighting_id ?? "?"}`}</strong><br />
                        <small>{n.score ?? "-"}% · <span className={"pill " + (n.match_status || "")}>{n.match_status || "-"}</span></small>
                      </>
                    ) : "-"}
                  </td>
                  <td>{n.message}</td>
                  <td>{n.match_id ? <Link className="btn small" to={`/admin/report/${n.match_id}`}>View full report</Link> : "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
