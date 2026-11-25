/* MPIS frontend - plain JavaScript single-page app (no build tools needed) */
const $app = document.getElementById("app");
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

function toast(msg){
  const t = document.getElementById("toast");
  t.textContent = msg; t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 3000);
}

async function api(path, opts = {}){
  const res = await fetch("/api" + path, opts);
  let data = {};
  try { data = await res.json(); } catch(e){}
  if (!res.ok) throw Object.assign(new Error(data.error || `Request failed (HTTP ${res.status})`), {status: res.status});
  return data;
}
const postJSON = (p, body) => api(p, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body||{})});
const img = n => "/api/admin/images/" + String(n || "").split("/").map(encodeURIComponent).join("/");

/* ------------------------------------------------ router */
const routes = {"/": home, "/register": registerPage, "/report": reportPage, "/track": trackPage, "/admin": adminPage};
function router(){
  const path = location.hash.replace("#","") || "/";
  const reportMatch = path.match(/^\/admin\/report\/(\d+)$/);
  if (reportMatch) {
    reportDetailPage(reportMatch[1]);
  } else {
    (routes[path] || home)();
  }
  document.querySelectorAll("nav a").forEach(a => a.classList.toggle("active", a.getAttribute("href") === "#"+path));
  document.getElementById("menu").classList.remove("open");
  window.scrollTo(0,0);
}
window.addEventListener("hashchange", router);
document.getElementById("burger").onclick = () => document.getElementById("menu").classList.toggle("open");

/* ------------------------------------------------ home */
async function home(){
  $app.innerHTML = `
  <section class="hero"><div class="in">
    <h1>Helping families find their missing loved ones, faster.</h1>
    <p>Register a missing person, or report someone you have seen. Our face-matching system compares photos in seconds
       and passes possible matches to trained staff to verify.</p>
    <div class="btns">
      <a class="btn accent" href="#/register">Report a missing person</a>
      <a class="btn ghost" href="#/report">I saw someone</a>
    </div>
  </div></section>
  <div class="stats" id="stats"></div>
  <div class="wrap">
    <h2 class="section-title">How it works</h2>
    <div class="grid">
      <div class="card"><div class="num">1</div><h3>Register or report</h3><p>Upload a clear photo with a few details. Families register cases; anyone can report a sighting.</p></div>
      <div class="card"><div class="num">2</div><h3>AI compares faces</h3><p>The face is detected, converted to a numerical fingerprint and compared against every stored record.</p></div>
      <div class="card"><div class="num">3</div><h3>Humans verify</h3><p>Possible matches go to authorised staff. Nothing is acted on until a person confirms it.</p></div>
      <div class="card"><div class="num">4</div><h3>Family is alerted</h3><p>Once verified, the family or authority is notified by SMS or email.</p></div>
    </div>
    <div class="notice" style="margin-top:28px"><strong>Privacy first:</strong> photos are only visible to authorised staff. Public users never see other people's photos or match results.</div>
  </div>`;
  try{
    const s = await api("/stats");
    document.getElementById("stats").innerHTML =
      `<div class="stat"><b>${s.cases}</b><span>Cases registered</span></div>
       <div class="stat"><b>${s.sightings}</b><span>Sightings reported</span></div>
       <div class="stat"><b>${s.verified}</b><span>Verified matches</span></div>`;
  }catch(e){}
}

/* ------------------------------------------------ shared form helpers */
function photoField(){
  return `<label>Photo *<small>Clear, front-facing, good light. JPG / PNG, max 10 MB.</small>
    <div class="drop"><input type="file" name="photo" id="photo" accept="image/*" required>
    <img id="preview" alt="" hidden></div></label>`;
}
function wirePreview(){
  document.getElementById("photo").onchange = e => {
    const f = e.target.files[0], p = document.getElementById("preview");
    if (f){ p.src = URL.createObjectURL(f); p.hidden = false; }
  };
}
function submitForm(form, endpoint, onDone){
  form.onsubmit = async e => {
    e.preventDefault();
    const btn = form.querySelector("button[type=submit]"), er = form.querySelector(".error");
    er.textContent = ""; btn.disabled = true; const old = btn.textContent; btn.textContent = "Analysing photo…";
    try { onDone(await api(endpoint, {method:"POST", body:new FormData(form)})); }
    catch(ex){ er.textContent = ex.message; btn.disabled = false; btn.textContent = old; }
  };
}

