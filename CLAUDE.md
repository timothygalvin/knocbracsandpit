# CLAUDE.md — Knocbrac Learning platform

Context file for any Claude instance (claude.ai project chats or Claude
Code) working on this codebase. Read this before touching anything.
(Claude Code reads CLAUDE.md automatically; it also works as AGENTS.md.)

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
5. Progress lives in localStorage per device; **completion** additionally
   syncs via the server (`submit.php?progress=<course>` derived from saved
   results). Never rely on localStorage alone for anything that must
   survive a device change; never lose work — the client falls back to
   downloading results JSON if the server is unreachable.
6. Deployment is hand-uploaded to 34sp (Plesk-ish, `httpdocs/`). Dotfiles
   are silently skipped by some upload tools; Windows editing converts line
   endings; FTP flattens permissions. After any deploy, verify:
   `/learn/api/submit.php` in a browser → `{"ok":false,...,"status":
   "receiver alive (php 5.6.36)..."}`.
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
                           python3 -m unittest discover -s tools/tests -v
    sites/knocbrac/        site.json (committed; no secrets) + learn/ tree
    docs/use_cases.md      the three use cases; every acceptance criterion
                           names its automated test — keep that mapping
                           intact when adding features
- Deploy: python3 tools/deploy.py knocbrac [--check|--dry-run|--all|--init]
  Password via env KB_DEPLOY_PASSWORD or prompt. learn/results/ is deploy-
  protected: only --init ships the placeholder index.
- New transports (e.g. rsync for agileintegrator) must pass the pipeline
  test suite with themselves substituted for LocalTransport (byte-identity
  = the proof) before earning a site.json entry.
- Releases: bump `release` in courses.json; the post-deploy verifier
  compares it against the live site. Assessments carry their own version.

## Current state / roadmap
- Live: framework r4; ascent w1s1–w1s2 (+w1s3 "soon"); graceco w1s1–w1s2
  (+w1s3 "soon"); receiver working incl. email + progress sync.
- Next: remaining Unit 1 sessions, then Unit 2 for both; checkpoint 1
  after each Unit 2; Grace's Spanish course (new folder, likely
  `gracees`); Timothy's Russian (adult course — see
  Course_Creation_Playbook.md, language addendum).
- Standalone artefacts from the diagnostic phase (Maths_Ascent_Jim_v4.html,
  Money_Makers_Grace_v2.html, both course-plan PDFs, results JSONs) live in
  the project files — the diagnostics are historical; the platform is
  canonical now.
