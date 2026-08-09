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

    python3 -m unittest discover -s tools/tests -v     # run everything
    python3 tools/dev_server.py                        # local platform
    python3 tools/deploy.py knocbrac --check           # pre-flight only
    python3 tools/deploy.py knocbrac --dry-run
    python3 tools/deploy.py knocbrac                   # the real thing

FTP password: env var KB_DEPLOY_PASSWORD, or you are prompted.
