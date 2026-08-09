"""UC3 acceptance tests — the deploy pipeline, end-to-end, no network.
Deploys the real knocbrac tree through LocalTransport into a temp target.
"""
import unittest, os, sys, json, shutil, tempfile, hashlib

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)
import deploy as D

REPO = os.path.dirname(TOOLS)
SITE_DIR = os.path.join(REPO, "sites", "knocbrac")

def sha(path):
    h = hashlib.sha256()
    h.update(open(path, "rb").read())
    return h.hexdigest()

class LocalDeploy(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # sandbox copy of the whole site so tests can mutate it
        self.base = os.path.join(self.tmp, "site")
        shutil.copytree(SITE_DIR, self.base)
        self.target = os.path.join(self.tmp, "server")
        self.site = json.load(open(os.path.join(SITE_DIR, "site.json")))
        self.site["transport"] = "local"
        self.site["target_dir"] = self.target
        self.site["remote_root"] = "httpdocs"
        # keep manifests inside the sandbox
        self._old_root = D.ROOT
        D.ROOT = self.tmp

    def tearDown(self):
        D.ROOT = self._old_root
        shutil.rmtree(self.tmp, ignore_errors=True)

    def deploy(self, include_init=False, force_all=True):
        files = D.deployable(self.site, self.base, include_init)
        todo, mani, manip = D.delta("t", self.base, files, force_all)
        if todo:
            D.upload(self.site, self.base, todo, dry=False)
            json.dump(mani, open(manip, "w"))
        return files, todo

    # UC3.4 — the transport-equivalence yardstick
    def test_local_deploy_byte_identical(self):
        files, todo = self.deploy()
        self.assertEqual(len(files), len(todo))
        for p in files:
            r = os.path.relpath(p, self.base).replace("\\", "/")
            dst = os.path.join(self.target, "httpdocs", r)
            self.assertTrue(os.path.exists(dst), "missing on target: " + r)
            self.assertEqual(sha(p), sha(dst), "byte mismatch: " + r)
        # nothing extra landed
        landed = []
        for dp, _dn, fn in os.walk(os.path.join(self.target, "httpdocs")):
            for f in fn:
                landed.append(os.path.relpath(os.path.join(dp, f),
                              os.path.join(self.target, "httpdocs")).replace("\\", "/"))
        expect = sorted(os.path.relpath(p, self.base).replace("\\", "/") for p in files)
        self.assertEqual(sorted(landed), expect)

    # UC3.2
    def test_delta_and_idempotence(self):
        self.deploy()
        files = D.deployable(self.site, self.base, False)
        todo2, _m, _p = D.delta("t", self.base, files, force_all=False)
        self.assertEqual(todo2, [], "re-deploy should transfer nothing")
        # touch exactly one file → exactly one upload
        target_file = os.path.join(self.base, "learn", "courses.json")
        open(target_file, "a").write("\n")
        todo3, _m, _p = D.delta("t", self.base, files, force_all=False)
        self.assertEqual([os.path.relpath(p, self.base).replace("\\", "/") for p in todo3],
                         ["learn/courses.json"])

    # UC3.3
    def test_results_protected(self):
        # plant a fake live-results file locally; it must never deploy
        fake = os.path.join(self.base, "learn", "results", "graceco-w1s1-session-x.json")
        open(fake, "w").write("{}")
        files, _ = self.deploy(include_init=False)
        rels = [os.path.relpath(p, self.base).replace("\\", "/") for p in files]
        self.assertFalse(any(r.startswith("learn/results/") for r in rels))
        self.assertFalse(os.path.exists(os.path.join(
            self.target, "httpdocs", "learn", "results", "graceco-w1s1-session-x.json")))
        # --init adds only the declared placeholder
        files_i = D.deployable(self.site, self.base, True)
        rels_i = [os.path.relpath(p, self.base).replace("\\", "/") for p in files_i]
        extra = set(rels_i) - set(rels)
        self.assertEqual(extra, {"learn/results/index.html"})

    # UC3.1
    def test_preflight_failure_blocks_deploy(self):
        open(os.path.join(self.base, "learn", "courses.json"), "a").write("{broken")
        with self.assertRaises(D.DeployError):
            D.preflight(self.site, self.base)

    # UC1.5 — a new course is content only
    def test_new_course_needs_no_engine_change(self):
        newc = os.path.join(self.base, "learn", "testco")
        os.makedirs(os.path.join(newc, "content"))
        json.dump({"id": "testco",
                   "map": {"heading": "{student}'s lab", "blurb": "b"},
                   "units": [{"title": "U1", "sessions":
                              [{"id": "w1s1", "title": "T"}]}]},
                  open(os.path.join(newc, "course.json"), "w"))
        json.dump({"id": "w1s1", "kind": "session", "tag": "t", "title": "T",
                   "blocks": [{"type": "read", "html": "hi"}],
                   "done": {"title": "d", "html": "x"}},
                  open(os.path.join(newc, "content", "w1s1.json"), "w"))
        reg = json.load(open(os.path.join(self.base, "learn", "courses.json")))
        reg["courses"].append({"id": "testco", "student": "T", "title": "T",
                               "tagline": "t", "icon": "🧪",
                               "theme": {"accent": "#333333", "soft": "#eeeeee",
                                         "warm": "#cccccc", "bigText": False}})
        json.dump(reg, open(os.path.join(self.base, "learn", "courses.json"), "w"))
        # all checks still pass — no engine file was touched
        D.preflight(self.site, self.base)
        files, todo = self.deploy()
        rels = [os.path.relpath(p, self.base).replace("\\", "/") for p in todo]
        self.assertIn("learn/testco/course.json", rels)
        self.assertIn("learn/testco/content/w1s1.json", rels)

    # UC3.5 — probe logic (the pure part of verification)
    def test_verify_probe_logic(self):
        ok, _ = D.check_probe({"url": "/x", "expect": "receiver alive"},
                              '{"status":"receiver alive (php 5.6.36)"}', self.base)
        self.assertTrue(ok)
        ok, _ = D.check_probe({"url": "/x", "expect": "receiver alive"},
                              "<html>500</html>", self.base)
        self.assertFalse(ok)
        rel = json.load(open(os.path.join(self.base, "learn", "courses.json")))["release"]
        ok, _ = D.check_probe({"url": "/c", "json_key": "release",
                               "matches_local": "learn/courses.json"},
                              json.dumps({"release": rel}), self.base)
        self.assertTrue(ok)
        ok, _ = D.check_probe({"url": "/c", "json_key": "release",
                               "matches_local": "learn/courses.json"},
                              json.dumps({"release": "r0"}), self.base)
        self.assertFalse(ok)

if __name__ == "__main__":
    unittest.main()
