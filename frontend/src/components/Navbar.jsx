import { useState } from "react";
import { NavLink, Link } from "react-router-dom";

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);
  return (
    <header className="nav">
      <Link to="/" className="brand" onClick={close}><span className="dot" />MPIS</Link>
      <button className="burger" aria-label="Menu" onClick={() => setOpen(!open)}>☰</button>
      <nav className={open ? "open" : ""}>
        <NavLink to="/register" onClick={close}>Report missing</NavLink>
        <NavLink to="/report" onClick={close}>Report a sighting</NavLink>
        <NavLink to="/track" onClick={close}>Track a case</NavLink>
        <NavLink to="/admin" className="staff" onClick={close}>Admin login</NavLink>
      </nav>
    </header>
  );
}
