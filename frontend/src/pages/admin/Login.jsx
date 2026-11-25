import { useState } from "react";
import { postJSON } from "../../api.js";

export default function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault(); setError("");
    try { onLogin((await postJSON("/login", { username, password })).user); }
    catch (ex) { setError(ex.message); }
  }

  return (
    <div className="wrap narrow">
      <h1>Staff login</h1>
      <form className="card" onSubmit={submit}>
        <label>Username<input autoComplete="username" required value={username} onChange={(e) => setUsername(e.target.value)} /></label>
        <label>Password<input type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} /></label>
        <div className="error">{error}</div>
        <button className="btn" type="submit">Log in</button>
      </form>
    </div>
  );
}
