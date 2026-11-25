import { useEffect, useState } from "react";
import { api, imageUrl, STATUSES } from "../../api.js";
import CaseModal from "./CaseModal.jsx";
import ImageModal from "../../components/ImageModal.jsx";

export default function CasesPane({ onChange }) {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [rows, setRows] = useState(null);
  const [openId, setOpenId] = useState(null);
  const [zoomImg, setZoomImg] = useState(null);

  const load = () =>
    api(`/admin/cases?q=${encodeURIComponent(q)}&status=${encodeURIComponent(status)}`).then(setRows);

  useEffect(() => {                       // debounce typing
    const t = setTimeout(load, 300);
    return () => clearTimeout(t);
  }, [q, status]);

  return (
    <>
      <div className="toolbar">
        <input placeholder="Search name, place or ID" value={q} onChange={(e) => setQ(e.target.value)} />
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          {STATUSES.map((s) => <option key={s}>{s}</option>)}
        </select>
      </div>
      {rows && rows.length === 0 && <div className="empty">No cases found.</div>}
      {rows && rows.length > 0 && (
        <div className="tablewrap">
          <table>
            <thead><tr><th></th><th>Case ID</th><th>Name</th><th>Age</th><th>Last seen</th><th>Status</th><th>Registered</th></tr></thead>
            <tbody>
              {rows.map((c) => (
                <tr key={c.id} style={{ cursor: "pointer" }} onClick={() => setOpenId(c.id)}>
                  <td onClick={(e) => { e.stopPropagation(); setZoomImg({ src: imageUrl(c.photo), caption: `${c.code || `#${c.id}`} · ${c.name}` }); }}>
                    <img src={imageUrl(c.photo)} alt="" />
                  </td>
                  <td><strong>{c.code || `#${c.id}`}</strong></td><td>{c.name}</td><td>{c.age ?? "-"}</td>
                  <td>{c.last_seen_location || "-"}</td>
                  <td><span className={"pill " + c.status}>{c.status}</span></td>
                  <td>{c.created_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {openId && <CaseModal id={openId} onClose={() => setOpenId(null)} onSaved={() => { load(); onChange(); }} />}
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
