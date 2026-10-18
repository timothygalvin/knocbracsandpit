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

    # ---- UC4: split deploy paths (content and code ship independently) ----

    def rels(self, files):
        return sorted(os.path.relpath(p, self.base).replace("\\", "/") for p in files)

    # UC4.1 — each path ships only its own artefact
    def test_artefact_paths_are_disjoint_and_complete(self):
        every = self.rels(D.deployable(self.site, self.base, False))
        content = self.rels(D.deployable(self.site, self.base, False, artefact="content"))
        code = self.rels(D.deployable(self.site, self.base, False, artefact="code"))
        self.assertEqual(set(content) & set(code), set(), "artefacts overlap")
        self.assertEqual(sorted(content + code), every, "a file belongs to neither path")
        # content is course data only; no engine file may ride along
        for r in content:
            self.assertTrue(r.endswith("course.json") or r.endswith("courses.json")
                            or "/content/" in r, "engine file on content path: " + r)
        for r in code:
            self.assertNotIn("/content/", r, "content file on code path: " + r)

    # UC4.2 — the coverage check catches a file that belongs to neither path
    def test_uncovered_file_detected(self):
        open(os.path.join(self.base, "learn", "stray.txt"), "w").write("x")
        probs = D.check_coverage(self.site, self.base)
        self.assertTrue(any("stray.txt" in p and "no artefact" in p for p in probs), probs)

    def test_overlapping_artefacts_detected(self):
        site = dict(self.site)
        site["artefacts"] = {"content": ["learn/courses.json"],
                             "code": ["learn/courses.json"]}
        probs = D.check_coverage(site, self.base)
        self.assertTrue(any("claimed by" in p for p in probs), probs)

    # UC4.3 — a content deploy must not make the pipeline forget the engine
    def test_split_deploy_preserves_other_artefact_in_manifest(self):
        # full deploy first, so the manifest knows about every file
        self.deploy()
        full = json.load(open(os.path.join(self.tmp, ".deploy-manifest-t.json")))
        self.assertTrue(any("/assets/" in k for k in full), "engine missing from manifest")
        # now change one content file and deploy ONLY content
        target = os.path.join(self.base, "learn", "courses.json")
        open(target, "a").write("\n")
        files = D.deployable(self.site, self.base, False, artefact="content")
        todo, mani, manip = D.delta("t", self.base, files, False,
                                    site=self.site, artefact="content")
        self.assertEqual(self.rels(todo), ["learn/courses.json"])
        # engine entries survive untouched; content entry is updated
        for k, v in full.items():
            if "/content/" not in k and not k.endswith("course.json") \
               and not k.endswith("courses.json"):
                self.assertEqual(mani.get(k), v, "engine entry lost from manifest: " + k)
        self.assertNotEqual(mani["learn/courses.json"], full["learn/courses.json"])
        # and a content deploy leaves the code path with nothing to do
        json.dump(mani, open(manip, "w"))
        code_files = D.deployable(self.site, self.base, False, artefact="code")
        code_todo, _m, _p = D.delta("t", self.base, code_files, False,
                                    site=self.site, artefact="code")
        self.assertEqual(code_todo, [], "content deploy dirtied the code path")

    # UC4.4 — a split deploy forgets files deleted from its own artefact only
    def test_split_deploy_prunes_within_its_artefact(self):
        self.deploy()
        gone = os.path.join(self.base, "learn", "ascent", "content", "w1s1.json")
        os.remove(gone)
        # manifest must stay valid for the check that would now fail; deploy raw
        files = D.deployable(self.site, self.base, False, artefact="content")
        _todo, mani, _p = D.delta("t", self.base, files, False,
                                  site=self.site, artefact="content")
        self.assertNotIn("learn/ascent/content/w1s1.json", mani)
        self.assertIn("learn/assets/shared.js", mani)

    # UC4.5 — the release manifest records what ships, with hashes
    def test_release_manifest_records_shipping_set(self):
        self.deploy()  # everything now "unchanged"
        newf = os.path.join(self.base, "learn", "graceco", "content", "w9s9.json")
        json.dump({"id": "w9s9", "kind": "session", "tag": "t", "title": "Ghost",
                   "blocks": [], "done": {"title": "d", "html": "x"}},
                  open(newf, "w"))
        files = D.deployable(self.site, self.base, False, artefact="content")
        man = D.release_manifest(self.site, self.base, "content", files, site_name="t")
        self.assertEqual(man["artefact"], "content")
        self.assertEqual(man["shipping"], ["learn/graceco/content/w9s9.json"])
        self.assertEqual(man["shipping_count"], 1)
        self.assertEqual(man["file_count"], len(files))
        by_path = {e["path"]: e for e in man["files"]}
        self.assertEqual(by_path["learn/graceco/content/w9s9.json"]["state"], "new")
        self.assertEqual(by_path["learn/ascent/course.json"]["state"], "unchanged")
        self.assertEqual(len(by_path["learn/graceco/content/w9s9.json"]["sha256"]), 64)
        self.assertIn("w9s9", [s["id"] for s in man["sessions"]])

    # UC3.5 — probe logic (the pure part of verification)
    def test_verify_probe_logic(self):
        ok, _ = D.check_probe({"url": "/x", "expect": "receiver alive"},
                              '{"status":"receiver alive (php 5.6.36)"}', self.base)
        self.assertTrue(ok)
        ok, _ = D.check_probe({"url": "/x", "expect": "receiver alive"},
                              "<html>500</html>", self.base)
        self.assertFalse(ok)
        rel = json.load(open(os.path.join(self.base, "learn", "courses.json")))["version"]
        ok, _ = D.check_probe({"url": "/c", "json_key": "version",
                               "matches_local": "learn/courses.json"},
                              json.dumps({"version": rel}), self.base)
        self.assertTrue(ok)
        ok, _ = D.check_probe({"url": "/c", "json_key": "version",
                               "matches_local": "learn/courses.json"},
                              json.dumps({"version": "r0"}), self.base)
        self.assertFalse(ok)

    # UC5 — a split deploy runs only its own artefact's probes
    def test_verify_probes_select_by_artefact(self):
        site = dict(self.site)
        site["verify"] = {"code": [{"url": "/a"}], "content": [{"url": "/b"}]}
        urls = lambda art: [p["url"] for p in D.select_probes(site, art)]
        self.assertEqual(urls("content"), ["/b"])
        self.assertEqual(urls("code"), ["/a"])
        self.assertEqual(urls(None), ["/a", "/b"], "full deploy runs both sets")
        # a flat list stays backward compatible for sites that declare one
        site["verify"] = [{"url": "/flat"}]
        self.assertEqual(urls("content"), ["/flat"])
        self.assertEqual(urls(None), ["/flat"])
        # the real site.json wires the content probe to the content marker
        real = D.select_probes(self.site, "content")
        self.assertEqual([p["json_key"] for p in real], ["version"])

if __name__ == "__main__":
    unittest.main()
