"""Transport proofs (UC3.4). Runs the REAL pipeline + REAL transport logic
against fake endpoints, asserting byte-identity of the deployed tree.
This is the proving ritual from docs/use_cases.md: a transport passes here
before it earns a site.json; the first live run is then just a shakedown.
"""
import unittest, os, sys, json, shutil, tempfile, hashlib

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)
import deploy as D

REPO = os.path.dirname(TOOLS)
SITE_DIR = os.path.join(REPO, "sites", "knocbrac")

def sha(path):
    h = hashlib.sha256(); h.update(open(path, "rb").read()); return h.hexdigest()


class FakeSFTPClient(object):
    """Duck-types the four paramiko.SFTPClient calls SftpTransport makes
    (stat, mkdir, put, close), writing into a local target directory."""
    def __init__(self, target): self.target = target
    def _p(self, remote): return os.path.join(self.target, *remote.split("/"))
    def stat(self, remote):
        if not os.path.exists(self._p(remote)):
            raise IOError("no such file: " + remote)
    def mkdir(self, remote): os.mkdir(self._p(remote))
    def put(self, local, remote): shutil.copyfile(local, self._p(remote))
    def close(self): pass


class SftpProof(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.base = os.path.join(self.tmp, "site")
        shutil.copytree(SITE_DIR, self.base)
        self.target = os.path.join(self.tmp, "server")
        os.makedirs(self.target)
        self.site = json.load(open(os.path.join(SITE_DIR, "site.json")))
        self.site["transport"] = "sftp"
        # bypass network: attach the fake client exactly where connect() would
        target = self.target
        class TestTransport(D.SftpTransport):
            def connect(self2):
                self2.sftp = FakeSFTPClient(target)
                self2.ssh = type("S", (), {"close": staticmethod(lambda: None)})()
        self._orig = D.TRANSPORTS["sftp"]
        D.TRANSPORTS["sftp"] = TestTransport
        self._old_root = D.ROOT
        D.ROOT = self.tmp

    def tearDown(self):
        D.TRANSPORTS["sftp"] = self._orig
        D.ROOT = self._old_root
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_sftp_deploy_byte_identical(self):
        """UC3.4 for the SFTP transport: full tree through ensure_dir/put,
        target must match source file-for-file with nothing extra."""
        files = D.deployable(self.site, self.base, False)
        todo, mani, manip = D.delta("t", self.base, files, True)
        D.upload(self.site, self.base, todo, dry=False)
        root = os.path.join(self.target, "httpdocs")
        for p in files:
            r = os.path.relpath(p, self.base).replace("\\", "/")
            dst = os.path.join(root, *r.split("/"))
            self.assertTrue(os.path.exists(dst), "missing on target: " + r)
            self.assertEqual(sha(p), sha(dst), "byte mismatch: " + r)
        landed = []
        for dp, _dn, fn in os.walk(root):
            for f in fn:
                landed.append(os.path.relpath(os.path.join(dp, f), root).replace("\\", "/"))
        expect = sorted(os.path.relpath(p, self.base).replace("\\", "/") for p in files)
        self.assertEqual(sorted(landed), expect)
        # results protection held through this transport too
        self.assertFalse(any(l.startswith("learn/results/") for l in landed))

    def test_ensure_dir_tolerates_existing(self):
        t = D.TRANSPORTS["sftp"](self.site)
        t.connect()
        t.ensure_dir("httpdocs")
        t.ensure_dir("httpdocs")            # second call must not raise
        t.ensure_dir("httpdocs/learn")
        self.assertTrue(os.path.isdir(os.path.join(self.target, "httpdocs", "learn")))


class SftpDependencyMessage(unittest.TestCase):
    def test_missing_paramiko_reports_clearly(self):
        """If paramiko isn't installed, the error must say how to fix it."""
        try:
            import paramiko  # noqa: F401
            self.skipTest("paramiko installed here — message path not reachable")
        except ImportError:
            pass
        site = {"host": "x", "user": "u"}
        with self.assertRaises(D.DeployError) as ctx:
            D.SftpTransport(site).connect()
        self.assertIn("pip install paramiko", str(ctx.exception))


class FakeBatchRunner(object):
    """Interprets the generated sftp batch locally: -mkdir → makedirs,
    put → copy. Lets the REAL batch-generation logic be proven byte-for-byte."""
    def __init__(self, target): self.target = target
    def run(self, batch_text):
        for line in batch_text.strip().split("\n"):
            if line.startswith("-mkdir "):
                os.makedirs(os.path.join(self.target, *line[7:].split("/")), exist_ok=True)
            elif line.startswith("put "):
                import shlex
                _put, local, remote = shlex.split(line)
                dst = os.path.join(self.target, *remote.split("/"))
                shutil.copyfile(local, dst)
            else:
                raise AssertionError("unexpected batch line: " + line)


class SftpCliProof(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.base = os.path.join(self.tmp, "site")
        shutil.copytree(SITE_DIR, self.base)
        self.target = os.path.join(self.tmp, "server")
        os.makedirs(self.target)
        self.site = json.load(open(os.path.join(SITE_DIR, "site.json")))
        self.site["transport"] = "sftpcli"
        target = self.target
        class TestTransport(D.SftpCliTransport):
            def connect(self2):
                self2._batch = []; self2._nfiles = 0
            def close(self2):
                FakeBatchRunner(target).run("\n".join(self2._batch) + "\n")
        self._orig = D.TRANSPORTS["sftpcli"]
        D.TRANSPORTS["sftpcli"] = TestTransport
        self._old_root = D.ROOT
        D.ROOT = self.tmp

    def tearDown(self):
        D.TRANSPORTS["sftpcli"] = self._orig
        D.ROOT = self._old_root
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_batch_deploy_byte_identical(self):
        files = D.deployable(self.site, self.base, False)
        todo, _m, _p = D.delta("t", self.base, files, True)
        D.upload(self.site, self.base, todo, dry=False)
        root = os.path.join(self.target, "httpdocs")
        for p in files:
            r = os.path.relpath(p, self.base).replace("\\", "/")
            dst = os.path.join(root, *r.split("/"))
            self.assertTrue(os.path.exists(dst), "missing on target: " + r)
            self.assertEqual(sha(p), sha(dst), "byte mismatch: " + r)
        landed = []
        for dp, _dn, fn in os.walk(root):
            for f in fn:
                landed.append(os.path.relpath(os.path.join(dp, f), root).replace("\\", "/"))
        self.assertEqual(sorted(landed),
                         sorted(os.path.relpath(p, self.base).replace("\\", "/") for p in files))

    def test_dirs_precede_their_files_in_batch(self):
        t = D.TRANSPORTS["sftpcli"](self.site)   # connect() bypassed in setUp
        t.connect()
        t.ensure_dir("httpdocs"); t.ensure_dir("httpdocs/learn")
        src = os.path.join(self.base, "learn", "courses.json")
        t.put(src, "httpdocs/learn/courses.json")
        joined = "\n".join(t._batch)
        self.assertLess(joined.index("-mkdir httpdocs/learn"),
                        joined.index("put "), "mkdir must precede put")


if __name__ == "__main__":
    unittest.main()

