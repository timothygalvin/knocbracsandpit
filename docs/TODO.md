# TODO / Roadmap — Knocbrac Learning

Priority-ordered within sections. (i) = infrastructure, (c) = content,
(o) = ops. Owner column: T = Timothy, F = Fable/senior agent,
A = content agent.

## Now / next
- (c/A) Jim Unit 2 remainder: w2s2 The Position Machine, w2s3 Summit
  Puzzle: The Staircase — FIRST OUTSOURCED UNIT, see docs/handoff/
- (c/A) Grace Unit 2 remainder: w2s2 The Margin, w2s3 Market Story:
  Losing Money on Purpose — same handoff
- (c/F) Checkpoint 1 for both (after Unit 2, per course plans):
  ascent/graceco checkpoint content using kind:"checkpoint"; reuses the
  diagnostic-style paged engine; results steer Unit 3
- (o/T) Confirm w1s3 finishes reached the server (emails/results/logtail)
  → closes the "finish doesn't register" question

## Platform features
- (i) Grown-up dashboard page: per-child progress + latest results +
  logtail, one URL for Timothy (currently: results/index.html + logtail)
- (i) .htaccess auth: get AuthUserFile path from 34sp, enable, set real
  password (kids type once per device)
- (i) TLS: ask 34sp about a cert covering www.knocbrac.com (Let's
  Encrypt?); then site_url back to https and revisit cache headers
- (i) Receiver: daily digest option (one email/day instead of per-session)
  if notification volume grows
- (i) Session player: optional per-question audio (helps Grace; needs
  asset hosting thought — keep static)

## Courses pipeline
- (c/F) Jim Units 3–5 plans → (c/A) session production per unit
- (c/F) Grace Units 3–5 likewise
- (c/F) Grace's Spanish course (gracees/): Step 0 + diagnostic per
  Playbook language addendum
- (c/F) Timothy's Russian: kickoff prompt exists
  (Russian_Kickoff_Prompt.md) — written diagnostic + oral protocol
- (c/F) Jim Course 2 concept: stats re-entered through biology/energy
  systems (per his plan's deferral of Data)

## Tooling & repo
- (i) deploy.py: split transports into tools/transports/ when the 4th
  transport lands (single-file was right for 1–2)
- (i) rsync-over-ssh transport for agileintegrator (must pass the proof
  ritual, UC3.4); then sites/agileintegrator/site.json
- (i) knocbrac → sftpcli transport once T does the keygen (README steps)
- (i) CI: run run_tests.py on every push (GitHub Actions if the repo is
  on GitHub; php-cgi + node in the runner so nothing skips)
- (i) Pre-flight idea: link-check html for dead internal refs
- (i) A "solutions render" tool: extract _working fields into a reviewer
  PDF per unit (makes content review fast)

## Other surfaces / interfaces (the expansion Timothy flagged)
- agileintegrator.com: second site on the new platform — decide what
  lives there; pipeline is ready, transport needs the proof ritual
- Possible: read-only progress page shareable to the twins' mother
  (results without admin) — sensitive, design carefully, T decides
- Possible: PWA wrapper / homescreen icons for the tablets (a manifest
  + icons; no app store) — cheap win for "feels like an app"
- Skill/plugin: distil CLAUDE.md + Playbook + Content Guide into a
  reusable course-production skill once the outsourced unit proves the
  docs are sufficient

## Ops hygiene
- (o) Rotate/backup: pull results/ folder into the repo monthly?
  (gitignored dir or a separate archive — decide)
- (o) Log review habit: logtail after each deploy + weekly
- (o) 34sp contact list: cert, AuthUserFile path, PHP version options
  (upgrade only after Chyrp compatibility is checked)
