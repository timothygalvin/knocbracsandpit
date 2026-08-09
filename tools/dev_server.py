#!/usr/bin/env python3
"""Local test server for the learning platform (repo layout).

Run from anywhere:   python3 tools/dev_server.py
Serves sites/knocbrac/ at http://localhost:8000/ → open /learn/
POSTs to the receiver run the Python fallback so the full loop works
locally (saves land in sites/knocbrac/learn/results/). Emails don't send
from a home machine.
"""
import http.server, subprocess, os, sys

PORT   = 8000
TOOLS  = os.path.dirname(os.path.abspath(__file__))
ROOT   = os.path.dirname(TOOLS)
DOCROOT = os.path.join(ROOT, "sites", "knocbrac")

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=DOCROOT, **kw)
    def do_POST(self):
        p = self.path.rstrip("/")
        if not (p.endswith("/api/submit.py") or p.endswith("/api/submit.php")
                or p.endswith("/cgi-bin/submit.cgi") or p.endswith("/cgi-bin/submit.py")):
            self.send_error(405, "POST only goes to the results receiver")
            return
        script = os.path.join(DOCROOT, "learn", "api", "submit.py")
        length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(length)
        env = dict(os.environ, REQUEST_METHOD="POST",
                   CONTENT_LENGTH=str(length),
                   CONTENT_TYPE=self.headers.get("Content-Type", ""),
                   DOCUMENT_ROOT=DOCROOT)
        try:
            r = subprocess.run([sys.executable, script], input=body, env=env,
                               capture_output=True, timeout=30)
            head, _, payload = r.stdout.partition(b"\r\n\r\n")
            status, ctype = 200, "application/json"
            for line in head.decode(errors="replace").split("\r\n"):
                if line.lower().startswith("status:"):
                    status = int(line.split()[1])
                elif line.lower().startswith("content-type:"):
                    ctype = line.split(":", 1)[1].strip()
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except Exception as e:
            self.send_error(500, "receiver failed: %s" % e)
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

if __name__ == "__main__":
    print("Knocbrac dev server → http://localhost:%d/learn/" % PORT)
    print("Ctrl+C to stop.")
    http.server.ThreadingHTTPServer(("", PORT), Handler).serve_forever()
