import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";

const STEPS = [
  ["Register or report", "Upload a clear photo with a few details. Families register cases; anyone can report a sighting."],
  ["AI compares faces", "The face is detected, converted to a numerical fingerprint and compared against every stored record."],
  ["Humans verify", "Possible matches go to authorised staff. Nothing is acted on until a person confirms it."],
  ["Family is alerted", "Once verified, the family or authority is notified by SMS or email."],
];

export default function Home() {
  const [stats, setStats] = useState(null);
  useEffect(() => { api("/stats").then(setStats).catch(() => {}); }, []);

  return (
    <>
      <section className="hero">
        <div className="in">
          <h1>Helping families find their missing loved ones, faster.</h1>
          <p>Register a missing person, or report someone you have seen. Our face-matching system compares photos
            in seconds and passes possible matches to trained staff to verify.</p>
          <div className="btns">
            <Link className="btn accent" to="/register">Report a missing person</Link>
            <Link className="btn ghost" to="/report">I saw someone</Link>
          </div>
        </div>
      </section>

      {stats && (
        <div className="stats">
          <div className="stat"><b>{stats.cases}</b><span>Cases registered</span></div>
          <div className="stat"><b>{stats.sightings}</b><span>Sightings reported</span></div>
          <div className="stat"><b>{stats.verified}</b><span>Verified matches</span></div>
        </div>
      )}

      <div className="wrap">
        <h2 className="section-title">How it works</h2>
        <div className="grid">
          {STEPS.map(([title, text], i) => (
            <div className="card" key={title}>
              <div className="num">{i + 1}</div><h3>{title}</h3><p>{text}</p>
            </div>
          ))}
        </div>
        <div className="notice" style={{ marginTop: 28 }}>
          <strong>Privacy first:</strong> photos are only visible to authorised staff. Public users never see
          other people's photos or match results.
        </div>
      </div>
    </>
  );
}
