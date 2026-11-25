import { useEffect, useState } from "react";
import { api } from "../api.js";
import FormShell from "../components/FormShell.jsx";
import PhotoField from "../components/PhotoField.jsx";

export default function ReportSighting() {
  const [result, setResult] = useState(null);
  const [previewId, setPreviewId] = useState("");
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    api("/next-ids").then((r) => setPreviewId(r.sighting_id)).catch(() => {});
  }, []);

  if (result) {
    return (
      <div className="wrap narrow">
        <div className="success">
          <p>Report submitted</p>
          <div className="big">Sighting ID: {result.sighting_id}</div>
          <p>{result.message}</p>
        </div>
        {showModal && (
          <div className="modal" onClick={(e) => e.target === e.currentTarget && setShowModal(false)}>
            <div className="box" style={{ maxWidth: 440, textAlign: "center" }}>
              <h2 style={{ color: "var(--ok)", marginBottom: 8 }}>Report submitted</h2>
              <p style={{ margin: "0 0 12px" }}>{result.message}</p>
              <div className="success" style={{ margin: "12px 0" }}>
                <div style={{ fontSize: ".85rem", color: "var(--muted)" }}>Sighting Reference ID</div>
                <div className="big">{result.sighting_id}</div>
              </div>
              <div className="actions">
                <button className="btn small" onClick={() => setShowModal(false)}>OK</button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="wrap narrow">
      <h1>Report a sighting</h1>
      <p>Found someone who may be lost or missing? Upload a photo and tell us where they are.</p>
      {previewId && <div className="notice" style={{ marginBottom: 14 }}>Sighting ID: <strong>{previewId}</strong></div>}
      <FormShell endpoint="/sightings" onDone={(r) => { setResult(r); setShowModal(true); }} submitLabel="Submit report">
        <PhotoField />
        <label>Where was the person seen? *<input name="location" required placeholder="e.g. Railway station, Dehradun" /></label>
        <label>Details<textarea name="description" rows={3} maxLength={800} placeholder="Condition, clothing, who they are with…" /></label>
        <div className="row">
          <label>Your name<input name="reporter_name" /></label>
          <label>Your phone / email<input name="reporter_contact" /></label>
        </div>
        <div className="notice">If someone is in danger or needs urgent help, call the emergency number <strong>112</strong> first.</div>
      </FormShell>
    </div>
  );
}