function showReportModal(title, idLabel, idValue, message, extraLinkHtml = ""){
  const m = document.createElement("div");
  m.className = "modal";
  m.innerHTML = `<div class="box" style="max-width:440px;text-align:center">
    <h2 style="color:var(--ok);margin-bottom:8px">${esc(title)}</h2>
    <p style="margin:0 0 12px">${esc(message)}</p>
    <div class="success" style="margin:12px 0">
      <div style="font-size:.85rem;color:var(--muted)">${esc(idLabel)}</div>
      <div class="big">${esc(idValue)}</div>
    </div>
    <div class="actions">
      ${extraLinkHtml}
      <button class="btn small" id="ok-modal">OK</button>
    </div>
  </div>`;
  document.body.appendChild(m);
  const close = () => m.remove();
  m.onclick = e => { if (e.target === m) close(); };
  m.querySelector("#ok-modal").onclick = close;
  m.querySelectorAll("a").forEach(a => a.onclick = close);
}

/* ------------------------------------------------ register missing */
function registerPage(){
  $app.innerHTML = `<div class="wrap narrow"><h1>Report a missing person</h1>
  <p>Fill in what you know. Only the name, a photo and a way to contact you are required.</p>
  <div class="notice" style="margin-bottom:14px">Case ID: <strong id="preview-id">Assigning…</strong></div>
  <form class="card" id="f">
    <div class="row"><label>Full name *<input name="name" required maxlength="100"></label>
      <label>Age<input name="age" type="number" min="0" max="120"></label></div>
    <div class="row"><label>Gender<select name="gender"><option value="">Select</option><option>Female</option><option>Male</option><option>Other</option></select></label>
      <label>Date missing<input name="date_missing" type="date"></label></div>
    <label>Last seen location<input name="last_seen_location" placeholder="Area, city"></label>
    <label>Identifying marks / clothing<textarea name="marks" rows="2" maxlength="500"></textarea></label>
    ${photoField()}
    <h3 style="margin:6px 0 0">Your contact details</h3>
    <div class="notice">Used only to alert you once staff verify a match.</div>
    <div class="row"><label>Your name<input name="contact_name"></label>
      <label>Phone *<input name="contact_phone" placeholder="+91 98765 43210"></label></div>
    <label>Email<input name="contact_email" type="email"></label>
    <div class="error"></div>
    <button class="btn accent" type="submit">Register case</button>
  </form></div>`;
  api("/next-ids").then(r => {
    const el = document.getElementById("preview-id");
    if (el) el.textContent = r.case_id;
  }).catch(() => {});
  wirePreview();
  submitForm(document.getElementById("f"), "/cases", r => {
    $app.innerHTML = `<div class="wrap narrow"><div class="success"><p>Report submitted</p>
      <div class="big">Case ID: ${esc(r.case_id)}</div>
      <p>Please save this ID. You can use it to <a href="#/track">track the status</a> of your case.
      We will contact you if staff verify a possible match.</p></div></div>`;
    showReportModal(
      "Report submitted",
      "Missing Person Case ID",
      r.case_id,
      "Your missing person report has been submitted. Save this ID to track your case.",
      `<a class="btn ghost small" href="#/track">Track case</a>`
    );
  });
}

