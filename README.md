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

Auth: knocbrac deploys over SFTP to the host's IP (old platform rule)
using the SYSTEM OpenSSH sftp — zero Python dependencies. One-time setup,
an SSH key (also kills the password prompt forever):

    ssh-keygen -t ed25519          # accept defaults; passphrase optional
    ssh-copy-id -p 22 knocbraccom@80.82.113.174
    # (if ssh-copy-id is missing:)
    # cat ~/.ssh/id_ed25519.pub | ssh -p 22 knocbraccom@80.82.113.174 \
    #     "mkdir -p .ssh && cat >> .ssh/authorized_keys"

Test it:  ssh -p 22 knocbraccom@80.82.113.174 true   (should not ask for
a password). If the old host refuses key auth entirely, fall back to
transport "sftp" (paramiko + password) or "ftp" — see _notes in
sites/knocbrac/site.json.
