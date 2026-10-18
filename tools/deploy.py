#!/usr/bin/env python3
"""Multi-site test + deploy pipeline (repo layout).

Sites are discovered from sites/<name>/site.json. Paths inside a site.json
(sources, exclude, matches_local) are relative to that site's directory.

    python3 tools/deploy.py knocbrac --check      pre-flight only
    python3 tools/deploy.py knocbrac --dry-run    show what would upload
    python3 tools/deploy.py knocbrac              check -> upload delta -> verify
    python3 tools/deploy.py knocbrac --all        ignore manifest, send everything
    python3 tools/deploy.py knocbrac --all --init also send protected placeholders

Split deploy paths (a site.json "artefacts" block declares them):

    python3 tools/deploy.py knocbrac --content    course content only
    python3 tools/deploy.py knocbrac --code       engine/platform files only
    python3 tools/deploy.py knocbrac --content --manifest[=path]
                                                  write a release manifest of
                                                  exactly what that path ships

Content and engine are separately deployable because content files declare
no engine features beyond the schema the live engine already renders. A
split deploy is authoritative only for its own artefact: the upload manifest
carries the other artefact's entries through untouched, so shipping content
never makes the pipeline forget the engine (or vice versa). The "coverage"
check refuses to deploy if any file belongs to neither path — otherwise a new
file would ship on a full deploy but be invisible to both split ones.

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


ASSET_REF = re.compile(r'assets/[A-Za-z0-9_.-]+(\?v=[A-Za-z0-9_.-]+)?')
SEMVER    = re.compile(r'^(\d+)\.(\d+)\.(\d+)$')
CONTENT_V = re.compile(r'^r(\d+)$')

def code_version_file(site):
    return site.get("code_version_file", "learn/assets/version.json")

def code_version(site, base):
    """Platform code version (semver). Code-owned, so bumping the engine
    never means editing a content file. None = site declares none."""
    p = os.path.join(base, code_version_file(site))
    if not os.path.exists(p):
        return None
    try:
        return json.load(open(p, encoding="utf-8")).get("version")
    except Exception:
        return None

def content_version(site, base):
    """(content version rN, the code MAJOR it targets) from courses.json."""
    reg = os.path.join(base, site.get("sources", ["learn"])[0], "courses.json")
    if not os.path.exists(reg):
        return None, None
    try:
        d = json.load(open(reg, encoding="utf-8"))
        return d.get("version"), d.get("requires_code")
    except Exception:
        return None, None

def check_cache(site, base):
    """Release integrity: every assets/ include in shipped HTML must carry
    ?v=<code version>, and a Cache-Control policy must exist in .htaccess.
    Guards the stale-shared.js bug class (the mergedDone TypeError) at
    pre-flight instead of in a child's browser. The token comes from the
    code-owned version file, NOT from courses.json — that separation is
    what keeps a code release off the content path."""
    probs = []
    release = code_version(site, base)
    if release is None:
        return []  # site declares no code version — check not applicable
    for p in _walk(site, base):
        if not p.endswith(".html"):
            continue
        rp = os.path.relpath(p, base).replace("\\", "/")
        if "/results/" in "/" + rp:
            continue  # receiver-owned page, not shipped by deploy
        src = open(p, encoding="utf-8", errors="replace").read()
        for m in ASSET_REF.finditer(src):
            ver = m.group(1)
            if ver is None:
                probs.append("%s: unversioned asset include %r — add ?v=%s"
                             % (rp, m.group(0), release))
            elif ver != "?v=" + str(release):
                probs.append("%s: %r does not match code version %r"
                             % (rp, m.group(0), release))
    ht = os.path.join(base, site.get("sources", ["learn"])[0], ".htaccess")
    if os.path.exists(ht) and "Cache-Control" not in open(ht, encoding="utf-8").read():
        probs.append(".htaccess has no Cache-Control policy — stale-asset "
                     "protection missing")
    return probs

def check_compat(site, base):
    """Two artefacts, two version lines, one compatibility rule.

    Code is semantic (MAJOR.MINOR.PATCH) and a MAJOR bump is the ONLY
    change that can invalidate content — minor and patch never do. Content
    is a simple rN counter (it has no dependents of its own, so semver
    would be three numbers where one will do) and names the code MAJOR it
    was authored against. Same scheme for every site."""
    if not artefact_globs(site):
        return []
    probs = []
    code = code_version(site, base)
    if code is None:
        return ["no code version file at %s — split deploy paths need one"
                % code_version_file(site)]
    if not SEMVER.match(str(code)):
        probs.append("code version %r is not semantic (want MAJOR.MINOR.PATCH)"
                     % code)
    cv, req = content_version(site, base)
    if cv is None:
        probs.append("courses.json has no 'version' (want a simple rN)")
    elif not CONTENT_V.match(str(cv)):
        probs.append("content version %r is not rN" % cv)
    if req is None:
        probs.append("courses.json has no 'requires_code' — content must name "
                     "the code MAJOR it was authored against")
    elif SEMVER.match(str(code)) and str(req) != str(code).split(".")[0]:
        probs.append("content targets code MAJOR %s but this tree's code is %s "
                     "— a MAJOR bump is the one change that breaks content, so "
                     "either the content or requires_code needs updating"
                     % (req, code))
    return probs

def artefact_globs(site):
    """Declared artefact classes: {"content": [globs], "code": [globs]}.
    A site that declares none simply has no split deploy paths."""
    return site.get("artefacts") or {}

def classify(site, rel):
    """Which artefact(s) a deployable path belongs to. Exactly one is
    correct; zero or several is a site.json bug and check_coverage says so."""
    return [name for name, pats in sorted(artefact_globs(site).items())
            if any(fnmatch.fnmatch(rel, p) for p in pats)]

def check_coverage(site, base):
    """Every deployable file belongs to exactly one artefact, so a split
    deploy can never silently leave one behind."""
    if not artefact_globs(site):
        return []
    probs = []
    for p in deployable(site, base, True):
        rel = os.path.relpath(p, base).replace("\\", "/")
        hits = classify(site, rel)
        if not hits:
            probs.append("%s belongs to no artefact — add a glob to site.json "
                         "'artefacts'; it would ship on a full deploy but be "
                         "invisible to every split one" % rel)
        elif len(hits) > 1:
            probs.append("%s is claimed by %s — artefact globs must not overlap"
                         % (rel, " and ".join(hits)))
    return probs

CHECKS = {"json": check_json, "php56": check_php56, "ids": check_ids,
          "manifests": check_manifests, "schema": check_schema,
          "cache": check_cache, "coverage": check_coverage,
          "compat": check_compat}

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
                self.ftp = FTP_TLS(timeout=30); self.ftp.connect(self.site["host"], int(self.site.get("port", 21)))
                self.ftp.login(self.site["user"], pwd)
                self.ftp.prot_p()
                say("✓ connected (FTPS)")
                return
            except Exception as e:
                say("… FTPS failed (%s), trying plain FTP" % e)
        self.ftp = FTP(timeout=30); self.ftp.connect(self.site["host"], int(self.site.get("port", 21)))
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
    """SFTP over SSH (paramiko). Used by knocbrac.com (IP-addressed, port
    22 — see the FileZilla profile this mirrors) and ready for
    agileintegrator.com. Auth: key_file if configured, else password from
    KB_DEPLOY_PASSWORD / site.json / prompt.

    Host-key policy is trust-on-first-use (AutoAddPolicy): fine for a
    hobby host you also reach with FileZilla; tighten to a known_hosts
    check if the threat model ever grows.

    Logic (ensure_dir/put) is proven by tools/tests/test_transports.py
    against a fake endpoint per UC3.4; first live run is the shakedown.

    A future rsync-over-ssh transport remains the better bulk option for
    the new platform; it must pass the same proof before use."""
    def connect(self):
        try:
            import paramiko
        except ImportError:
            raise DeployError("sftp transport needs paramiko — install with: "
                              "pip install paramiko")
        kw = dict(hostname=self.site["host"],
                  port=int(self.site.get("port", 22)),
                  username=self.site["user"], timeout=30)
        key = self.site.get("key_file")
        if key:
            kw["key_filename"] = os.path.expanduser(key)
        else:
            kw["password"] = (os.environ.get("KB_DEPLOY_PASSWORD")
                              or self.site.get("password")
                              or getpass.getpass("Password for %s@%s: "
                                                 % (self.site["user"], self.site["host"])))
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(**kw)
        self.sftp = self.ssh.open_sftp()
        say("✓ connected (SFTP, port %s)" % kw["port"])
    def ensure_dir(self, remote_dir):
        try:
            self.sftp.stat(remote_dir)
        except IOError:
            try:
                self.sftp.mkdir(remote_dir)
            except IOError:
                pass  # created concurrently or no permission — surfaces on put
    def put(self, local_path, remote_path):
        self.sftp.put(local_path, remote_path)
    def close(self):
        try:
            self.sftp.close(); self.ssh.close()
        except Exception:
            pass

class SftpCliTransport(Transport):
    """SFTP via the system OpenSSH client (`sftp` — preinstalled on macOS,
    Linux, and Windows 10+). ZERO Python dependencies. Requires SSH key
    auth (batch mode disables password prompts by design) — see README for
    the one-time key setup. ensure_dir/put collect into a batch script;
    close() flushes it in a single `sftp -b` run. Commands are prefixed
    with '-' where failure is expected-and-fine (mkdir of existing dirs)."""
    def connect(self):
        import shutil as _sh
        if not _sh.which("sftp"):
            raise DeployError("system `sftp` not found — install OpenSSH "
                              "client, or use transport 'sftp' (paramiko)")
        self._batch = []
        self._nfiles = 0
    def ensure_dir(self, remote_dir):
        self._batch.append("-mkdir %s" % remote_dir)
    def put(self, local_path, remote_path):
        self._batch.append('put "%s" "%s"' % (local_path, remote_path))
        self._nfiles += 1
    def _cmd(self, batch_path):
        """argv for the batched run. site.json "ssh_options" entries are
        passed through as -o flags, which is how a LEGACY host stays
        deployable from a clean clone instead of depending on whoever's
        ~/.ssh/config. knocbrac needs this: its sshd is OpenSSH 5.3, which
        can only sign with ssh-rsa (SHA-1) — and OpenSSH 8.8+ clients
        disable that by default, so they load the key and then discard it."""
        cmd = ["sftp", "-b", batch_path,
               "-P", str(self.site.get("port", 22)),
               "-o", "BatchMode=yes"]
        for opt in self.site.get("ssh_options", []):
            cmd += ["-o", str(opt)]
        cmd.append("%s@%s" % (self.site["user"], self.site["host"]))
        return cmd

    def close(self):
        if not getattr(self, "_batch", None):
            return
        import tempfile
        fd, bpath = tempfile.mkstemp(suffix=".sftp"); os.close(fd)
        try:
            with open(bpath, "w", encoding="utf-8") as fh:
                fh.write("\n".join(self._batch) + "\n")
            cmd = self._cmd(bpath)
            say("… flushing %d file(s) in one sftp batch" % self._nfiles)
            r = subprocess.run(cmd, capture_output=True, timeout=600)
            if r.returncode != 0:
                raise DeployError(
                    "sftp batch failed (is your SSH key installed on the "
                    "server? see README):\n" + r.stderr.decode(errors="replace")[-800:])
            say("✓ sftp batch complete")
        finally:
            os.remove(bpath)

TRANSPORTS = {"ftp": FtpTransport, "local": LocalTransport,
              "sftp": SftpTransport, "sftpcli": SftpCliTransport}

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

def deployable(site, base, include_init, artefact=None):
    """The files a deploy would ship. artefact=None means the whole site;
    naming one narrows the set to that artefact's declared globs."""
    out = []
    for p in _walk(site, base):
        r = os.path.relpath(p, base).replace("\\", "/")
        skip = False
        for pat in site.get("exclude", []):
            if fnmatch.fnmatch(r, pat):
                skip = not (include_init and r in site.get("init_include", []))
                break
        if skip:
            continue
        if artefact and artefact not in classify(site, r):
            continue
        out.append(p)
    return out

