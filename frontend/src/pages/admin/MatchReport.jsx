import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, postJSON, imageUrl } from "../../api.js";
import { useToast } from "../../components/Toast.jsx";
import ImageModal from "../../components/ImageModal.jsx";
import Login from "./Login.jsx";

export default function MatchReport() {
  const { matchId } = useParams();
  const toast = useToast();
  const [user, setUser] = useState(undefined);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [zoomImg, setZoomImg] = useState(null);

  const loadReport = () =>
    api(`/admin/matches/${matchId}`).then(setData).catch((e) => setError(e.message));

  useEffect(() => {
    api("/me").then((r) => {
      setUser(r.user);
      if (r.user) loadReport();
    }).catch(() => setUser(null));
  }, [matchId]);

  async function act(action) {
    if (action === "verify" && !window.confirm("Confirm these are the same person and notify the family?")) return;
    if (action === "reject" && !window.confirm("Mark this match as NOT the same person?")) return;
    setBusy(true);
    try {
      await postJSON(`/admin/matches/${matchId}/${action}`);
      toast("Report updated");
      await loadReport();
    } catch (ex) {
      toast(ex.message);
    }
    setBusy(false);
  }

  if (user === undefined) return <div className="wrap"><div className="empty">Loading…</div></div>;
  if (!user) return <Login onLogin={(u) => { setUser(u); loadReport(); }} />;
  if (error) return <div className="wrap"><div className="card"><div className="error">{error}</div><Link className="btn ghost small" to="/admin">Back to Dashboard</Link></div></div>;
  if (!data) return <div className="wrap"><div className="empty">Loading full report…</div></div>;

  const { match: m, case: c, sighting: s, history, notifications } = data;
  const level = m.score >= 75 ? "hi" : m.score >= 50 ? "mid" : "lo";

  return (
    <div className="wrap">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10, marginBottom: 18 }}>
        <Link className="btn ghost small" to="/admin">← Back to Alerts</Link>
        <div>Signed in as <strong>{user}</strong></div>
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 14 }}>
          <div>
            <h1>Match Report #{m.id}</h1>
            <div className="facts">
              Detected: {m.created_at} · Cosine distance: {Number(m.distance).toFixed(4)}
              {m.reviewed_by && <><br />Last reviewed by <strong>{m.reviewed_by}</strong> on {m.reviewed_at}</>}
            </div>
          </div>
          <div className={"score " + level}>
            <b>{m.score}%</b>match<br /><span className={"pill " + m.status}>{m.status}</span>
          </div>
        </div>
        <div className="actions" style={{ justifyContent: "flex-start", marginTop: 16 }}>
          {m.status !== "verified" ? (
            <button className="btn ok small" disabled={busy} onClick={() => act("verify")}>✓ Verify &amp; notify family</button>
          ) : (
            <button className="btn small" disabled={busy} onClick={() => act("notify")}>↻ Resend SMS / Email alert</button>
          )}
          {m.status !== "rejected" && <button className="btn bad small" disabled={busy} onClick={() => act("reject")}>✕ Mark as not the same person</button>}
          {m.status !== "pending" && <button className="btn ghost small" disabled={busy} onClick={() => act("reopen")}>↺ Reopen for review</button>}
        </div>
      </div>

      <div className="row" style={{ marginBottom: 20 }}>
        <div className="card">
          <h2>Missing Person Report</h2>
          {c ? (
            <>
              <div
                className="img-wrap"
                style={{ marginBottom: 14 }}
                onClick={() => setZoomImg({ src: imageUrl(c.photo), caption: `${c.code || `#${c.id}`} · ${c.name}` })}
              >
                <img className="thumb" style={{ maxHeight: 340 }} src={imageUrl(c.photo)} alt="Missing person" />
                <span className="enlarge-hint">🔍 Click to enlarge</span>
              </div>
              <div className="facts">
                <strong>{c.code || `#${c.id}`}: {c.name}</strong> <span className={"pill " + c.status}>{c.status}</span><br /><br />
                <strong>Age / Gender:</strong> {c.age ?? "-"} yrs · {c.gender || "-"}<br />
                <strong>Date missing:</strong> {c.date_missing || "-"}<br />
                <strong>Last seen location:</strong> {c.last_seen_location || "-"}<br />
                <strong>Identifying marks:</strong> {c.marks || "-"}<br />
                <strong>Contact person:</strong> {c.contact_name || "-"}<br />
                <strong>Phone:</strong> {c.contact_phone || "-"}<br />
                <strong>Email:</strong> {c.contact_email || "-"}<br />
                <strong>Registered:</strong> {c.created_at}<br />
                <strong>Updated:</strong> {c.updated_at}
              </div>
            </>
          ) : <div className="empty">Case record not found.</div>}
        </div>

        <div className="card">
          <h2>Sighting Report</h2>
          {s ? (
            <>
              <div
                className="img-wrap"
                style={{ marginBottom: 14 }}
                onClick={() => setZoomImg({ src: imageUrl(s.photo), caption: `${s.code || `#${s.id}`} · ${s.location}` })}
              >
                <img className="thumb" style={{ maxHeight: 340 }} src={imageUrl(s.photo)} alt="Sighting" />
                <span className="enlarge-hint">🔍 Click to enlarge</span>
              </div>
              <div className="facts">
                <strong>{s.code || `#${s.id}`}</strong><br /><br />
                <strong>Location seen:</strong> {s.location}<br />
                <strong>Description:</strong> {s.description || "-"}<br />
                <strong>Reporter name:</strong> {s.reporter_name || "-"}<br />
                <strong>Reporter contact:</strong> {s.reporter_contact || "-"}<br />
                <strong>Reported at:</strong> {s.created_at}
              </div>
            </>
          ) : <div className="empty">Sighting record not found.</div>}
        </div>
      </div>

      <div className="row">
        <div className="card">
          <h3>Case Timeline</h3>
          {history.length ? (
            <ul className="timeline">
              {history.map((h, i) => <li key={i}>{h.event}<small>{h.actor} · {h.created_at}</small></li>)}
            </ul>
          ) : <div className="empty">No history events.</div>}
        </div>
        <div className="card">
          <h3>Alerts Sent for This Match</h3>
          {notifications.length ? (
            <div className="tablewrap">
              <table>
                <thead><tr><th>Time</th><th>Channel</th><th>To</th><th>Status</th><th>Message</th></tr></thead>
                <tbody>
                  {notifications.map((n) => (
                    <tr key={n.id}>
                      <td>{n.created_at}</td>
                      <td>{n.channel}</td>
                      <td>{n.recipient}</td>
                      <td><span className={"pill " + (n.status === "sent" ? "Verified" : n.status === "failed" ? "rejected" : "pending")}>{n.status || "logged"}</span></td>
                      <td>{n.message}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <div className="empty">No family alerts sent for this match yet.</div>}
        </div>
      </div>
      {zoomImg && (
        <ImageModal
          src={zoomImg.src}
          caption={zoomImg.caption}
          onClose={() => setZoomImg(null)}
        />
      )}
    </div>
  );
}
