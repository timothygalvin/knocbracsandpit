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


class StateStorePython(unittest.TestCase):
    """UC6 on the Python receiver, which needs no optional binary — so the
    state-sync logic is actually verified on every machine. submit.php is
    the live implementation and mirrors this; its own tests live in
    Receiver below and need php-cgi."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.base = os.path.join(self.tmp, "site")
        shutil.copytree(SITE_DIR, self.base)
        self.script = os.path.join(self.base, "learn", "api", "submit.py")
        self.results = os.path.join(self.base, "learn", "results")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def call(self, method="GET", body=b"", query=""):
        env = dict(os.environ, REQUEST_METHOD=method, QUERY_STRING=query)
        if method == "POST":
            env["CONTENT_TYPE"] = "application/json"
            env["CONTENT_LENGTH"] = str(len(body))
        r = subprocess.run([sys.executable, self.script], input=body, env=env,
                           capture_output=True, timeout=30)
        head, _, payload = r.stdout.partition(b"\r\n\r\n")
        return head.decode(errors="replace"), json.loads(payload.decode())

    def post_state(self, session="w2s2", answers=None, course="graceco"):
        return self.call("POST", json.dumps(
            {"kind": "state", "course": course, "session": session,
             "work": {"answers": answers or {"g1.a": "10"},
                      "checked": {"g1": 1}}}).encode())

    def test_state_round_trip(self):
        _h, j = self.post_state(answers={"g1.a": "10", "g2.b": "50"})
        self.assertTrue(j["ok"]); self.assertEqual(j["saved"], "w2s2")
        _h, j = self.call("GET", query="state=graceco")
        self.assertTrue(j["ok"])
        self.assertEqual(j["sessions"]["w2s2"]["answers"]["g2.b"], "50")
        self.assertEqual(j["sessions"]["w2s2"]["checked"]["g1"], 1)
        self.assertIn("savedAt", j["sessions"]["w2s2"])

    def test_state_accumulates_and_last_write_wins(self):
        self.post_state("w2s2", {"g1.a": "10"})
        self.post_state("w2s3", {"m1.a": "-20"})
        self.post_state("w2s2", {"g1.a": "99"})
        _h, j = self.call("GET", query="state=graceco")
        s = j["sessions"]
        self.assertEqual(sorted(s.keys()), ["w2s2", "w2s3"])
        self.assertEqual(s["w2s2"]["answers"]["g1.a"], "99")
        self.assertEqual(s["w2s3"]["answers"]["m1.a"], "-20")

    def test_courses_do_not_share_state(self):
        self.post_state("w2s2", {"g1.a": "10"}, course="graceco")
        self.post_state("w2s2", {"m1.a": "14"}, course="ascent")
        _h, g = self.call("GET", query="state=graceco")
        _h, a = self.call("GET", query="state=ascent")
        self.assertEqual(g["sessions"]["w2s2"]["answers"], {"g1.a": "10"})
        self.assertEqual(a["sessions"]["w2s2"]["answers"], {"m1.a": "14"})

    def test_empty_state_is_not_an_error(self):
        _h, j = self.call("GET", query="state=ascent")
        self.assertTrue(j["ok"]); self.assertEqual(j["sessions"], {})

    def test_state_never_pollutes_the_family_index(self):
        """The regression that would hurt most: state files live in the
        results folder and must never be read as submitted results."""
        self.post_state("w2s2")
        self.call("POST", json.dumps(
            {"course": "graceco", "student": "Grace", "kind": "session",
             "session": "w1s1", "title": "Test w1s1",
             "when": "2026-10-10T10:00:00", "detail": []}).encode())
        idx = open(os.path.join(self.results, "index.html")).read()
        self.assertIn("Test w1s1", idx)
        self.assertNotIn("state-", idx)
        self.assertTrue(os.path.exists(
            os.path.join(self.results, "state-graceco.json")))

    def test_state_cannot_escape_the_results_folder(self):
        _h, j = self.post_state(course="../../../etc/passwd")
        self.assertTrue(j["ok"])
        stray = [f for f in os.listdir(self.results) if f.startswith("state-")]
        self.assertEqual(stray, ["state-etcpasswd.json"],
                         "course id must be sanitised into the folder")

    def test_php_and_python_receivers_agree_on_the_contract(self):
        """Cheap guard against the two receivers drifting apart: both must
        name the file the same way, skip it in the index, and branch on
        kind == state."""
        php = open(os.path.join(self.base, "learn", "api", "submit.php"),
                   encoding="utf-8").read()
        py = open(self.script, encoding="utf-8").read()
        for token in ("state-", "'state'", "savedAt"):
            self.assertIn(token.strip("'"), php.replace('"', "'"),
                          "submit.php missing " + token)
        for token in ("state-", "state", "savedAt"):
            self.assertIn(token, py, "submit.py missing " + token)


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

    # ---- UC6: in-progress work survives a device change ----
    def _state(self, session="w2s2", answers=None, savedAt=None):
        return {"kind": "state", "course": "graceco", "session": session,
                "work": {"answers": answers or {"g1.a": "10"},
                         "checked": {"g1": 1}, "skipped": {}, "cursor": 0,
                         "savedAt": savedAt or "2026-10-10T12:00:00Z"}}

    def test_state_round_trip(self):
        _h, body = self.post(self._state(answers={"g1.a": "10", "g2.b": "50"}))
        j = json.loads(body)
        self.assertTrue(j["ok"]); self.assertEqual(j["saved"], "w2s2")
        _h, body = self.call("GET", query="state=graceco")
        j = json.loads(body)
        self.assertTrue(j["ok"])
        self.assertEqual(j["sessions"]["w2s2"]["answers"]["g2.b"], "50")
        self.assertEqual(j["sessions"]["w2s2"]["checked"]["g1"], 1)

    def test_state_accumulates_sessions_and_last_write_wins(self):
        self.post(self._state("w2s2", {"g1.a": "10"}))
        self.post(self._state("w2s3", {"m1.a": "-20"}))
        self.post(self._state("w2s2", {"g1.a": "99"}))       # same session again
        _h, body = self.call("GET", query="state=graceco")
        s = json.loads(body)["sessions"]
        self.assertEqual(sorted(s.keys()), ["w2s2", "w2s3"])
        self.assertEqual(s["w2s2"]["answers"]["g1.a"], "99")
        self.assertEqual(s["w2s3"]["answers"]["m1.a"], "-20")

    def test_state_is_stamped_server_side(self):
        _h, body = self.post(self._state(savedAt="not-a-date"))
        self.assertNotEqual(json.loads(body)["savedAt"], "not-a-date")

    def test_empty_state_is_not_an_error(self):
        _h, body = self.call("GET", query="state=ascent")
        j = json.loads(body)
        self.assertTrue(j["ok"]); self.assertEqual(j["sessions"], {})

    def test_state_never_pollutes_progress_or_the_family_index(self):
        """The regression that would hurt most: state files sharing the
        results folder must not be read as submitted results."""
        self.post(self._payload("w1s1"))          # one real result
        self.post(self._state("w2s2"))            # plus live work
        _h, body = self.call("GET", query="progress=graceco")
        self.assertEqual(json.loads(body)["done"], ["w1s1"])
        idx = open(os.path.join(self.results, "index.html")).read()
        self.assertIn("Test w1s1", idx)
        self.assertNotIn("state-", idx)
        # and the state file is not mistaken for a result file on disk
        self.assertTrue(os.path.exists(
            os.path.join(self.results, "state-graceco.json")))

    def test_state_cannot_escape_the_results_folder(self):
        evil = self._state(); evil["course"] = "../../../etc/passwd"
        _h, body = self.post(evil)
        self.assertTrue(json.loads(body)["ok"])
        stray = [f for f in os.listdir(self.results) if f.startswith("state-")]
        self.assertEqual(stray, ["state-etcpasswd.json"],
                         "course id must be sanitised into the folder")

    def test_invalid_json_rejected_politely(self):
        head, body = self.call("POST", b"this is not json")
        j = json.loads(body)
        self.assertFalse(j["ok"])

    def test_client_beacon_and_logtail(self):
        _h, body = self.post({"clientlog": "JS error: test beacon from unit test"})
        self.assertTrue(json.loads(body)["ok"])
        # beacon must not create a results file
        self.assertEqual([f for f in os.listdir(self.results) if f.endswith(".json")], [])
        # a real save gets logged too
        self.post(self._payload())
        _h, body = self.call("GET", query="logtail=1")
        j = json.loads(body)
        self.assertTrue(j["ok"])
        joined = "\n".join(j["lines"])
        self.assertIn("test beacon", joined)
        self.assertIn("SAVE graceco-w1s1", joined)
        # the log file defends itself from web execution
        log = open(os.path.join(self.base, "learn", "api", "receiver.log.php")).read()
        self.assertTrue(log.startswith("<?php exit; ?>"))

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