/* ------------------------------------------------ report sighting */
function reportPage(){
  $app.innerHTML = `<div class="wrap narrow"><h1>Report a sighting</h1>
  <p>Found someone who may be lost or missing? Upload a photo and tell us where they are.</p>
  <div class="notice" style="margin-bottom:14px">Sighting ID: <strong id="preview-id">Assigning…</strong></div>
  <form class="card" id="f">
    ${photoField()}
    <label>Where was the person seen? *<input name="location" required placeholder="e.g. Railway station, Dehradun"></label>
    <label>Details<textarea name="description" rows="3" maxlength="800" placeholder="Condition, clothing, who they are with…"></textarea></label>
    <div class="row"><label>Your name<input name="reporter_name"></label>
      <label>Your phone / email<input name="reporter_contact"></label></div>
    <div class="notice">If someone is in danger or needs urgent help, call the emergency number <strong>112</strong> first.</div>
    <div class="error"></div>
    <button class="btn accent" type="submit">Submit report</button>
  </form></div>`;
  api("/next-ids").then(r => {
    const el = document.getElementById("preview-id");
    if (el) el.textContent = r.sighting_id;
  }).catch(() => {});
  wirePreview();
  submitForm(document.getElementById("f"), "/sightings", r => {
    $app.innerHTML = `<div class="wrap narrow"><div class="success"><p>Report submitted</p>
      <div class="big">Sighting ID: ${esc(r.sighting_id)}</div>
      <p>${esc(r.message)}</p></div></div>`;
    showReportModal(
      "Report submitted",
      "Sighting Reference ID",
      r.sighting_id,
      r.message
    );
  });
}

/* ------------------------------------------------ track */
function trackPage(){
  $app.innerHTML = `<div class="wrap narrow"><h1>Track a case</h1>
  <form class="card" id="f"><label>Case ID<input id="cid" type="text" required placeholder="e.g. MP-2026-0001"></label>
  <div class="error"></div><button class="btn" type="submit">Check status</button><div id="out"></div></form></div>`;
  document.getElementById("f").onsubmit = async e => {
    e.preventDefault();
    const out = document.getElementById("out"), er = e.target.querySelector(".error"); er.textContent = ""; out.innerHTML = "";
    try{
      const cid = document.getElementById("cid").value.trim();
      const r = await api(`/cases/${encodeURIComponent(cid)}/status`);
      out.innerHTML = `<p>Case <strong>${esc(r.id)}</strong> is <span class="pill ${esc(r.status)}">${esc(r.status)}</span>
        <br><small>Last updated ${esc(r.updated_at)}</small></p>`;
    }catch(ex){ er.textContent = ex.message; }
  };
}

/* ------------------------------------------------ admin */
async function adminPage(){
  const me = await api("/me");
  if (!me.user) return loginView();
  dashboard(me.user);
}
function loginView(){
  $app.innerHTML = `<div class="wrap narrow"><h1>Staff login</h1>
  <form class="card" id="f"><label>Username<input name="u" autocomplete="username" required></label>
  <label>Password<input name="p" type="password" autocomplete="current-password" required></label>
  <div class="error"></div><button class="btn" type="submit">Log in</button></form></div>`;
  document.getElementById("f").onsubmit = async e => {
    e.preventDefault(); const er = e.target.querySelector(".error"); er.textContent = "";
    try{ await postJSON("/login", {username:e.target.u.value, password:e.target.p.value}); adminPage(); }
    catch(ex){ er.textContent = ex.message; }
  };
}

const TABS = [["matches","Match review"],["cases","Cases"],["sightings","Sightings"],["alerts","Alerts"]];
let tab = "matches", currentUser = "";
async function dashboard(user){
  currentUser = user;
  $app.innerHTML = `<div class="wrap">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
      <h1>Dashboard</h1><div>Signed in as <strong>${esc(user)}</strong> <button class="btn ghost small" id="out">Log out</button></div></div>
    <div id="alert-banner"></div>
    <div id="ov" class="grid" style="margin-bottom:22px"></div>
    <div class="tabs">${TABS.map(([k,l]) => `<button data-t="${k}" class="${k===tab?"on":""}">${l}</button>`).join("")}</div>
    <div id="pane"></div></div>`;
  document.getElementById("out").onclick = async () => { await postJSON("/logout"); loginView(); };
  document.querySelectorAll(".tabs button").forEach(b => b.onclick = () => { tab = b.dataset.t; dashboard(user); });
  try{
    const o = await api("/admin/overview");
    if (o.pending_matches > 0){
      const ab = document.getElementById("alert-banner");
      ab.innerHTML = `<div class="notice" style="margin-bottom:18px;border-left-color:var(--accent);background:rgba(232,116,59,.12);display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap">
        <div><strong>Match alert:</strong> ${o.pending_matches} probable face ${o.pending_matches===1?"match":"matches"} detected and awaiting staff verification.</div>
        ${tab !== "matches" ? `<button class="btn accent small" id="go-matches">Review matches</button>` : ""}
      </div>`;
      const gm = document.getElementById("go-matches");
      if (gm) gm.onclick = () => { tab = "matches"; dashboard(user); };
      const abtn = document.querySelector('.tabs button[data-t="alerts"]');
      if (abtn) abtn.textContent = `Alerts (${o.pending_matches})`;
    }
    document.getElementById("ov").innerHTML =
      `<div class="stat"><b>${o.pending_matches}</b><span>Matches awaiting review</span></div>
       <div class="stat"><b>${Object.values(o.by_status).reduce((a,b)=>a+b,0)}</b><span>Total cases</span></div>
       <div class="stat"><b>${o.by_status["Active"]}</b><span>Active cases</span></div>
       <div class="stat"><b>${o.sightings}</b><span>Sightings</span></div>`;
  }catch(e){ if (e.status===401) return loginView(); }
  ({matches:matchesPane, cases:casesPane, sightings:sightingsPane, alerts:alertsPane})[tab](document.getElementById("pane"));
}

