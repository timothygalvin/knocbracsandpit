"""UC1/UC2 acceptance tests — content and platform checks.
Run: python3 -m unittest discover -s tools/tests -v
"""
import unittest, os, sys, json, shutil, tempfile

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)
import deploy as D

REPO = os.path.dirname(TOOLS)
SITE_DIR = os.path.join(REPO, "sites", "knocbrac")

def real_site():
    return json.load(open(os.path.join(SITE_DIR, "site.json"), encoding="utf-8"))

class ChecksTree(unittest.TestCase):
    """Each test copies the real tree to a sandbox, breaks one thing, and
    asserts the right check catches it (and only then)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.base = os.path.join(self.tmp, "site")
        shutil.copytree(SITE_DIR, self.base)
        self.site = real_site()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def path(self, *bits):
        return os.path.join(self.base, *bits)

    # UC1.1
    def test_valid_tree_passes(self):
        for name in dict.fromkeys(self.site["checks"] + ["schema", "cache"]):
            self.assertEqual(D.CHECKS[name](self.site, self.base), [],
                             "check %r flagged the known-good tree" % name)

    def test_broken_json_detected(self):
        with open(self.path("learn", "courses.json"), "a") as fh:
            fh.write("{trailing garbage")
        probs = D.check_json(self.site, self.base)
        self.assertTrue(any("courses.json" in p for p in probs))

    # UC2.2
    def test_php7_token_detected(self):
        p = self.path("learn", "api", "submit.php")
        src = open(p).read()
        open(p, "w").write(src.replace("$method = kb_get",
            "$oops = $_GET['x'] ?? 'boom';\n$method = kb_get"))
        probs = D.check_php56(self.site, self.base)
        self.assertTrue(any("??" in p_ for p_ in probs))

    # UC1.2
    def test_hyphen_id_detected(self):
        p = self.path("learn", "ascent", "course.json")
        m = json.load(open(p))
        m["units"][0]["sessions"][0]["id"] = "w1-s1"
        json.dump(m, open(p, "w"))
        probs = D.check_ids(self.site, self.base)
        self.assertTrue(any("hyphen" in p_ for p_ in probs))

    # UC1.3 — the Jim bug can never ship again
    def test_missing_content_detected(self):
        p = self.path("learn", "graceco", "course.json")
        m = json.load(open(p))
        m["units"][0]["sessions"].append({"id": "w9s9", "title": "Ghost"})
        json.dump(m, open(p, "w"))
        probs = D.check_manifests(self.site, self.base)
        self.assertTrue(any("w9s9" in p_ for p_ in probs))

    def test_soon_sessions_need_no_content(self):
        p = self.path("learn", "graceco", "course.json")
        m = json.load(open(p))
        m["units"][0]["sessions"].append({"id": "w9s9", "title": "Ghost", "soon": True})
        json.dump(m, open(p, "w"))
        self.assertEqual(D.check_manifests(self.site, self.base), [])

    # UC1.4
    def test_schema_violation_detected(self):
        p = self.path("learn", "ascent", "content", "w1s1.json")
        doc = json.load(open(p))
        doc["blocks"].append({"type": "dance_party", "html": "x"})
        doc["blocks"].append({"type": "q", "id": "zz",
                              "parts": [{"id": "a", "label": "x", "type": "numeric"}]})
        json.dump(doc, open(p, "w"))
        probs = D.check_schema(self.site, self.base)
        self.assertTrue(any("dance_party" in p_ for p_ in probs))
        self.assertTrue(any("no accept/range" in p_ for p_ in probs))

    # UC3.6 — the mergedDone bug class: stale assets vs fresh pages
    def test_unversioned_asset_detected(self):
        rel = D.code_version(self.site, self.base)
        p = self.path("learn", "app", "course.html")
        src = open(p).read()
        open(p, "w").write(src.replace("?v=" + rel, "", 1))  # strip one version tag
        probs = D.check_cache(self.site, self.base)
        self.assertTrue(any("unversioned" in x for x in probs), probs)

    def test_version_mismatch_detected(self):
        p = self.path("learn", "assets", "version.json")
        v = json.load(open(p)); v["version"] = "9.9.9"; json.dump(v, open(p, "w"))
        probs = D.check_cache(self.site, self.base)
        self.assertTrue(any("does not match code version" in x for x in probs), probs)

    # UC5 — the cache token is code-owned, so a code bump never edits content
    def test_cache_token_comes_from_code_not_content(self):
        reg = self.path("learn", "courses.json")
        before = open(reg, "rb").read()
        v = self.path("learn", "assets", "version.json")
        doc = json.load(open(v)); doc["version"] = "2.0.0"; json.dump(doc, open(v, "w"))
        for f in ("index.html", os.path.join("app", "course.html"),
                  os.path.join("app", "session.html")):
            p = self.path("learn", f)
            open(p, "w").write(open(p).read().replace("?v=1.0.0", "?v=2.0.0"))
        # bumping the engine leaves courses.json untouched and cache happy
        self.assertEqual(D.check_cache(self.site, self.base), [])
        self.assertEqual(open(reg, "rb").read(), before)

    # UC5 — compatibility rule: only a code MAJOR bump can invalidate content
    def test_compat_accepts_minor_and_patch_bumps(self):
        v = self.path("learn", "assets", "version.json")
        for bump in ("1.1.0", "1.0.7", "1.12.34"):
            doc = json.load(open(v)); doc["version"] = bump; json.dump(doc, open(v, "w"))
            probs = [x for x in D.check_compat(self.site, self.base) if "MAJOR" in x]
            self.assertEqual(probs, [], "%s should not break content" % bump)

    def test_compat_rejects_major_bump_without_content_update(self):
        v = self.path("learn", "assets", "version.json")
        doc = json.load(open(v)); doc["version"] = "2.0.0"; json.dump(doc, open(v, "w"))
        probs = D.check_compat(self.site, self.base)
        self.assertTrue(any("MAJOR" in x for x in probs), probs)
        # declaring the new major on the content side clears it
        reg = self.path("learn", "courses.json")
        r = json.load(open(reg)); r["requires_code"] = "2"; json.dump(r, open(reg, "w"))
        self.assertEqual([x for x in D.check_compat(self.site, self.base)
                          if "MAJOR" in x], [])

    def test_missing_code_version_file_is_not_a_silent_pass(self):
        # check_cache can only no-op when there is no token to compare against;
        # compat must then be the thing that shouts, or version drift rots
        os.remove(self.path("learn", "assets", "version.json"))
        self.assertEqual(D.check_cache(self.site, self.base), [])
        probs = D.check_compat(self.site, self.base)
        self.assertTrue(any("no code version file" in x for x in probs), probs)

    def test_compat_rejects_malformed_versions(self):
        v = self.path("learn", "assets", "version.json")
        doc = json.load(open(v)); doc["version"] = "r7"; json.dump(doc, open(v, "w"))
        self.assertTrue(any("not semantic" in x
                            for x in D.check_compat(self.site, self.base)))
        doc["version"] = "1.0.0"; json.dump(doc, open(v, "w"))
        reg = self.path("learn", "courses.json")
        r = json.load(open(reg)); r["version"] = "1.0.0"; json.dump(r, open(reg, "w"))
        self.assertTrue(any("is not rN" in x
                            for x in D.check_compat(self.site, self.base)))

    def test_missing_cache_header_detected(self):
        p = self.path("learn", ".htaccess")
        src = open(p).read()
        open(p, "w").write(src.replace("Cache-Control", "X-Nothing"))
        probs = D.check_cache(self.site, self.base)
        self.assertTrue(any("Cache-Control" in x for x in probs), probs)

    def test_receiver_results_page_exempt(self):
        # the receiver-generated results/index.html is allowed unversioned refs
        p = self.path("learn", "results", "index.html")
        self.assertIn("assets/base.css", open(p).read())
        self.assertEqual([x for x in D.check_cache(self.site, self.base)
                          if "results" in x], [])


if __name__ == "__main__":
    unittest.main()
