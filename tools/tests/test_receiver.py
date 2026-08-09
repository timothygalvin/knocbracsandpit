"""UC2 acceptance tests — receiver behaviour and marking engine.
These need optional binaries (php-cgi, node) and SKIP with a reason when
absent, per use_cases.md 2.1.
"""
import unittest, os, sys, json, shutil, tempfile, subprocess

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO  = os.path.dirname(TOOLS)
SITE_DIR = os.path.join(REPO, "sites", "knocbrac")

HAVE_PHPCGI = shutil.which("php-cgi") is not None
HAVE_NODE   = shutil.which("node") is not None


@unittest.skipUnless(HAVE_PHPCGI, "php-cgi not installed — receiver tests skipped")
class Receiver(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.base = os.path.join(self.tmp, "site")
        shutil.copytree(SITE_DIR, self.base)
        self.script = os.path.join(self.base, "learn", "api", "submit.php")
        self.results = os.path.join(self.base, "learn", "results")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def call(self, method="GET", body=b"", query=""):
        env = dict(os.environ, REQUEST_METHOD=method,
                   SCRIPT_FILENAME=self.script, REDIRECT_STATUS="1",
                   QUERY_STRING=query)
        if method == "POST":
            env["CONTENT_TYPE"] = "application/json"
            env["CONTENT_LENGTH"] = str(len(body))
        r = subprocess.run(["php-cgi"], input=body, env=env,
                           capture_output=True, timeout=30)
        head, _, payload = r.stdout.partition(b"\r\n\r\n")
        return head.decode(errors="replace"), payload.decode(errors="replace")

    def post(self, obj):
        return self.call("POST", json.dumps(obj).encode())

    def _payload(self, session="w1s1"):
        return {"course": "graceco", "student": "Grace", "kind": "session",
                "session": session, "title": "Test " + session,
                "when": "2026-08-01T10:00:00",
                "detail": [{"q": "p1", "parts":
                            [{"part": "a", "raw": "6", "mark": "correct"}]}]}

    # UC2.4
    def test_round_trip_save_index_response(self):
        head, body = self.post(self._payload())
        j = json.loads(body)
        self.assertTrue(j["ok"])
        self.assertTrue(os.path.exists(os.path.join(self.results, j["file"])))
        idx = open(os.path.join(self.results, "index.html")).read()
        self.assertIn("Grace", idx)
        self.assertIn("Test w1s1", idx)

    def test_alive_check(self):
        _h, body = self.call("GET")
        j = json.loads(body)
        self.assertFalse(j["ok"])
        self.assertIn("receiver alive", j["status"])

    def test_progress_endpoint(self):
        self.post(self._payload("w1s1"))
        self.post(self._payload("w1s2"))
        _h, body = self.call("GET", query="progress=graceco")
        j = json.loads(body)
        self.assertTrue(j["ok"])
        self.assertEqual(sorted(j["done"]), ["w1s1", "w1s2"])

    def test_invalid_json_rejected_politely(self):
        head, body = self.call("POST", b"this is not json")
        j = json.loads(body)
        self.assertFalse(j["ok"])

    # UC2.5 — every response is HTTP 200 (ErrorDocument-proof)
    def test_all_responses_are_200(self):
        for head, _b in [self.call("GET"),
                         self.call("POST", b"not json"),
                         self.post(self._payload())]:
            self.assertNotIn("Status:", head,
                             "receiver must not set an error status: " + head)


@unittest.skipUnless(HAVE_NODE, "node not installed — marking-engine tests skipped")
class MarkingEngine(unittest.TestCase):
    """UC2.3 — drive shared.js's KB.markPart through node."""
    def run_js(self, cases):
        shared = os.path.join(SITE_DIR, "learn", "assets", "shared.js")
        stub = (
            "globalThis.location={pathname:'/learn/app/x.html',search:''};"
            "globalThis.document={querySelector:()=>null,createElement:()=>({classList:{add:()=>{}},style:{}}),"
            "body:{appendChild:()=>{},classList:{add:()=>{},toggle:()=>{},contains:()=>false}},"
            "documentElement:{style:{setProperty:()=>{}}}};"
            "globalThis.localStorage={getItem:()=>null,setItem:()=>{}};")
        js = (stub +
              "eval(require('fs').readFileSync(%r,'utf8').replace('const KB','globalThis.KB'));"
              "const cases=%s;"
              "console.log(JSON.stringify(cases.map(c=>KB.markPart(c.part,c.raw))));"
              % (shared, json.dumps(cases)))
        r = subprocess.run(["node", "-e", js], capture_output=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        return json.loads(r.stdout.decode())

    def test_documented_verdicts(self):
        cases = [
            {"part": {"type": "numeric", "accept": [4.2]},  "raw": "£4.20"},
            {"part": {"type": "numeric", "accept": [1.375]},"raw": "1 3/8"},
            {"part": {"type": "numeric", "accept": [0.5]},  "raw": "1/2"},
            {"part": {"type": "numeric", "accept": [0.5], "pctOk": True}, "raw": "50"},
            {"part": {"type": "numeric", "accept": [0.5]},  "raw": "50"},
            {"part": {"type": "numeric", "accept": [-5]},   "raw": "-5"},
            {"part": {"type": "numeric", "range": [31.4, 31.42]}, "raw": "31.41"},
            {"part": {"type": "text", "accept": ["3n+2", "2+3n"]}, "raw": "3 × n + 2"},
            {"part": {"type": "text", "accept": ["3n+2", "3xn+2"]}, "raw": "3 × n + 2"},
            {"part": {"type": "text", "accept": ["да"]},    "raw": "ДА"},
            {"part": {"type": "numeric", "accept": [6]},    "raw": ""},
        ]
        # narrow accept-list -> "review" (human eye, never auto-wrong);
        # generous list incl. the ×-variant -> "correct". Playbook rule.
        expect = ["correct", "correct", "correct", "correct", "incorrect",
                  "correct", "correct", "review", "correct", "correct", "blank"]
        self.assertEqual(self.run_js(cases), expect)


if __name__ == "__main__":
    unittest.main()
