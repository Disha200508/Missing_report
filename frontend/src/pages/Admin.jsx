import { useEffect, useState } from "react";
import { api } from "../api.js";
import Login from "./admin/Login.jsx";
import Dashboard from "./admin/Dashboard.jsx";

export default function Admin() {
  const [user, setUser] = useState(undefined);   // undefined = still checking
  useEffect(() => { api("/me").then((r) => setUser(r.user)).catch(() => setUser(null)); }, []);

  if (user === undefined) return <div className="wrap"><div className="empty">Loading…</div></div>;
  if (!user) return <Login onLogin={setUser} />;
  return <Dashboard user={user} onLogout={() => setUser(null)} />;
}
