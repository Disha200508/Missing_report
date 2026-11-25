import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, postJSON, imageUrl } from "../../api.js";
import { useToast } from "../../components/Toast.jsx";
import ImageModal from "../../components/ImageModal.jsx";

export default function MatchesPane({ onChange }) {
  const toast = useToast();
  const [status, setStatus] = useState("pending");
  const [rows, setRows] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [zoomImg, setZoomImg] = useState(null);

  const load = () => api("/admin/matches?status=" + status).then(setRows);
  useEffect(() => { setRows(null); load(); }, [status]);

  async function review(m, action) {
    if (action === "verify" && !window.confirm("Confirm these are the same person? The family will be notified.")) return;
    setBusyId(m.id);
    try {
      await postJSON(`/admin/matches/${m.id}/${action}`);
      toast(action === "verify" ? "Verified. Family notified." : "Match rejected");
      await load(); onChange();
    } catch (ex) { toast(ex.message); }
    setBusyId(null);
  }

  return (
    <>
      <div className="toolbar">
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="pending">Pending review</option>
          <option value="verified">Verified</option>
          <option value="rejected">Rejected</option>
        </select>
      </div>
      {rows === null && <div className="empty">Loading…</div>}
      {rows && rows.length === 0 && <div className="empty">No {status} matches.</div>}
      {rows && rows.map((m) => {
        const level = m.score >= 75 ? "hi" : m.score >= 50 ? "mid" : "lo";
        return (
          <div className="card" style={{ marginBottom: 16 }} key={m.id}>
            <div className="match">
              <div>
                <div
                  className="img-wrap"
                  onClick={() => setZoomImg({ src: imageUrl(m.case_photo), caption: `${m.case_code || `#${m.case_id}`} · ${m.name}` })}
                >
                  <img src={imageUrl(m.case_photo)} alt="Missing person" />
                  <span className="enlarge-hint">🔍 Enlarge</span>
                </div>
                <div className="facts" style={{ marginTop: 8 }}>
                  <strong>{m.case_code || `#${m.case_id}`}: {m.name}</strong><br />
                  {m.age ?? "?"} yrs · {m.gender || "-"}<br />Last seen: {m.last_seen_location || "-"}
                </div>
              </div>
              <div className={"score " + level}>
                <b>{m.score}%</b>match<br /><span className={"pill " + m.status}>{m.status}</span>
              </div>
              <div>
                <div
                  className="img-wrap"
                  onClick={() => setZoomImg({ src: imageUrl(m.sighting_photo), caption: `${m.sighting_code || `#${m.sighting_id}`} · ${m.sighting_location}` })}
                >
                  <img src={imageUrl(m.sighting_photo)} alt="Sighting" />
                  <span className="enlarge-hint">🔍 Enlarge</span>
                </div>
                <div className="facts" style={{ marginTop: 8 }}>
                  <strong>{m.sighting_code || `#${m.sighting_id}`}</strong><br />
                  {m.sighting_location}<br />{m.description}<br />{m.seen_at}
                </div>
              </div>
            </div>
            {m.status === "pending" ? (
              <div className="actions">
                <button className="btn ok small" disabled={busyId === m.id} onClick={() => review(m, "verify")}>✓ Verify &amp; notify family</button>
                <button className="btn bad small" disabled={busyId === m.id} onClick={() => review(m, "reject")}>✕ Not the same person</button>
                <Link className="btn ghost small" to={`/admin/report/${m.id}`}>View full report</Link>
              </div>
            ) : (
              <p className="facts" style={{ textAlign: "center" }}>
                Reviewed by {m.reviewed_by} on {m.reviewed_at} · <Link to={`/admin/report/${m.id}`}>View full report</Link>
              </p>
            )}
          </div>
        );
      })}
      {zoomImg && (
        <ImageModal
          src={zoomImg.src}
          caption={zoomImg.caption}
          onClose={() => setZoomImg(null)}
        />
      )}
    </>
  );
}
