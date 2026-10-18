# CLAUDE.md — Knocbrac Learning platform

Context file for any Claude instance (claude.ai project chats or Claude
Code) working on this codebase. Read this before touching anything.
(Claude Code reads CLAUDE.md automatically; it also works as AGENTS.md.)

## Documentation map (read what your task needs)
- CLAUDE.md (this file) — invariants + schemas. Everyone, always.
- docs/ARCHITECTURE.md — how the pieces fit (diagrams). Platform work.
- docs/CONTENT_GUIDE.md — writing sessions: methodology, style sheets,
  QA gate. Content agents start here after this file.
- Course_Creation_Playbook.md (project files) — designing whole courses
  from diagnostics. Senior/steering work.
- docs/use_cases.md — what the repo guarantees, traced to tests.
- docs/TODO.md — roadmap and ownership.
- docs/handoff/ — ready-to-paste briefs for outsourced work.

## What this is
A self-serve family learning platform at https://www.knocbrac.com/learn/ —
personalised courses for Jim (maths, "The Ascent"), Grace (money & markets,
"Grace & Co."), with more coming (Grace's Spanish; Timothy's Russian).
Static HTML/JS + one small PHP receiver. No database. No build step.
A Chyrp blog lives alongside it in httpdocs — never touch it.

The kids use tablets in a second household with **no adult tech support
available** — everything must be fully self-serve, resilient, and lose no
work. This is the prime directive.

## Hard invariants (violating these has broken production before)
1. **The server runs PHP 5.6.36.** No `??`, no arrow functions, no spread,
   no typed params. Use `array()`, `isset()` ternaries, and the existing
   `kb_get()` helper. Parse errors render as blank pages (display_errors
   off) — always `php -l` before shipping. Do not suggest upgrading PHP
   casually: Chyrp likely depends on 5.6.
2. **All receiver responses are HTTP 200** with `ok:true/false` in the JSON
   body. Error status codes get their bodies swallowed by the host's
   ErrorDocument handling (observed as blank pages). Clients read only the
   JSON.
3. **Session/course ids contain no hyphens** (`w1s1`, `graceco`). The
   progress endpoint parses results filenames
   `course-session-kind-YYYYmmdd-HHMMSS.json` by splitting on hyphens.
4. **Content and delivery are strictly separate.** Engine files (`assets/`,
   `app/`, `api/`) know nothing about any course. A new course = one folder
   + one entry in `courses.json`. If a change requires editing engine files
   per-course, the design is wrong.
5. **Three things persist, all three server-backed since code 1.1.0.**
   *Completion* — localStorage, merged from `submit.php?progress=<course>`
   (derived from saved results filenames). *In-progress work* — the answers
   a child has typed: localStorage first (instant, offline-safe), mirrored
   to `submit.php` with `kind:"state"` on a 2.5s debounce, read back by
   `KB.bestWork()` which takes whichever of device/server has the newer
   `savedAt`. *Submitted results* — one file per finished session in the
   family folder. State lives at `results/state-<course>.json`, named so it
   can never match the progress glob `<course>-*.json` nor the family index.
   Never rely on localStorage alone for anything that must survive a device
   change — that exact gap lost Jim all six sessions of typed work in
   Sept 2026, while the course map still showed ticks. Never lose work: the
   client still falls back to downloading results JSON if the server is
   unreachable. `tools/recover_state.py` rebuilds work from results and
   `tools/seed_state.py` pushes it back into the store.
6. Deployment: `python3 tools/deploy.py knocbrac` over SFTP to the host's
   IP 80.82.113.174 port 22 (old 34sp platform is IP-addressed). Default
   transport "sftpcli" = system OpenSSH sftp, zero Python deps, SSH-key
   auth (setup in README). Fallbacks: "sftp" (paramiko+password), "ftp"
   at ftp.knocbrac.com (site.json _notes).
   site_url is http:// — the host's TLS cert doesn't cover www.knocbrac.com,
   so kids' traffic is unencrypted (accepted for now; revisit with 34sp).
   Old hand-upload traps still apply to any manual work: dotfiles skipped
   by GUI tools, Windows line endings, flattened permissions. The deploy
   verifier replaces manual checking: expect "receiver alive (php 5.6.36)"
   and a matching release.
