import { useEffect, useState } from "react";
import { api, imageUrl } from "../../api.js";

export default function SightingsPane() {
  const [rows, setRows] = useState(null);
  useEffect(() => { api("/admin/sightings").then(setRows); }, []);
  if (!rows) return <div className="empty">Loading…</div>;
  if (!rows.length) return <div className="empty">No sightings yet.</div>;
  return (
    <div className="tablewrap">
      <table>
        <thead><tr><th></th><th>Sighting ID</th><th>Location</th><th>Details</th><th>Reporter</th><th>Time</th></tr></thead>
        <tbody>
          {rows.map((s) => (
            <tr key={s.id}>
              <td><img src={imageUrl(s.photo)} alt="" /></td><td><strong>{s.code || `#${s.id}`}</strong></td><td>{s.location}</td>
              <td>{s.description || "-"}</td>
              <td>{s.reporter_name || "-"}<br /><small>{s.reporter_contact}</small></td>
              <td>{s.created_at}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