async function matchesPane(p){
  p.innerHTML = `<div class="toolbar"><select id="ms"><option value="pending">Pending review</option>
    <option value="verified">Verified</option><option value="rejected">Rejected</option></select></div><div id="list"></div>`;
  const sel = document.getElementById("ms");
  const load = async () => {
    const list = document.getElementById("list"), rows = await api("/admin/matches?status="+sel.value);
    if (!rows.length){ list.innerHTML = `<div class="empty">No ${sel.value} matches.</div>`; return; }
    list.innerHTML = rows.map(m => {
      const lvl = m.score >= 75 ? "hi" : m.score >= 50 ? "mid" : "lo";
      return `<div class="card" style="margin-bottom:16px"><div class="match">
        <div><img src="${img(m.case_photo)}" alt="Missing person"><div class="facts"><strong>${esc(m.case_code || "#"+m.case_id)}: ${esc(m.name)}</strong><br>
          ${m.age ?? "?"} yrs · ${esc(m.gender||"-")}<br>Last seen: ${esc(m.last_seen_location||"-")}</div></div>
        <div class="score ${lvl}"><b>${m.score}%</b>match<br><span class="pill ${m.status}">${m.status}</span></div>
        <div><img src="${img(m.sighting_photo)}" alt="Sighting"><div class="facts"><strong>${esc(m.sighting_code || "#"+m.sighting_id)}</strong><br>
          ${esc(m.sighting_location)}<br>${esc(m.description||"")}<br>${esc(m.seen_at)}</div></div></div>
        ${m.status==="pending" ? `<div class="actions"><button class="btn ok small" data-a="verify" data-id="${m.id}">✓ Verify &amp; notify family</button>
          <button class="btn bad small" data-a="reject" data-id="${m.id}">✕ Not the same person</button>
          <a class="btn ghost small" href="#/admin/report/${m.id}">View full report</a></div>`
          : `<p class="facts" style="text-align:center">Reviewed by ${esc(m.reviewed_by)} on ${esc(m.reviewed_at)} · <a href="#/admin/report/${m.id}">View full report</a></p>`}
      </div>`;}).join("");
    list.querySelectorAll("[data-a]").forEach(b => b.onclick = async () => {
      if (b.dataset.a==="verify" && !confirm("Confirm these are the same person? The family will be notified.")) return;
      b.disabled = true;
      try{ await postJSON(`/admin/matches/${b.dataset.id}/${b.dataset.a}`); toast("Done"); dashboard(currentUser); }
      catch(ex){ toast(ex.message); b.disabled = false; }
    });
  };
  sel.onchange = load; load();
}

