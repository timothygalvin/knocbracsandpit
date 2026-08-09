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
        for name in self.site["checks"] + ["schema"]:
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

if __name__ == "__main__":
    unittest.main()
