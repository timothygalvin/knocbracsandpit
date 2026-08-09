# Architecture — Knocbrac Learning

Companion to CLAUDE.md (invariants, schemas) and README.md (quickstart).
This file explains how the pieces fit. Diagrams are ASCII on purpose:
readable in any terminal, diffable in git.

## 1. System context

    ┌──────────────────┐  http (port 80)   ┌───────────────────────────────┐
    │  Twins' tablets  │◄─────────────────►│  34sp shared host (PHP 5.6)   │
    │  (2nd household, │   pages, JSON,    │  www.knocbrac.com             │
    │  browser only)   │   results POSTs   │  httpdocs/                    │
    └──────────────────┘                   │   ├─ (chyrp blog — untouched) │
                                           │   ├─ robots.txt               │
    ┌──────────────────┐   completion      │   └─ learn/  ◄────────────┐   │
    │  Timothy         │◄──────────────────│        the platform       │   │
    │  (email, browser)│   emails, results │                           │   │
    └────────┬─────────┘   folder, logtail └───────────────────────────┼───┘
             │                                                         │
             │ git + deploy.py (FTP/SFTP)     ┌────────────────────────┴──┐
             └───────────────────────────────►│  knocbracsandpit repo     │
                                              │  tools/ + sites/ + docs/  │
               agents produce content ───────►│  (content PRs land here)  │
                                              └───────────────────────────┘

Prime directive: the tablets have NO adult tech support available.
Everything must be self-serve, resilient, and lose no work.

## 2. The platform (inside learn/)

    ENGINE (shared, agents don't touch)        CONTENT (per course, agents add)
    ┌─────────────────────────────────┐        ┌──────────────────────────────┐
    │ index.html      hub             │ reads  │ courses.json   registry      │
    │ app/course.html course map      │◄───────│ <course>/course.json manifest│
    │ app/session.html player         │        │ <course>/content/*.json      │
    │ assets/base.css design tokens   │        │   sessions & checkpoints     │
    │ assets/shared.js KB runtime:    │        └──────────────────────────────┘
    │   theming · storage · marking · │
    │   mergedDone · submitResults ·  │        Adding a course = one folder
    │   error beacon                  │        + one registry entry. If a task
    │ api/submit.php  THE receiver    │        needs an engine edit, the task
    │ api/submit.py   dormant fallback│        is wrong.
    │ results/        family folder   │
    └─────────────────────────────────┘

## 3. Data flow: finishing a session

    tablet                         server (submit.php)              Timothy
    ──────                         ───────────────────              ───────
    Finish ✓ pressed
      │ markDone → localStorage
      │ POST results JSON ───────► validate (200-only responses)
      │                            save results/<c>-<s>-<kind>-<ts>.json
      │                            rebuild results/index.html
      │                            append receiver.log.php  ───────► logtail view
      │                            mail() notification      ───────► inbox
      │ ◄──────── {ok, file, emailed}
      │ toast "saved to family folder"
      │ (on any failure: results JSON downloads locally — nothing lost;
      │  beacon logs the failure server-side)

    Later, any device:
      course map → GET ?progress=<course> → completed session ids
      (derived from results filenames) merged into local progress.
      This is why session ids must never contain hyphens.

## 4. Deploy pipeline (tools/deploy.py)

    edit ─► run_tests.py ─► deploy.py <site> ─► live
             29 tests        │
                             ├─ PRE-FLIGHT (per-site named checks)
                             │    json · php56 · ids · manifests ·
                             │    schema · cache
                             ├─ DELTA (sha256 manifest; changed files only;
                             │    learn/results/* protected)
                             ├─ TRANSPORT (per-site; four-method contract)
                             │    ftp (live) · sftpcli (proven, key-auth)
                             │    sftp/paramiko (proven) · local (tests)
                             └─ VERIFY (live probes: receiver alive,
                                  release matches local)

    New transports are PROVEN before use: the pipeline test suite runs
    through them against a fake endpoint, asserting byte-identity
    (docs/use_cases.md, UC3.4).

## 5. Component reference

| Piece | Lives at | Owner |
|---|---|---|
| Engine pages & runtime | learn/{index.html,app/,assets/} | platform work only |
| Receiver | learn/api/submit.php (+config.txt) | platform work only |
| Course content | learn/<course>/ | content agents |
| Registry | learn/courses.json | one line per new course |
| Deploy/tests | tools/ | platform work only |
| Docs | docs/, CLAUDE.md, README.md | everyone keeps current |

## 6. Known constraints (why things are the way they are)
- PHP 5.6.36 on the host → array() syntax, kb_get(), no ?? (see CLAUDE.md
  invariant 1 — this one has burned us).
- All receiver responses HTTP 200 — error statuses get blanked by the
  host's ErrorDocument handling.
- http:// not https:// — the host cert doesn't cover www.knocbrac.com.
  Accepted for now; on the TODO.
- Old platform is IP-addressed for SFTP; FTP(S) at ftp.knocbrac.com is
  the currently-active transport.
- Browser caching bit us once (stale shared.js vs fresh page): assets are
  version-locked to the release (?v=rN) and no-cache headers are set; the
  "cache" pre-flight check makes a mismatch undeployable.
