#!/usr/bin/env python3
"""Knocbrac Learning — results receiver (Python CGI edition).
NOTE: as of r3 the PRIMARY receiver is submit.php, which needs no CGI setup.
This script is kept as a fallback for hosts without PHP. Same behaviour:
accepts a JSON POST, saves it into the results folder, rebuilds
results/index.html, and emails a notification. Stdlib only.
Email settings live in config.txt next to this script.
"""
import sys, os, json, re, html
from datetime import datetime

# ---- configuration: edit api/config.txt, NOT this file ----
NOTIFY_EMAIL = "timothy@knocbrac.com"
FROM_EMAIL   = "learning@knocbrac.com"
def _load_config():
    global NOTIFY_EMAIL, FROM_EMAIL
    try:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.txt")
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line.startswith("NOTIFY_EMAIL="):
                    NOTIFY_EMAIL = line.split("=", 1)[1].strip()
                elif line.startswith("FROM_EMAIL="):
                    FROM_EMAIL = line.split("=", 1)[1].strip()
    except Exception:
        pass  # missing config file: defaults above apply
# ------------------------------------------------------------

MAX_BYTES = 300_000
HERE      = os.path.dirname(os.path.abspath(__file__))
def _results_dir():
    """Work from learn/api/ OR from a cgi-bin/ anywhere on the account."""
    rel = os.path.normpath(os.path.join(HERE, "..", "results"))
    if os.path.isdir(rel):
        return rel
    droot = os.environ.get("DOCUMENT_ROOT", "")
    cand = os.path.join(droot, "learn", "results")
    if droot and os.path.isdir(cand):
        return cand
    return rel  # will be created on save if possible
RESULTS_DIR = _results_dir()

def respond(obj, status="200 OK"):
    body = json.dumps(obj)
    sys.stdout.write("Status: %s\r\nContent-Type: application/json\r\n"
                     "Cache-Control: no-store\r\nContent-Length: %d\r\n\r\n%s"
                     % (status, len(body.encode()), body))
    sys.stdout.flush()
    sys.exit(0)

def clean(s, fallback):
    s = re.sub(r"[^a-z0-9_-]", "", str(s or "").lower())
    return s[:40] or fallback

def send_mail(subject, text):
    msg = ("From: Knocbrac Learning <%s>\r\nTo: %s\r\nSubject: %s\r\n"
           "Content-Type: text/plain; charset=utf-8\r\n\r\n%s"
           % (FROM_EMAIL, NOTIFY_EMAIL, subject, text))
    try:  # preferred on shared hosting
        import subprocess
        p = subprocess.run(["/usr/sbin/sendmail", "-t", "-oi"],
                           input=msg.encode(), timeout=15)
        if p.returncode == 0:
            return True
    except Exception:
        pass
    try:  # fallback: local SMTP
        import smtplib
        with smtplib.SMTP("localhost", 25, timeout=15) as s:
            s.sendmail(FROM_EMAIL, [NOTIFY_EMAIL], msg.encode())
        return True
    except Exception:
        return False

def rebuild_index():
    files = sorted((f for f in os.listdir(RESULTS_DIR) if f.endswith(".json")),
                   reverse=True)
    rows = []
    for f in files:
        try:
            with open(os.path.join(RESULTS_DIR, f), encoding="utf-8") as fh:
                d = json.load(fh)
            label = "%s — %s (%s)" % (d.get("student", "?"),
                                      d.get("title", d.get("session", "?")),
                                      d.get("kind", "session"))
            when = d.get("when", "")[:16].replace("T", " ")
        except Exception:
            label, when = f, ""
        rows.append('<li><a href="%s" download>%s</a> <span class="sub">%s</span></li>'
                    % (html.escape(f), html.escape(label), html.escape(when)))
    page = """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow"><title>Results — family folder</title>
<link rel="stylesheet" href="../assets/base.css"></head><body><div class="wrap">
<h1>Family results folder</h1>
<p class="sub">Newest first. Tap to download a file, then upload it to Claude to build the next course block.</p>
<div class="card"><ul style="line-height:2.2">%s</ul></div>
<p class="grownup"><a href="../index.html">&larr; Back to Knocbrac Learning</a></p>
</div></body></html>""" % ("\n".join(rows) or "<li>Nothing here yet.</li>")
    with open(os.path.join(RESULTS_DIR, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(page)

def main():
    _load_config()
    if os.environ.get("REQUEST_METHOD") != "POST":
        respond({"ok": False, "error": "POST only"}, "405 Method Not Allowed")
    try:
        n = int(os.environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        n = 0
    if n <= 0 or n > MAX_BYTES:
        respond({"ok": False, "error": "bad size"}, "400 Bad Request")
    try:
        data = json.loads(sys.stdin.buffer.read(n).decode("utf-8"))
    except Exception:
        respond({"ok": False, "error": "invalid JSON"}, "400 Bad Request")

    course  = clean(data.get("course"), "course")
    kind    = clean(data.get("kind"), "session")
    session = clean(data.get("session"), "s")
    stamp   = datetime.now().strftime("%Y%m%d-%H%M%S")
    fname   = "%s-%s-%s-%s.json" % (course, session, kind, stamp)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, fname), "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)

    try:
        rebuild_index()
    except Exception:
        pass

    student = str(data.get("student", "?"))[:40]
    title   = str(data.get("title", session))[:80]
    correct = skipped = total = 0
    for d in data.get("detail", []):
        for p in d.get("parts", []):
            total += 1
            if p.get("mark") == "correct": correct += 1
            if p.get("mark") == "skipped": skipped += 1
    emailed = send_mail(
        "Knocbrac Learning: %s finished \"%s\"" % (student, title),
        "%s has just finished \"%s\" (%s).\n\n"
        "Quick tally: %d of %d parts correct, %d skipped.\n\n"
        "Full results: https://www.knocbrac.com/learn/results/\n"
        "File: %s\n\n— Knocbrac Learning" % (student, title, kind, correct, total, skipped, fname))

    respond({"ok": True, "file": fname, "emailed": emailed})

if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        respond({"ok": False, "error": "server error: %s" % e}, "500 Internal Server Error")
