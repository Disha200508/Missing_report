// All calls to the Flask backend go through here.
export async function api(path, opts = {}) {
  const res = await fetch("/api" + path, opts);
  let data = {};
  try { data = await res.json(); } catch (e) { /* empty body */ }
  if (!res.ok) {
    const message = data.details ? `${data.error} [Details: ${data.details}]` : (data.error || `Request failed (HTTP ${res.status})`);
    throw Object.assign(new Error(message), { status: res.status });
  }
  return data;
}

export const postJSON = (path, body) =>
  api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });

export const patchJSON = (path, body) =>
  api(path, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });

export const postForm = (path, formData) => api(path, { method: "POST", body: formData });

export const imageUrl = (name) => "/api/admin/images/" + String(name || "").split("/").map(encodeURIComponent).join("/");

export const STATUSES = ["Active", "Under Investigation", "Probable Match Found", "Verified", "Closed"];