async function casesPane(p){
  p.innerHTML = `<div class="toolbar"><input id="q" placeholder="Search name, place or ID"><select id="st"><option value="">All statuses</option>
    ${["Active","Under Investigation","Probable Match Found","Verified","Closed"].map(s=>`<option>${s}</option>`).join("")}</select></div>
    <div class="tablewrap" id="tb"></div>`;
  const load = async () => {
    const rows = await api(`/admin/cases?q=${encodeURIComponent(q.value)}&status=${encodeURIComponent(st.value)}`);
    document.getElementById("tb").innerHTML = rows.length ? `<table><tr><th></th><th>Case ID</th><th>Name</th><th>Age</th><th>Last seen</th><th>Status</th><th>Registered</th></tr>
      ${rows.map(c => `<tr style="cursor:pointer" data-id="${c.id}"><td><img src="${img(c.photo)}" alt=""></td><td><strong>${esc(c.code || "#"+c.id)}</strong></td><td>${esc(c.name)}</td><td>${c.age ?? "-"}</td>
        <td>${esc(c.last_seen_location||"-")}</td><td><span class="pill ${esc(c.status)}">${esc(c.status)}</span></td><td>${esc(c.created_at)}</td></tr>`).join("")}</table>`
      : `<div class="empty">No cases found.</div>`;
    document.querySelectorAll("tr[data-id]").forEach(r => r.onclick = () => caseModal(r.dataset.id));
  };
  const q = document.getElementById("q"), st = document.getElementById("st");
  let t; q.oninput = () => { clearTimeout(t); t = setTimeout(load, 300); }; st.onchange = load; load();
}

async function caseModal(id){
  const {case:c, history} = await api("/admin/cases/"+id);
  const m = document.createElement("div"); m.className = "modal";
  m.innerHTML = `<div class="box"><div style="display:flex;gap:16px"><img class="thumb" style="width:130px" src="${img(c.photo)}" alt="">
    <div><h3>${esc(c.code || "#"+c.id)} · ${esc(c.name)}</h3><div class="facts">${c.age ?? "?"} yrs · ${esc(c.gender||"-")}<br>Missing since: ${esc(c.date_missing||"-")}<br>
    Last seen: ${esc(c.last_seen_location||"-")}<br>Marks: ${esc(c.marks||"-")}<br>Contact: ${esc(c.contact_name||"")} ${esc(c.contact_phone||"")} ${esc(c.contact_email||"")}</div></div></div>
    <label style="margin-top:14px">Status<select id="ns">${["Active","Under Investigation","Probable Match Found","Verified","Closed"].map(s=>`<option ${s===c.status?"selected":""}>${s}</option>`).join("")}</select></label>
    <h3 style="margin-top:16px">History</h3><ul class="timeline">${history.map(h=>`<li>${esc(h.event)}<small>${esc(h.actor)} · ${esc(h.created_at)}</small></li>`).join("")}</ul>
    <div class="actions"><button class="btn small" id="sv">Save status</button><button class="btn ghost small" id="cl">Close</button></div></div>`;
  document.body.appendChild(m);
  m.onclick = e => { if (e.target===m) m.remove(); };
  m.querySelector("#cl").onclick = () => m.remove();
  m.querySelector("#sv").onclick = async () => {
    await api(`/admin/cases/${id}/status`, {method:"PATCH", headers:{"Content-Type":"application/json"}, body:JSON.stringify({status:m.querySelector("#ns").value})});
    m.remove(); toast("Status updated"); casesPane(document.getElementById("pane"));
  };
}

