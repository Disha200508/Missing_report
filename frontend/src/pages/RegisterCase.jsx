import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import FormShell from "../components/FormShell.jsx";
import PhotoField from "../components/PhotoField.jsx";

export default function RegisterCase() {
  const [result, setResult] = useState(null);
  const [previewId, setPreviewId] = useState("");
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    api("/next-ids").then((r) => setPreviewId(r.case_id)).catch(() => {});
  }, []);

  if (result) {
    return (
      <div className="wrap narrow">
        <div className="success">
          <p>Report submitted</p>
          <div className="big">Case ID: {result.case_id}</div>
          <p>Please save this ID. You can use it to <Link to="/track">track the status</Link> of your case.
            We will contact you if staff verify a possible match.</p>
        </div>
        {showModal && (
          <div className="modal" onClick={(e) => e.target === e.currentTarget && setShowModal(false)}>
            <div className="box" style={{ maxWidth: 440, textAlign: "center" }}>
              <h2 style={{ color: "var(--ok)", marginBottom: 8 }}>Report submitted</h2>
              <p style={{ margin: "0 0 12px" }}>Your missing person report has been submitted. Save this ID to track your case.</p>
              <div className="success" style={{ margin: "12px 0" }}>
                <div style={{ fontSize: ".85rem", color: "var(--muted)" }}>Missing Person Case ID</div>
                <div className="big">{result.case_id}</div>
              </div>
              <div className="actions">
                <Link className="btn ghost small" to="/track" onClick={() => setShowModal(false)}>Track case</Link>
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
      <h1>Report a missing person</h1>
      <p>Fill in what you know. Only the name, a photo and a way to contact you are required.</p>
      {previewId && <div className="notice" style={{ marginBottom: 14 }}>Case ID: <strong>{previewId}</strong></div>}
      <FormShell endpoint="/cases" onDone={(r) => { setResult(r); setShowModal(true); }} submitLabel="Register case">
        <div className="row">
          <label>Full name *<input name="name" required maxLength={100} /></label>
          <label>Age<input name="age" type="number" min="0" max="120" /></label>
        </div>
        <div className="row">
          <label>Gender
            <select name="gender"><option value="">Select</option><option>Female</option><option>Male</option><option>Other</option></select>
          </label>
          <label>Date missing<input name="date_missing" type="date" /></label>
        </div>
        <label>Last seen location<input name="last_seen_location" placeholder="Area, city" /></label>
        <label>Identifying marks / clothing<textarea name="marks" rows={2} maxLength={500} /></label>
        <PhotoField />
        <h3 style={{ margin: "6px 0 0" }}>Your contact details</h3>
        <div className="notice">Used only to alert you once staff verify a match.</div>
        <div className="row">
          <label>Your name<input name="contact_name" /></label>
          <label>Phone *<input name="contact_phone" placeholder="+91 98765 43210" /></label>
        </div>
        <label>Email<input name="contact_email" type="email" /></label>
      </FormShell>
    </div>
  );
}