def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def delta(site_name, base, paths, force_all, site=None, artefact=None):
    """Changed files, plus the upload manifest to write once they land.

    A split deploy is authoritative ONLY for its own artefact: entries for
    the other artefact are carried through from disk untouched, so shipping
    content never makes the pipeline forget the engine files (which would
    silently re-upload the whole site on the next run). Within the deployed
    artefact, entries whose files have gone are dropped."""
    manip = os.path.join(ROOT, ".deploy-manifest-%s.json" % site_name)
    disk = {}
    if os.path.exists(manip):
        try: disk = json.load(open(manip, encoding="utf-8"))
        except Exception: disk = {}
    old = {} if force_all else disk
    new = dict(disk) if artefact else {}
    todo = []
    for p in paths:
        r = os.path.relpath(p, base).replace("\\", "/")
        d = sha(p); new[r] = d
        if old.get(r) != d: todo.append(p)
    if artefact:
        here = set(os.path.relpath(p, base).replace("\\", "/") for p in paths)
        for r in list(new):
            if r not in here and artefact in classify(site or {}, r):
                del new[r]
    return todo, new, manip

def release_manifest(site, base, artefact, files, site_name=None):
    """A record of exactly what a release contains: every file with its
    hash and size, which of them this push would actually send, and a
    readable summary of the course content in it."""
    import datetime
    live = {}
    if site_name:
        manip = os.path.join(ROOT, ".deploy-manifest-%s.json" % site_name)
        if os.path.exists(manip):
            try: live = json.load(open(manip, encoding="utf-8"))
            except Exception: live = {}
    entries, contents = [], []
    for p in sorted(files):
        rel = os.path.relpath(p, base).replace("\\", "/")
        digest = sha(p)
        entries.append({"path": rel, "sha256": digest,
                        "bytes": os.path.getsize(p),
                        "state": "new" if rel not in live else
                                 ("changed" if live[rel] != digest else "unchanged")})
        if "/content/" in rel and rel.endswith(".json"):
            try:
                doc = json.load(open(p, encoding="utf-8"))
                contents.append({"course": rel.split("/")[1], "id": doc.get("id"),
                                 "kind": doc.get("kind"), "tag": doc.get("tag"),
                                 "title": doc.get("title")})
            except Exception:
                pass
    reg = os.path.join(base, site.get("sources", ["learn"])[0], "courses.json")
    release = None
    if os.path.exists(reg):
        try: release = json.load(open(reg, encoding="utf-8")).get("release")
        except Exception: pass
    shipping = [e for e in entries if e["state"] != "unchanged"]
    return {"artefact": artefact or "all",
            "release": release,
            "generated": datetime.datetime.now().replace(microsecond=0).isoformat(),
            "file_count": len(entries),
            "shipping_count": len(shipping),
            "shipping": [e["path"] for e in shipping],
            "sessions": sorted(contents, key=lambda c: (c["course"], c["id"] or "")),
            "files": entries}

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

