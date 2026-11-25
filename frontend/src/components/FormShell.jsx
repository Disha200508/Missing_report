import { useState } from "react";
import { postForm } from "../api.js";

// Shared <form> that posts multipart data and reports success/error.
export default function FormShell({ endpoint, onDone, submitLabel, children }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setBusy(true); setError("");
    try {
      onDone(await postForm(endpoint, new FormData(e.target)));
    } catch (ex) {
      setError(ex.message);
      setBusy(false);
    }
  }

  return (
    <form className="card" onSubmit={handleSubmit}>
      {children}
      <div className="error">{error}</div>
      <button className="btn accent" type="submit" disabled={busy}>
        {busy ? "Analysing photo…" : submitLabel}
      </button>
    </form>
  );
}