async function sightingsPane(p){
  const rows = await api("/admin/sightings");
  p.innerHTML = rows.length ? `<div class="tablewrap"><table><tr><th></th><th>Sighting ID</th><th>Location</th><th>Details</th><th>Reporter</th><th>Time</th></tr>
    ${rows.map(s=>`<tr><td><img src="${img(s.photo)}" alt=""></td><td><strong>${esc(s.code || "#"+s.id)}</strong></td><td>${esc(s.location)}</td><td>${esc(s.description||"-")}</td>
    <td>${esc(s.reporter_name||"-")}<br><small>${esc(s.reporter_contact||"")}</small></td><td>${esc(s.created_at)}</td></tr>`).join("")}</table></div>`
    : `<div class="empty">No sightings yet.</div>`;
}
async function alertsPane(p){
  const [pendingMatches, notifications] = await Promise.all([
    api("/admin/matches?status=pending"),
    api("/admin/notifications")
  ]);
  const matchHtml = pendingMatches.length
    ? `<div class="tablewrap" style="margin-bottom:24px"><table><tr><th>Detected</th><th>Case</th><th>Sighting</th><th>Confidence</th><th>Action</th></tr>
        ${pendingMatches.map(m=>`<tr><td>${esc(m.created_at)}</td><td><strong>${esc(m.case_code || "#"+m.case_id)} ${esc(m.name)}</strong><br><small>${esc(m.last_seen_location||"-")}</small></td>
        <td><strong>${esc(m.sighting_code || "#"+m.sighting_id)}</strong> ${esc(m.sighting_location)}</td><td><span class="pill pending">${m.score}% match</span></td>
        <td><a class="btn small" href="#/admin/report/${m.id}">View full report</a></td></tr>`).join("")}</table></div>`
    : `<div class="empty" style="padding:18px 0">No pending probable-match alerts.</div>`;
  const notifHtml = notifications.length
    ? `<div class="tablewrap"><table><tr><th>Time</th><th>Channel</th><th>To</th><th>Status</th><th>Match</th><th>Message</th><th>Report</th></tr>
        ${notifications.map(n=>`<tr><td>${esc(n.created_at)}</td><td>${esc(n.channel)}</td><td>${esc(n.recipient)}</td>
        <td><span class="pill ${n.status==="sent"?"Verified":n.status==="failed"?"rejected":"pending"}">${esc(n.status || "logged")}</span>${n.error ? `<br><small>${esc(n.error)}</small>` : ""}</td>
        <td>${n.match_id ? `<strong>${esc(n.case_code || "#"+(n.case_id??"?"))}</strong> ${esc(n.case_name||"")} ↔ <strong>${esc(n.sighting_code || "#"+(n.sighting_id??"?"))}</strong><br><small>${n.score ?? "-"}% · <span class="pill ${esc(n.match_status||"")}">${esc(n.match_status||"-")}</span></small>` : "-"}</td>
        <td>${esc(n.message)}</td>
        <td>${n.match_id ? `<a class="btn small" href="#/admin/report/${n.match_id}">View full report</a>` : "-"}</td></tr>`).join("")}</table></div>`
    : `<div class="empty" style="padding:18px 0">No family alerts sent yet.</div>`;
  p.innerHTML = `<h3 style="margin-bottom:10px">Staff Match Alerts</h3>${matchHtml}<h3 style="margin-bottom:10px">Family Notifications Sent</h3>${notifHtml}`;
}

