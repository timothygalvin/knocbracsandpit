/* Knocbrac Learning — shared runtime. Content lives in course folders; this never changes per course. */
const KB = {
  root: (() => {            // absolute-ish path to /learn/ regardless of page depth
    const p = location.pathname;
    const i = p.lastIndexOf("/app/");
    return i >= 0 ? p.slice(0, i + 1) : p.replace(/[^/]*$/, "");
  })(),
  qs: k => new URLSearchParams(location.search).get(k),
  el: s => document.querySelector(s),

  beacon(msg) {   /* fire-and-forget diagnostics to the receiver log */
    try {
      fetch(KB.root + "api/submit.php", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ clientlog: String(msg).slice(0, 480) })
      }).catch(() => {});
    } catch (e) { /* never let diagnostics break the app */ }
  },

  toast(msg, ms = 2600) {
    let t = KB.el("#toast");
    if (!t) { t = document.createElement("div"); t.id = "toast"; t.className = "toast"; document.body.appendChild(t); }
    t.textContent = msg; t.classList.add("show");
    clearTimeout(KB._tt); KB._tt = setTimeout(() => t.classList.remove("show"), ms);
  },

  async json(path) {
    const r = await fetch(path, { cache: "no-store" });
    if (!r.ok) throw new Error(path + " → " + r.status);
    return r.json();
  },
  async registry() { return KB.json(KB.root + "courses.json"); },
  async course(id) { return KB.json(KB.root + id + "/course.json"); },

  applyTheme(theme) {
    const r = document.documentElement.style;
    if (theme.accent) r.setProperty("--accent", theme.accent);
    if (theme.soft) r.setProperty("--soft", theme.soft);
    if (theme.warm) r.setProperty("--warm", theme.warm);
    if (theme.bigText) document.body.classList.add("big");
  },
  mountTextToggle() {
    const b = document.createElement("button");
    b.className = "textsize"; b.textContent = "Aa ↕"; b.setAttribute("aria-label", "Toggle bigger text");
    b.onclick = () => {
      document.body.classList.toggle("big");
      localStorage.setItem("kb:bigtext", document.body.classList.contains("big") ? "1" : "0");
    };

/* uncaught errors on the tablets report themselves to the family log */
window.addEventListener("error", e =>
  KB.beacon("JS error: " + e.message + " @ " + (e.filename || "?") + ":" + (e.lineno || "?") +
            " on " + location.pathname + location.search));
window.addEventListener("unhandledrejection", e =>
  KB.beacon("Unhandled rejection: " + String(e.reason).slice(0, 200) +
            " on " + location.pathname + location.search));
    document.body.appendChild(b);
    if (localStorage.getItem("kb:bigtext") === "1") document.body.classList.add("big");
  },

  /* ---- progress (localStorage; per-course) ---- */
  doneMap(course) { try { return JSON.parse(localStorage.getItem("kb:" + course + ":done") || "{}"); } catch { return {}; } },
  markDone(course, session) {
    const m = KB.doneMap(course); m[session] = new Date().toISOString();
    localStorage.setItem("kb:" + course + ":done", JSON.stringify(m));
  },
  saveWork(course, session, state) {
    /* local copy first: instant, and the only copy that works offline */
    state.savedAt = new Date().toISOString();
    localStorage.setItem("kb:" + course + ":" + session, JSON.stringify(state));
    KB.pushWork(course, session, state);          /* then mirror to the server */
  },
  /* ---- in-progress work mirrored server-side (survives a device change) ----
     A child's typed answers used to live only in this tablet's storage, so
     clearing browser data lost everything while the course map still showed
     ticks (those sync from the results folder). The push is debounced and
     entirely failure-tolerant: if it never lands, localStorage still has the
     work and nothing is worse than before. */
  _pushTimers: {},
  pushWork(course, session, state) {
    const k = course + ":" + session;
    clearTimeout(KB._pushTimers[k]);
    KB._pushTimers[k] = setTimeout(function () {
      fetch(KB.root + "api/submit.php", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kind: "state", course: course,
                               session: session, work: state })
      }).catch(function () { /* offline: the local copy stands */ });
    }, 2500);
  },
  async pullWork(course) {
    try {
      const r = await fetch(KB.root + "api/submit.php?state=" +
                            encodeURIComponent(course), { cache: "no-store" });
      const j = await r.json();
      return (j.ok && j.sessions) ? j.sessions : {};
    } catch (e) { return {}; }
  },
  /* the newer of (this device, the server) — server wins only if it is
     genuinely newer, so work typed offline is never thrown away */
  async bestWork(course, session) {
    const local = KB.loadWork(course, session);
    let remote = null;
    try { remote = (await KB.pullWork(course))[session] || null; } catch (e) { }
    if (!remote) return local;
    if (!local) return remote;
    /* work saved by the pre-1.1.0 engine carries no savedAt, so it would
       lose to ANY server copy on the first load after an upgrade. Never
       lose work: with no stamp to compare, keep whichever side has more
       typed answers. */
    if (!local.savedAt) {
      const n = o => Object.keys((o && o.answers) || {}).length;
      return n(remote) > n(local) ? remote : local;
    }
    return (String(remote.savedAt || "") > String(local.savedAt || ""))
      ? remote : local;
  },
  /* completion synced from the server's results folder, merged into local */
  async mergedDone(course) {
    try {
      const r = await fetch(KB.root + "api/submit.php?progress=" + encodeURIComponent(course), { cache: "no-store" });
      const j = await r.json();
      if (j.ok && Array.isArray(j.done)) {
        const local = KB.doneMap(course);
        for (const id of j.done) if (!local[id]) KB.markDone(course, id);
      }
    } catch (e) { /* offline or old receiver: local only */ }
    return KB.doneMap(course);
  },
  loadWork(course, session) { try { return JSON.parse(localStorage.getItem("kb:" + course + ":" + session) || "null"); } catch { return null; } },

  /* ---- marking engine (ported from the diagnostic apps) ---- */
  parseNumeric(raw) {
    if (raw == null) return null;
    let s = String(raw).trim().toLowerCase()
      /* every dash a keyboard or a copy-paste can produce becomes the plain
         hyphen parseFloat understands. Our own prompts print the TRUE minus
         (U+2212), so a child copying the sign out of the question used to be
         marked wrong on every negative answer — 16 parts across 8 sessions. */
      .replace(/[−‒–—―⁃﹣－]/g, "-")
      .replace(/[£$€,]/g, "").replace(/(cm2|cm²|cm|kg|g|ml|degrees|deg|°|p\b)/g, "").trim();
    if (s === "") return null;
    let pct = false;
    if (s.endsWith("%")) { pct = true; s = s.slice(0, -1).trim(); }
    let m = s.match(/^(-?\d+)\s+(\d+)\s*\/\s*(\d+)$/);
    if (m) { const w = +m[1]; return (Math.abs(w) + (+m[2]) / (+m[3])) * (w < 0 ? -1 : 1); }
    m = s.match(/^(-?\d+(?:\.\d+)?)\s*\/\s*(-?\d+(?:\.\d+)?)$/);
    if (m && +m[2] !== 0) return (+m[1]) / (+m[2]);
    const v = parseFloat(s.replace(/\s/g, ""));
    if (isNaN(v)) return null;
    return pct ? v / 100 : v;
  },
  normText(raw) {
    return String(raw || "").toLowerCase().replace(/[\s()]/g, "").replace(/×|\*|·/g, "x").replace(/xn/g, "nx");
  },
  markPart(part, raw) {
    if (raw == null || String(raw).trim() === "") return "blank";
    if (part.type === "numeric") {
      let v = KB.parseNumeric(raw);
      if (v == null) return "review";
      const hit = x => part.range
        ? (x >= part.range[0] - 1e-9 && x <= part.range[1] + 1e-9)
        : part.accept.some(a => Math.abs(x - a) < 1e-6);
      if (hit(v)) return "correct";
      /* probability leniency: bare "50" meaning 50% (Grace's rule) */
      if (part.pctOk && v > 1 && v <= 100 && hit(v / 100)) return "correct";
      return "incorrect";
    }
    if (part.accept) return part.accept.some(a => KB.normText(a) === KB.normText(raw)) ? "correct" : "review";
    return "review";
  },

  /* ---- results to the family folder (server), with local fallback ---- */
  async submitResults(payload) {
    /* try the PHP receiver first (runs like any other page on the host),
       then the CGI variants — whichever the host allows; no config needed */
    const endpoints = [
      KB.root + "api/submit.php",
      KB.root + "api/submit.py",
      "/cgi-bin/submit.cgi",
      "/cgi-bin/submit.py"
    ];
    let err = null;
    for (const url of endpoints) {
      try {
        const r = await fetch(url, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const j = await r.json();          /* throws on HTML error pages */
        if (!j.ok) throw new Error(j.error || "server said no");
        return { ok: true, file: j.file, emailed: j.emailed };
      } catch (e) { err = e; }
    }
    KB.beacon("submitResults exhausted all endpoints on " + location.pathname +
              " — last error: " + String(err));
    {
      /* offline / server issue: download instead so nothing is lost */
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = (payload.course || "results") + "-" + (payload.kind || "session") + "-" +
        new Date().toISOString().replace(/[:T]/g, "-").slice(0, 19) + ".json";
      a.click(); URL.revokeObjectURL(a.href);
      return { ok: false, error: String(err) };
    }
  }
};
