import { useEffect, useState } from "react";
import { api, patchJSON, imageUrl, STATUSES } from "../../api.js";
import { useToast } from "../../components/Toast.jsx";

export default function CaseModal({ id, onClose, onSaved }) {
  const toast = useToast();
  const [data, setData] = useState(null);
  const [status, setStatus] = useState("");

  useEffect(() => {
    api("/admin/cases/" + id).then((d) => { setData(d); setStatus(d.case.status); });
  }, [id]);

  async function save() {
    await patchJSON(`/admin/cases/${id}/status`, { status });
    toast("Status updated"); onSaved(); onClose();
  }

  if (!data) return null;
  const { case: c, history } = data;
  return (
    <div className="modal" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="box">
        <div style={{ display: "flex", gap: 16 }}>
          <img className="thumb" style={{ width: 130 }} src={imageUrl(c.photo)} alt="" />
          <div>
            <h3>{c.code || `#${c.id}`} · {c.name}</h3>
            <div className="facts">
              {c.age ?? "?"} yrs · {c.gender || "-"}<br />
              Missing since: {c.date_missing || "-"}<br />
              Last seen: {c.last_seen_location || "-"}<br />
              Marks: {c.marks || "-"}<br />
              Contact: {c.contact_name} {c.contact_phone} {c.contact_email}
            </div>
          </div>
        </div>
        <label style={{ marginTop: 14 }}>Status
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            {STATUSES.map((s) => <option key={s}>{s}</option>)}
          </select>
        </label>
        <h3 style={{ marginTop: 16 }}>History</h3>
        <ul className="timeline">
          {history.map((h, i) => <li key={i}>{h.event}<small>{h.actor} · {h.created_at}</small></li>)}
        </ul>
        <div className="actions">
          <button className="btn small" onClick={save}>Save status</button>
          <button className="btn ghost small" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}
