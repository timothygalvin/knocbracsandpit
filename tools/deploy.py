#!/usr/bin/env python3
"""Multi-site test + deploy pipeline (repo layout).

Sites are discovered from sites/<name>/site.json. Paths inside a site.json
(sources, exclude, matches_local) are relative to that site's directory.

    python3 tools/deploy.py knocbrac --check      pre-flight only
    python3 tools/deploy.py knocbrac --dry-run    show what would upload
    python3 tools/deploy.py knocbrac              check -> upload delta -> verify
    python3 tools/deploy.py knocbrac --all        ignore manifest, send everything
    python3 tools/deploy.py knocbrac --all --init also send protected placeholders

Transports: ftp (live), local (deploys to a directory — used by the test
suite and for proving new transports), sftp (documented stub).
Password: env KB_DEPLOY_PASSWORD or interactive prompt; never required in git.
Per-site upload state: .deploy-manifest-<site>.json at the repo root
(gitignored).
"""
import sys, os, json, re, hashlib, getpass, subprocess, fnmatch, shutil
from ftplib import FTP, FTP_TLS, error_perm

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT  = os.path.dirname(TOOLS)           # repo root
SITES = os.path.join(ROOT, "sites")

def say(msg): print(msg, flush=True)
class DeployError(Exception): pass

# ============================================================ named checks
# A check receives (site, base_dir) and returns a list of problem strings.

def _walk(site, base):
    out = []
    for src in site.get("sources", []):
        top = os.path.join(base, src)
        if not os.path.isdir(top):
            raise DeployError("source folder missing: %s" % src)
        for dirpath, _dirs, files in os.walk(top):
            for f in files:
                out.append(os.path.join(dirpath, f))
    return sorted(out)

def check_json(site, base):
    probs = []
    for p in _walk(site, base):
        if p.endswith(".json"):
            try:
                json.load(open(p, encoding="utf-8"))
            except Exception as e:
                probs.append("invalid JSON: %s — %s" % (os.path.relpath(p, base), e))
    return probs

PHP7_TOKENS = [
    (r"\?\?", "null-coalescing ?? (PHP 7+; this host runs PHP 5.6)"),
    (r"\bfn\s*\(", "arrow function fn( (PHP 7.4+)"),
]
def check_php56(site, base):
    probs = []
    for p in _walk(site, base):
        if p.endswith(".php"):
            src = open(p, encoding="utf-8", errors="replace").read()
            for pat, why in PHP7_TOKENS:
                if re.search(pat, src):
                    probs.append("%s contains %s" % (os.path.relpath(p, base), why))
            try:
                r = subprocess.run(["php", "-l", p], capture_output=True, timeout=20)
                if r.returncode != 0:
                    probs.append("php -l failed for %s:\n%s"
                                 % (os.path.relpath(p, base), r.stdout.decode()))
            except FileNotFoundError:
                pass
    return probs

def check_ids(site, base):
    probs = []
    for cj in [p for p in _walk(site, base) if os.path.basename(p) == "course.json"]:
        m = json.load(open(cj, encoding="utf-8"))
        if "-" in m.get("id", ""):
            probs.append("course id contains a hyphen: %s" % m.get("id"))
        for u in m.get("units", []):
            for s in u.get("sessions", []):
                if "-" in s.get("id", ""):
                    probs.append("session id contains a hyphen: %s/%s"
                                 % (m.get("id"), s["id"]))
    return probs

def check_manifests(site, base):
    probs = []
    for cj in [p for p in _walk(site, base) if os.path.basename(p) == "course.json"]:
        m = json.load(open(cj, encoding="utf-8"))
        cdir = os.path.dirname(cj)
        for u in m.get("units", []):
            for s in u.get("sessions", []):
                if not s.get("soon"):
                    cf = os.path.join(cdir, "content", s["id"] + ".json")
                    if not os.path.exists(cf):
                        probs.append('%s lists %s but content/%s.json is missing '
                                     '(mark it "soon": true?)'
                                     % (os.path.relpath(cj, base), s["id"], s["id"]))
    return probs

SESSION_BLOCKS = {"read", "reveal", "q", "summit"}
PART_TYPES = {"numeric", "text"}
def check_schema(site, base):
    """Session/checkpoint content only uses structures the engine renders."""
    probs = []
    for p in _walk(site, base):
        if not (os.sep + "content" + os.sep in p and p.endswith(".json")):
            continue
        rp = os.path.relpath(p, base)
        try:
            doc = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue  # check_json reports parse failures
        kind = doc.get("kind")
        if kind == "session":
            for b in doc.get("blocks", []):
                t = b.get("type")
                if t not in SESSION_BLOCKS:
                    probs.append("%s: unknown block type %r" % (rp, t))
                if t == "q":
                    for part in b.get("parts", []):
                        if part.get("type") not in PART_TYPES:
                            probs.append("%s: q %s part %s has unknown type %r"
                                         % (rp, b.get("id"), part.get("id"), part.get("type")))
                        if part.get("type") == "numeric" and not (
                                part.get("accept") or part.get("range")):
                            probs.append("%s: numeric part %s.%s has no accept/range"
                                         % (rp, b.get("id"), part.get("id")))
        elif kind == "checkpoint":
            for sec in doc.get("sections", []):
                for q in sec.get("questions", []):
                    for part in q.get("parts", []):
                        if part.get("type") not in PART_TYPES:
                            probs.append("%s: %s part %s unknown type %r"
                                         % (rp, q.get("id"), part.get("id"), part.get("type")))
        else:
            probs.append("%s: kind must be 'session' or 'checkpoint', got %r" % (rp, kind))
    return probs

