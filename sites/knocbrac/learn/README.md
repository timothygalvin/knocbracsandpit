# DEPRECATED — see the repo-root README.md

This file is no longer maintained and is no longer deployed (it is
excluded in `sites/knocbrac/site.json`).

**Master document: `README.md` at the repo root**, section
"Host notes — knocbrac (34sp, old platform)". Everything still useful
here — PHP version, permissions, email/results config, robots.txt, the
basic-auth block, the Python CGI fallback, local testing, TLS — was
migrated there.

Why it was retired:

- It described a manual upload procedure that `tools/deploy.py`
  superseded (`--content` / `--code`; see the root README and CLAUDE.md).
- It was being served publicly at `/learn/README.md` while containing the
  `.htpasswd` example password and the receiver's setup detail.
- Its "progress lives in each tablet's browser storage" note became
  actively wrong with code 1.1.0, which mirrors both completion and
  in-progress work server-side (CLAUDE.md invariant 5). That stale
  assumption is what cost Jim a unit's worth of typed answers.

If a copy of the old text is still on the live server, delete it by hand:
deploy only ever uploads.