def select_probes(site, artefact=None):
    """Which verification probes apply. site.json "verify" may be a flat
    list (run after every deploy) or a per-artefact map, in which case a
    split deploy runs only its own artefact's probes and a full deploy
    runs all of them."""
    probes = site.get("verify", [])
    if isinstance(probes, dict):
        return (probes.get(artefact, []) if artefact
                else [pr for key in sorted(probes) for pr in probes[key]])
    return probes

def verify(site, base, artefact=None):
    import urllib.request
    root = site.get("site_url", "").rstrip("/")
    probes = select_probes(site, artefact)
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

def run(name, flags, manifest_out=None):
    site, base = load_site(name)
    if site.get("transport") not in TRANSPORTS:
        raise DeployError("unknown transport %r" % site.get("transport"))
    chosen = [a for a in sorted(artefact_globs(site)) if "--" + a in flags]
    if len(chosen) > 1:
        raise DeployError("pick one artefact path, not %s" % " and ".join(chosen))
    art = chosen[0] if chosen else None
    say("=== site: %s (%s) · %s ===" % (name, site["transport"],
                                        ("%s only" % art) if art else "full site"))
    preflight(site, base)
    files = deployable(site, base, "--init" in flags, artefact=art)
    if art:
        say("— %s path: %d of %d deployable file(s) —"
            % (art, len(files), len(deployable(site, base, "--init" in flags))))
    if manifest_out:
        rel = release_manifest(site, base, art, files, site_name=name)
        d = os.path.dirname(manifest_out)
        if d: os.makedirs(d, exist_ok=True)
        with open(manifest_out, "w", encoding="utf-8") as fh:
            json.dump(rel, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        say("✓ release manifest → %s (%d file(s) in release, %d to ship, "
            "%d session(s))"
            % (os.path.relpath(manifest_out, ROOT), rel["file_count"],
               rel["shipping_count"], len(rel["sessions"])))
    if "--check" in flags: return
    todo, new_manifest, manip = delta(name, base, files, "--all" in flags,
                                      site=site, artefact=art)
    if not todo:
        say("Nothing changed since last deploy. (--all forces everything.)")
    else:
        if upload(site, base, todo, "--dry-run" in flags):
            json.dump(new_manifest, open(manip, "w", encoding="utf-8"), indent=2)
    if "--dry-run" not in flags:
        verify(site, base, artefact=art)

DEFAULT_MANIFEST_DIR = os.path.join(ROOT, "releases")

def main():
    args = sys.argv[1:]
    flags = set(a.split("=", 1)[0] for a in args if a.startswith("--"))
    names = [a for a in args if not a.startswith("--")]
    if not names:
        say("Sites: %s" % (", ".join(list_sites()) or "(none found)"))
        say("Usage: python3 tools/deploy.py <site> "
            "[--check|--dry-run|--all|--init] [--content|--code] "
            "[--manifest[=path]]")
        return
    manifest_out = None
    if "--manifest" in flags:
        given = [a for a in args if a.startswith("--manifest=")]
        if given:
            manifest_out = os.path.abspath(given[0].split("=", 1)[1])
        else:
            art = next((a[2:] for a in args
                        if a in ("--content", "--code")), "full")
            manifest_out = os.path.join(DEFAULT_MANIFEST_DIR,
                                        "%s-%s.json" % (names[0], art))
    try:
        run(names[0], flags, manifest_out=manifest_out)
    except DeployError as e:
        say("✗ " + str(e)); sys.exit(1)

if __name__ == "__main__":
    main()