async function reportDetailPage(matchId){
  const me = await api("/me");
  if (!me.user) return loginView();
  $app.innerHTML = `<div class="wrap"><div class="empty">Loading full report…</div></div>`;
  try{
    const {match:m, case:c, sighting:s, history, notifications} = await api("/admin/matches/" + matchId);
    const lvl = m.score >= 75 ? "hi" : m.score >= 50 ? "mid" : "lo";
    $app.innerHTML = `<div class="wrap">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:18px">
        <div>
          <a class="btn ghost small" href="#/admin" id="back-alerts">← Back to Alerts</a>
        </div>
        <div>Signed in as <strong>${esc(me.user)}</strong></div>
      </div>

      <div class="card" style="margin-bottom:20px">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:14px">
          <div>
            <h1>Match Report #${m.id}</h1>
            <div class="facts">Detected: ${esc(m.created_at)} · Cosine distance: ${Number(m.distance).toFixed(4)}
              ${m.reviewed_by ? `<br>Last reviewed by <strong>${esc(m.reviewed_by)}</strong> on ${esc(m.reviewed_at)}` : ""}
            </div>
          </div>
          <div class="score ${lvl}"><b>${m.score}%</b>match<br><span class="pill ${esc(m.status)}">${esc(m.status)}</span></div>
        </div>
        <div class="actions" style="justify-content:flex-start;margin-top:16px">
          ${m.status !== "verified" ? `<button class="btn ok small" data-act="verify">✓ Verify &amp; notify family</button>` : `<button class="btn small" data-act="notify">↻ Resend SMS / Email alert</button>`}
          ${m.status !== "rejected" ? `<button class="btn bad small" data-act="reject">✕ Mark as not the same person</button>` : ""}
          ${m.status !== "pending" ? `<button class="btn ghost small" data-act="reopen">↺ Reopen for review</button>` : ""}
        </div>
      </div>

      <div class="row" style="margin-bottom:20px">
        <div class="card">
          <h2>Missing Person Report</h2>
          ${c ? `
            <img class="thumb" style="max-height:280px;object-fit:cover;margin-bottom:14px" src="${img(c.photo)}" alt="Missing person">
            <div class="facts">
              <strong>${esc(c.code || "#"+c.id)}: ${esc(c.name)}</strong> <span class="pill ${esc(c.status)}">${esc(c.status)}</span><br><br>
              <strong>Age / Gender:</strong> ${c.age ?? "-"} yrs · ${esc(c.gender || "-")}<br>
              <strong>Date missing:</strong> ${esc(c.date_missing || "-")}<br>
              <strong>Last seen location:</strong> ${esc(c.last_seen_location || "-")}<br>
              <strong>Identifying marks:</strong> ${esc(c.marks || "-")}<br>
              <strong>Contact person:</strong> ${esc(c.contact_name || "-")}<br>
              <strong>Phone:</strong> ${esc(c.contact_phone || "-")}<br>
              <strong>Email:</strong> ${esc(c.contact_email || "-")}<br>
              <strong>Registered:</strong> ${esc(c.created_at)}<br>
              <strong>Updated:</strong> ${esc(c.updated_at)}
            </div>
          ` : `<div class="empty">Case record not found.</div>`}
        </div>

        <div class="card">
          <h2>Sighting Report</h2>
          ${s ? `
            <img class="thumb" style="max-height:280px;object-fit:cover;margin-bottom:14px" src="${img(s.photo)}" alt="Sighting">
            <div class="facts">
              <strong>${esc(s.code || "#"+s.id)}</strong><br><br>
              <strong>Location seen:</strong> ${esc(s.location)}<br>
              <strong>Description:</strong> ${esc(s.description || "-")}<br>
              <strong>Reporter name:</strong> ${esc(s.reporter_name || "-")}<br>
              <strong>Reporter contact:</strong> ${esc(s.reporter_contact || "-")}<br>
              <strong>Reported at:</strong> ${esc(s.created_at)}
            </div>
          ` : `<div class="empty">Sighting record not found.</div>`}
        </div>
      </div>

      <div class="row">
        <div class="card">
          <h3>Case Timeline</h3>
          ${history.length ? `<ul class="timeline">${history.map(h=>`<li>${esc(h.event)}<small>${esc(h.actor)} · ${esc(h.created_at)}</small></li>`).join("")}</ul>`
            : `<div class="empty">No history events.</div>`}
        </div>
        <div class="card">
          <h3>Alerts Sent for This Match</h3>
          ${notifications.length ? `<div class="tablewrap"><table><tr><th>Time</th><th>Channel</th><th>To</th><th>Status</th><th>Message</th></tr>
            ${notifications.map(n=>`<tr><td>${esc(n.created_at)}</td><td>${esc(n.channel)}</td><td>${esc(n.recipient)}</td><td><span class="pill ${n.status==="sent"?"Verified":n.status==="failed"?"rejected":"pending"}">${esc(n.status || "logged")}</span></td><td>${esc(n.message)}</td></tr>`).join("")}
            </table></div>` : `<div class="empty">No family alerts sent for this match yet.</div>`}
        </div>
      </div>
    </div>`;

    document.getElementById("back-alerts").onclick = () => { tab = "alerts"; };
    $app.querySelectorAll("[data-act]").forEach(btn => btn.onclick = async () => {
      const act = btn.dataset.act;
      if (act === "verify" && !confirm("Confirm these are the same person and notify the family?")) return;
      if (act === "reject" && !confirm("Mark this match as NOT the same person?")) return;
      btn.disabled = true;
      try{
        await postJSON(`/admin/matches/${matchId}/${act}`);
        toast("Report updated");
        reportDetailPage(matchId);
      }catch(ex){ toast(ex.message); btn.disabled = false; }
    });
  }catch(ex){
    if (ex.status === 401) return loginView();
    $app.innerHTML = `<div class="wrap"><div class="card"><div class="error">${esc(ex.message)}</div><a class="btn ghost small" href="#/admin">Back to Dashboard</a></div></div>`;
  }
}

router();
