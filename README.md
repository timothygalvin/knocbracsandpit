# Knocbrac sites monorepo

Shared deployment/test tooling (`tools/`) + one directory per site
(`sites/<name>/`). See `docs/use_cases.md` for what this repo guarantees
and `CLAUDE.md` for platform context that any agent must read first.

    tools/deploy.py          multi-site pipeline: checks → delta upload → verify
    tools/dev_server.py      local run of the learning platform (+ receiver)
    tools/tests/             automated acceptance tests (stdlib unittest)
    sites/knocbrac/          site.json + the deployable learn/ tree
    sites/agileintegrator/   (future — SFTP/rsync transport to be proven)

Quick start:

    python3 tools/run_tests.py                         # run everything (with tally)
    python3 tools/dev_server.py                        # local platform
    python3 tools/deploy.py knocbrac --check           # pre-flight only
    python3 tools/deploy.py knocbrac --dry-run
    python3 tools/deploy.py knocbrac                   # the real thing

Releases are scripted, not manual. There are TWO independently
deployable artefacts, versioned separately (see CLAUDE.md § Versioning
and docs/use_cases.md UC4/UC5):

    python3 tools/deploy.py knocbrac --content         # course data only
    python3 tools/deploy.py knocbrac --code            # engine/platform only
    python3 tools/deploy.py knocbrac --content --manifest
                                                       # + write a release record

    content  rN      in sites/<site>/learn/courses.json ("version")
    code     semver  in sites/<site>/learn/assets/version.json

Neither path ships a file belonging to the other, so a content release
never touches an engine file and vice versa. `--manifest[=path]` writes
releases/<site>-<artefact>.json: every file with sha256 and size, which
of them the push will actually send, and the sessions contained. Add
`--dry-run` to any of the above to see the file list without sending.

NOTE: deploy only ever uploads. It never deletes, so a file withdrawn
from the deployable set (e.g. learn/README.md, excluded in site.json)
must also be removed on the server by hand.

## Host notes — knocbrac (34sp, old platform)

Migrated here from `sites/knocbrac/learn/README.md`, which is deprecated
and no longer deployed. THIS file is the master.

- **PHP 5.6.36.** The receiver (`learn/api/submit.php`) runs like any other
  page — no CGI setup, no execute bit. `php -l` before shipping it; a parse
  error renders a blank page. Beware: a brew-installed PHP is 8.x, so a
  local lint proves syntax, not 5.6 compatibility — the `php56` pre-flight
  check's token scan is the actual 5.6 gate.
- **Permissions**: directories 755, files 644. Nothing needs to be
  executable. If results saves fail with a permissions error, set
  `learn/results/` to 775.
- **Email + results**: edit `learn/api/config.txt` (plain text) —
  `NOTIFY_EMAIL=` you, `FROM_EMAIL=` ideally a real mailbox on the domain.
  If a save works but reports `"emailed":false`, FROM_EMAIL is not a real
  mailbox on knocbrac.com. Liveness check: open
  `www.knocbrac.com/learn/api/submit.php` — `{"ok":false,"error":"POST only"}`
  means it is alive.
- **robots.txt** belongs at the site root (`httpdocs/robots.txt`), not under
  `learn/` — merge with any existing one.
- **Basic auth** (when 34sp supply the path): uncomment the auth block in
  `learn/.htaccess`, create `.htpasswd` from `learn/.htpasswd.example`
  (CHANGE the example password), and set `AuthUserFile` to its absolute
  server path.
- **Python fallback**: `learn/api/submit.py` works as a CGI if PHP ever goes
  away — chmod 755 and rename `api/htaccess-cgi.optional` to `.htaccess`
  (on some hosts that `.htaccess` itself 500s, which is why it ships
  disabled). The client tries submit.php, then submit.py, then /cgi-bin/.
  It also powers `tools/dev_server.py`, so keep its logic in step with the
  PHP — the state contract is covered by a drift test (UC6.7).
- **Adding a course** is content-only: one folder with `course.json` +
  `content/*.json`, plus one entry in `learn/courses.json`. No engine edits
  (UC1.5 enforces this).
- **Local test** before any deploy: `python3 tools/dev_server.py`, then open
  `http://localhost:8000/learn/`. It serves the site and runs the receiver,
  so the full loop works offline. Opening `index.html` as a `file://` URL
  will NOT work — the pages fetch JSON.
- **TLS**: the host's certificate does not cover www.knocbrac.com, so
  `site_url` is deliberately `http://`. Live checks must use plain HTTP.
- **Progress and work both survive a device change** since code 1.1.0 — see
  CLAUDE.md invariant 5. The old "progress is per-device only" note in the
  deprecated README is wrong and was what lost Jim his work.

Auth: knocbrac deploys over SFTP using the SYSTEM OpenSSH sftp — zero
Python dependencies — to `ftp.knocbrac.com` port 22. (The hostname works;
an older note claiming the IP was required was wrong.) `sftp` runs with
`BatchMode=yes`, so it CANNOT prompt for a password: a key is mandatory.

**The one thing that will waste your afternoon.** This host runs
**OpenSSH 5.3** (verified 11 Oct 2026). It can only sign with `ssh-rsa`
(RSA/SHA-1), and OpenSSH 8.8+ clients disable that algorithm by default —
so a modern client loads your key, silently discards it, and reports
`Permission denied (publickey,password)` exactly as if no key existed.
Look for this pair in `ssh -v` output:

    debug1: loaded pubkey from ~/.ssh/id_rsa: RSA SHA256:...
    debug1: no identity pubkey loaded from ~/.ssh/id_rsa     <-- discarded

The fix is `PubkeyAcceptedAlgorithms=+ssh-rsa`, which site.json passes
through via `ssh_options` so a clean clone works without touching anyone's
`~/.ssh/config`. A new ed25519 or ECDSA key will NOT help — 5.3 predates
both (6.5 and 5.7 respectively). RSA is the only option here.

One-time setup:

    ssh-keygen -t rsa -b 4096      # only if you have no ~/.ssh/id_rsa
    ssh-copy-id -o PubkeyAcceptedAlgorithms=+ssh-rsa -p 22 \
        knocbraccom@ftp.knocbrac.com

If the account is sftp-only (no shell), ssh-copy-id will fail — install
the key by hand instead, since sftp can chmod:

    sftp -o PubkeyAcceptedAlgorithms=+ssh-rsa -P 22 knocbraccom@ftp.knocbrac.com
    sftp> mkdir .ssh
    sftp> put ~/.ssh/id_rsa.pub .ssh/authorized_keys
    sftp> chmod 700 .ssh
    sftp> chmod 600 .ssh/authorized_keys

Readiness test — use sftp, not ssh, because it matches what deploy does
(and still passes if the account has no shell):

    sftp -b /dev/null -o BatchMode=yes \
        -o PubkeyAcceptedAlgorithms=+ssh-rsa \
        -P 22 knocbraccom@ftp.knocbrac.com      # must exit 0

Fallbacks if keys stay broken: transport `sftp` (paramiko + password,
needs `pip install paramiko`), or back to `ftp` with `use_tls: false` —
note FTPS login 530s on this host and plain FTP sends the password in
clear text. See `_notes` in sites/knocbrac/site.json.