7. Kids' first names only in code, content, filenames and results. The
   `/learn/` tree is noindexed (headers + meta + robots.txt at site root);
   `.htaccess` basic-auth exists but is commented out pending the
   AuthUserFile path from the host.

## Tree (under httpdocs/)
    learn/
      index.html            hub — renders courses.json
      courses.json          registry: id, student, title, icon, theme
                            (accent/soft/warm/bigText), release marker
      assets/base.css       design tokens; Fredoka display + Nunito body
      assets/shared.js      KB namespace: theming, storage, marking engine,
                            mergedDone(), submitResults() w/ endpoint
                            fallback + local download
      app/course.html       generic course map (?c=id): units, soft-lock,
                            "soon" flag renders locked/Coming soon
      app/session.html      generic player (?c=&s=): practice mode
                            (instant feedback, hints after 2 tries) and
                            checkpoint mode (paged, skip, deferred marking,
                            send-results)
      api/submit.php        THE receiver (PHP 5.6-safe): saves results,
                            rebuilds results/index.html, emails via mail(),
                            GET ?progress= returns completed session ids.
                            Config in api/config.txt (NOTIFY_EMAIL/FROM_EMAIL)
      api/submit.py         dormant Python CGI fallback; also powers local
                            dev (dev_server.py, kept beside learn/)
      results/              the family folder; receiver-owned
      ascent/  graceco/     courses: course.json + content/*.json

## Content schemas (JSON, fetched at runtime)
Registry entry: `{id, student, title, tagline, icon, theme:{accent, soft,
warm, bigText}}`. bigText=true turns on the dyslexia-friendly larger
default (Grace); the Aa toggle exists everywhere regardless.

Course manifest: `{id, map:{heading ("{student}" substituted), blurb},
units:[{title, sessions:[{id, title, time?, kind?:"checkpoint",
soon?:true}]}]}`.

Session content (`kind:"session"`): `{id, kind, tag, title, intro,
blocks:[...], done:{title, html}}` with block types:
- `read` — `{html}`
- `reveal` — `{button, html}` hidden until tapped (the surprise pattern)
- `q` — `{id, prompt, hint?, parts:[{id, label, type:"numeric"|"text",
  accept:[...], range?:[lo,hi], pctOk?:true}]}` — instant-checked
- `summit` — `{html}` end-of-session discussion prompt (dinner-table)

Checkpoint content (`kind:"checkpoint"`): `{id, kind, title,
sections:[{id, name, intro?, questions:[{id, level, prompt,
parts:[...same as above, plus type:"text" without accept → "review"]}]}]}`
— paged, skippable, marked at the end, submitted to the family folder.

Marking engine (shared.js `KB.markPart`): numeric answers are normalised
(strips £/$/€, %, units, fractions "3/4", mixed numbers "1 3/8"); `pctOk`
lets bare "50" mean 50% on probability parts (Grace's rule — always set it
on probability questions). Text `accept` matching is lower-cased,
space-stripped, ×/* → x. Cyrillic and accented text pass through fine.

## Design language & pedagogy (keep these, they're the product)
- Per-course theme via CSS variables; one design system, many worlds.
- Sessions are one sitting (Grace ~35 min, Jim ~45); short sentences and
  one idea per line in Grace's content.
- Patterns with names, used everywhere: the **rematch** (diagnostic misses
  return as boss questions), the **reveal** (learner forces the rule from
  a pattern before it's stated), the **summit** (every session ends with
  something to discuss with a human — the conversation is the engine).
- Tone: warm, capable, never patronising. Skips are information.

## Repo layout, testing & release
The codebase now lives in a git monorepo:
    tools/deploy.py        multi-site pipeline (checks → delta → verify);
                           transports: ftp (live), local (for tests and for
                           proving new transports), sftp (documented stub)
    tools/dev_server.py    local platform (+ receiver) at localhost:8000
    tools/tests/           acceptance suite — run before ANY change ships:
                           python3 tools/run_tests.py  (prints a tally)
    sites/knocbrac/        site.json (committed; no secrets) + learn/ tree
    docs/use_cases.md      the three use cases; every acceptance criterion
                           names its automated test — keep that mapping
                           intact when adding features
- Deploy: python3 tools/deploy.py knocbrac [--check|--dry-run|--all|--init]
  Password via env KB_DEPLOY_PASSWORD or prompt. learn/results/ is deploy-
  protected: only --init ships the placeholder index.
- Split deploy paths (site.json `artefacts`, UC4): `--content` ships course
  data only (courses.json, */course.json, */content/*.json), `--code` ships
  the engine only. Content is safe to ship ahead of code — it uses no engine
  feature the live engine lacks. A split deploy keeps the other artefact's
  entries in the upload manifest, so it never triggers a full re-upload.
  The `coverage` check blocks any file belonging to neither path.
  `--manifest[=path]` writes a release record (files + sha256 + what this
  push ships + sessions) to releases/<site>-<artefact>.json. The two paths
  are symmetric: neither ships a file belonging to the other.
- New transports (e.g. rsync for agileintegrator) must pass the pipeline
  test suite with themselves substituted for LocalTransport (byte-identity
  = the proof) before earning a site.json entry.
- Versioning: TWO artefacts, two version lines, versioned separately. Same
  scheme for every site (agileintegrator.com included).
  * CODE — semantic, in `learn/assets/version.json` (`{"version":"1.0.0"}`),
    code-owned so an engine bump never edits a content file. MAJOR is the
    breaking boundary: minor and patch can NEVER invalidate content.
    Bumping it means editing the ?v= on the asset includes in the three app
    pages to match — the "cache" check enforces that, so a mismatch cannot
    deploy. Supersedes the old r1–r6 asset counter (r6 == 1.0.0).
  * CONTENT — a simple `rN` counter in courses.json (`version`), plus
    `requires_code` naming the code MAJOR it was authored against. Content
    has no dependents of its own, so one number does the work of three.
  The "compat" check enforces both formats and the MAJOR rule. The verifier
  probes each artefact's own marker (site.json `verify` is a per-artefact
  map). Assessments carry their own version.
  There is deliberately NO combined package version: the old packaged "rN"
  artefact (r12 was the last) is retired in favour of the two above.

## Current state / roadmap
- Live (verified against the server 27 Sep 2026, all 28 files sha-matched):
  content r6 — ascent AND graceco both complete through w2s3, no "soon"
  flags left in Unit 1 or 2; receiver alive (php 5.6.36), email + progress
  sync working. Note: fetching `.htaccess`/`.ht*` returns 404 and
  `submit.php`/`.py` return output rather than source — that is Apache
  behaviour, not missing files; don't diagnose it as a broken deploy.
- Pending deploys: code 1.0.0 (version.json + the ?v= re-key, 4 files via
  `--code`) and the content marker rename (courses.json, 1 file via
  `--content`). Independent of each other — that is the point of the split.
- Next: remaining Unit 1 sessions, then Unit 2 for both; checkpoint 1
  after each Unit 2; Grace's Spanish course (new folder, likely
  `gracees`); Timothy's Russian (adult course — see
  Course_Creation_Playbook.md, language addendum).
- Standalone artefacts from the diagnostic phase (Maths_Ascent_Jim_v4.html,
  Money_Makers_Grace_v2.html, both course-plan PDFs, results JSONs) live in
  the project files — the diagnostics are historical; the platform is
  canonical now.
