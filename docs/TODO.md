# TODO / Roadmap — Knocbrac Learning

Priority-ordered within sections. (i) = infrastructure, (c) = content,
(o) = ops. Owner column: T = Timothy, F = Fable/senior agent,
A = content agent.

## Blocking before the next code deploy
- (o/T) **`php -l` submit.php somewhere with PHP before shipping code 1.1.0.**
  No PHP or container runtime exists on this machine, so the state endpoint
  in submit.php is UNLINTED and all 10 php-cgi receiver tests skip. A parse
  error renders blank pages (invariant 1). The logic is verified via the
  Python twin (UC6) and the file is structurally balanced + PHP5.6-token
  clean, but that is not a substitute. `brew install php` locally, or lint a
  staged copy on the host over ssh, then run run_tests.py again and expect
  10 more passes.
- (o/T) Delete the live `/learn/README.md` by hand. It is now excluded from
  deployment (it leaked the .htpasswd example password `lemonade` and the
  receiver setup), but deploy only uploads — it never deletes.

## Now / next
- (c/A) Jim Unit 2 remainder: w2s2 The Position Machine, w2s3 Summit
  Puzzle: The Staircase — FIRST OUTSOURCED UNIT, see docs/handoff/
- (c/A) Grace Unit 2 remainder: w2s2 The Margin, w2s3 Market Story:
  Losing Money on Purpose — same handoff
- (c/F) Checkpoint 1 for both (after Unit 2, per course plans):
  ascent/graceco checkpoint content using kind:"checkpoint"; reuses the
  diagnostic-style paged engine; results steer Unit 3
- (o/T) Confirm w1s3 finishes reached the server (emails/results/logtail)
  → closes the "finish doesn't register" question. NOTE: 32 results files
  exist on the server as of 10 Oct 2026, including six separate w1s3
  submissions for ascent — finishes ARE registering, possibly more than
  once per session.
- (c/F) **ascent w2s2 lost Jim halfway.** His submitted result shows m1 and
  m2 correct, then m3–m6 entirely BLANK with 1–2 check presses on empty
  boxes — and 14 minutes later he completed w2s3 fully (12 answers, 9/12).
  So it is not fatigue or lost work: the reverse-machine half of The
  Position Machine (from the "Run the machine backwards" reveal onward)
  stopped him dead. Needs a rewrite of m3 onward, or splitting the session.
  Steering call — the diagnostic data is in recovered/ascent-w2s2.json.

## Versioning & release paths
- DONE (27 Sep 2026, approved by T): two artefacts, two version lines.
  Code semver in learn/assets/version.json (1.0.0, MAJOR = breaking
  boundary), content `rN` + `requires_code` in courses.json, `compat`
  check enforcing both, per-artefact verify probes, packaged "rN" retired.
  See CLAUDE.md § Repo layout and docs/use_cases.md UC5.
- (o/T) Ship the two pending releases: `--code` (4 files: version.json +
  the ?v= re-key) and `--content` (1 file: the marker rename). Separately,
  to exercise the split for real.
- (i) Second site: give agileintegrator.com its own `artefacts` globs +
  version files under the same scheme once its transport is proven.

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