CHECKS = {"json": check_json, "php56": check_php56, "ids": check_ids,
          "manifests": check_manifests, "schema": check_schema}

# ============================================================ transports
class Transport(object):
    """Contract between pipeline and platform. Implement four methods.

    connect()                     open the connection (may prompt for auth)
    ensure_dir(remote_dir)        create remote dir if missing (root-first)
    put(local_path, remote_path)  upload one file, binary, overwrite
    close()                       shut down politely

    remote paths are POSIX-style relative to the account root, e.g.
    "httpdocs/learn/app/session.html". A new transport is PROVEN by
    passing tools/tests/test_pipeline.py with itself substituted for
    LocalTransport (see docs/use_cases.md, UC3.4).
    """
    def __init__(self, site): self.site = site
    def connect(self): raise NotImplementedError
    def ensure_dir(self, remote_dir): raise NotImplementedError
    def put(self, local_path, remote_path): raise NotImplementedError
    def close(self): pass

class FtpTransport(Transport):
    """Plain FTP / FTPS — the old-platform (knocbrac.com) workhorse."""
    def connect(self):
        pwd = (os.environ.get("KB_DEPLOY_PASSWORD")
               or self.site.get("password")
               or getpass.getpass("Password for %s@%s: "
                                  % (self.site["user"], self.site["host"])))
        if self.site.get("use_tls", True):
            try:
                self.ftp = FTP_TLS(self.site["host"], timeout=30)
                self.ftp.login(self.site["user"], pwd)
                self.ftp.prot_p()
                say("✓ connected (FTPS)")
                return
            except Exception as e:
                say("… FTPS failed (%s), trying plain FTP" % e)
        self.ftp = FTP(self.site["host"], timeout=30)
        self.ftp.login(self.site["user"], pwd)
        say("✓ connected (FTP — note: credentials travel unencrypted)")
    def ensure_dir(self, remote_dir):
        try: self.ftp.mkd(remote_dir)
        except error_perm: pass
    def put(self, local_path, remote_path):
        with open(local_path, "rb") as fh:
            self.ftp.storbinary("STOR " + remote_path, fh)
    def close(self):
        try: self.ftp.quit()
        except Exception: pass

class LocalTransport(Transport):
    """Deploys into a local directory (site key "target_dir" or env
    KB_LOCAL_TARGET). Exists so the whole pipeline is testable with no
    network, and as the yardstick for proving other transports."""
    def connect(self):
        self.target = os.environ.get("KB_LOCAL_TARGET") or self.site.get("target_dir")
        if not self.target:
            raise DeployError("local transport needs target_dir or KB_LOCAL_TARGET")
        os.makedirs(self.target, exist_ok=True)
    def ensure_dir(self, remote_dir):
        os.makedirs(os.path.join(self.target, remote_dir), exist_ok=True)
    def put(self, local_path, remote_path):
        dst = os.path.join(self.target, remote_path)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(local_path, dst)

class SftpTransport(Transport):
    """STUB — new platform (agileintegrator.com). Two sane routes:

    A) paramiko SFTP: connect with key_file/agent, sftp.mkdir in
       ensure_dir (tolerate existing), sftp.put in put().
    B) rsync-over-ssh (preferred if available): collect files in put(),
       flush once in close() via
         rsync -az --files-from=<list> <site_dir>/ user@host:<remote_root>/
    Either way: prove it per docs/use_cases.md UC3.4 before first use."""
    def connect(self):
        raise NotImplementedError(
            "SFTP transport is a stub — implement per docstring (paramiko or "
            "rsync-over-ssh), then prove it with tools/tests/test_pipeline.py.")

TRANSPORTS = {"ftp": FtpTransport, "local": LocalTransport, "sftp": SftpTransport}

# ============================================================ pipeline core
def load_site(name):
    p = os.path.join(SITES, name, "site.json")
    if not os.path.exists(p):
        raise DeployError("no such site: %s (missing %s)" % (name, os.path.relpath(p, ROOT)))
    site = json.load(open(p, encoding="utf-8"))
    return site, os.path.join(SITES, name)

def list_sites():
    if not os.path.isdir(SITES): return []
    return sorted(d for d in os.listdir(SITES)
                  if os.path.exists(os.path.join(SITES, d, "site.json")))

def preflight(site, base):
    say("— Pre-flight (%s) —" % ", ".join(site.get("checks", [])))
    probs = []
    for name in site.get("checks", []):
        fn = CHECKS.get(name)
        if not fn:
            probs.append("unknown check in site.json: %s" % name); continue
        got = fn(site, base)
        probs += got
        say(("✓ %s" % name) if not got
            else ("✗ %s (%d problem%s)" % (name, len(got), "" if len(got) == 1 else "s")))
    for p in probs: say("  ✗ " + p)
    if probs: raise DeployError("pre-flight failed")
    say("✓ PRE-FLIGHT PASSED")

def deployable(site, base, include_init):
    out = []
    for p in _walk(site, base):
        r = os.path.relpath(p, base).replace("\\", "/")
        skip = False
        for pat in site.get("exclude", []):
            if fnmatch.fnmatch(r, pat):
                skip = not (include_init and r in site.get("init_include", []))
                break
        if not skip:
            out.append(p)
    return out

def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def delta(site_name, base, paths, force_all):
    manip = os.path.join(ROOT, ".deploy-manifest-%s.json" % site_name)
    old = {}
    if os.path.exists(manip) and not force_all:
        try: old = json.load(open(manip, encoding="utf-8"))
        except Exception: old = {}
    new, todo = {}, []
    for p in paths:
        r = os.path.relpath(p, base).replace("\\", "/")
        d = sha(p); new[r] = d
        if old.get(r) != d: todo.append(p)
    return todo, new, manip

def upload(site, base, todo, dry):
    remote_root = site.get("remote_root", "").strip("/")
    if dry:
        for p in todo: say("would upload: %s" % os.path.relpath(p, base))
        say("— dry run: %d file(s), nothing sent —" % len(todo))
        return False
    t = TRANSPORTS[site["transport"]](site)
    t.connect()
    made = set()
    for p in todo:
        r = os.path.relpath(p, base).replace("\\", "/")
        remote = (remote_root + "/" + r) if remote_root else r
        parts = remote.split("/")[:-1]
        cur = ""
        for part in parts:
            cur = (cur + "/" + part) if cur else part
            if cur not in made:
                t.ensure_dir(cur); made.add(cur)
        t.put(p, remote)
        say("↑ %s" % r)
    t.close()
    say("✓ uploaded %d file(s)" % len(todo))
    return True

def check_probe(pr, body, base):
    """Pure verification-probe logic (unit-testable). Returns (ok, message)."""
    if "expect" in pr:
        ok = pr["expect"] in body
        return ok, ("%s contains %r" % (pr["url"], pr["expect"])) if ok else \
               ("%s missing %r — got: %s" % (pr["url"], pr["expect"], body.strip()[:120]))
    if "json_key" in pr:
        live = json.loads(body).get(pr["json_key"], "?")
        local = json.load(open(os.path.join(base, pr["matches_local"]),
                               encoding="utf-8")).get(pr["json_key"], "?")
        ok = live == local
        return ok, ("%s %s matches local: %s" % (pr["url"], pr["json_key"], live)) if ok \
               else ("%s mismatch — local %s, live %s" % (pr["json_key"], local, live))
    return False, "probe has neither 'expect' nor 'json_key'"

def verify(site, base):
    import urllib.request
    root = site.get("site_url", "").rstrip("/")
    probes = site.get("verify", [])
    if not (root and probes):
        say("(no verification probes configured)"); return
    say("— Post-deploy verification —")
    for pr in probes:
        try:
            with urllib.request.urlopen(root + pr["url"], timeout=20) as r:
                body = r.read().decode("utf-8", "replace")
            ok, msg = check_probe(pr, body, base)
            say(("✓ " if ok else "✗ ") + msg)
        except Exception as e:
            say("✗ %s failed: %s" % (pr["url"], e))

def run(name, flags):
    site, base = load_site(name)
    if site.get("transport") not in TRANSPORTS:
        raise DeployError("unknown transport %r" % site.get("transport"))
    say("=== site: %s (%s) ===" % (name, site["transport"]))
    preflight(site, base)
    if "--check" in flags: return
    todo, new_manifest, manip = delta(name, base,
                                      deployable(site, base, "--init" in flags),
                                      "--all" in flags)
    if not todo:
        say("Nothing changed since last deploy. (--all forces everything.)")
    else:
        if upload(site, base, todo, "--dry-run" in flags):
            json.dump(new_manifest, open(manip, "w", encoding="utf-8"), indent=2)
    if "--dry-run" not in flags:
        verify(site, base)

def main():
    args = sys.argv[1:]
    flags = set(a for a in args if a.startswith("--"))
    names = [a for a in args if not a.startswith("--")]
    if not names:
        say("Sites: %s" % (", ".join(list_sites()) or "(none found)"))
        say("Usage: python3 tools/deploy.py <site> [--check|--dry-run|--all|--init]")
        return
    try:
        run(names[0], flags)
    except DeployError as e:
        say("✗ " + str(e)); sys.exit(1)

if __name__ == "__main__":
    main()
