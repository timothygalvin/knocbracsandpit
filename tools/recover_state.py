#!/usr/bin/env python3
"""Rebuild learner work from the family results folder.

Each finished session POSTs its full detail to the server — every question's
try count and every part's raw answer. So when a tablet loses its
localStorage, the work is recoverable: this reads the results files back and
reconstructs the exact state shape the session player uses
({answers, checked, skipped, cursor}, answers keyed "<question>.<part>").

    python3 tools/recover_state.py                 # report only
    python3 tools/recover_state.py --build         # write recovered/*.json

Then `tools/seed_state.py <course>` pushes it to the state store (code
1.1.0) so the tablet picks it up. recovered/ is gitignored: kids' answers.

Read-only against the server. Where a session was submitted more than once,
the most recent submission wins.
"""
import sys, os, re, json, urllib.request, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECOVERED = os.path.join(ROOT, "recovered")
SITE = "http://www.knocbrac.com/learn/results/"
NAME = re.compile(r"^([a-z]+)-([a-z0-9]+)-(session|checkpoint)-(\d{8})-(\d{6})\.json$")

def say(m): print(m, flush=True)

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "recover_state/1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")

def latest_per_session():
    """Newest submission for each (course, session)."""
    index = fetch(SITE + "index.html")
    files = sorted(set(re.findall(r'href="([^"]+\.json)"', index)))
    best = {}
    for f in files:
        m = NAME.match(f)
        if not m:
            say("  ?? skipping unparsed filename: %s" % f); continue
        course, session, _kind, d, t = m.groups()
        key = (course, session)
        if key not in best or (d, t) > best[key][0]:
            best[key] = ((d, t), f)
    return best

def to_state(doc, source):
    """Results detail -> the player's state shape."""
    answers, checked = {}, {}
    for item in doc.get("detail", []):
        q = item.get("q")
        if item.get("tries"):
            checked[q] = item["tries"]
        for p in item.get("parts", []):
            raw = p.get("raw", "")
            if raw != "":
                answers["%s.%s" % (q, p.get("part"))] = raw
        if item.get("skipped"):
            pass  # checkpoints only; skips are re-derived on load
    return {"answers": answers, "checked": checked, "skipped": {}, "cursor": 0,
            "_recovered_from": source, "_submitted": doc.get("when")}

def main():
    build = "--build" in sys.argv[1:]
    best = latest_per_session()
    if build:
        os.makedirs(RECOVERED, exist_ok=True)
    rows = collections.defaultdict(list)
    for (course, session), (_stamp, f) in sorted(best.items()):
        doc = json.loads(fetch(SITE + f))
        state = to_state(doc, f)
        if build:
            out = os.path.join(RECOVERED, "%s-%s.json" % (course, session))
            with open(out, "w", encoding="utf-8") as fh:
                json.dump(state, fh, indent=2, ensure_ascii=False)
        marks = [p.get("mark") for i in doc.get("detail", [])
                 for p in i.get("parts", [])]
        rows[course].append((session, doc.get("student"),
                             len(state["answers"]), len(state["checked"]),
                             marks.count("correct"), len(marks)))
    for course, items in sorted(rows.items()):
        say("\n== %s" % course)
        say("   %-8s %-6s %7s %9s %10s" %
            ("session", "who", "answers", "qs tried", "correct"))
        for s, who, na, nc, ok, tot in items:
            say("   %-8s %-6s %7d %9d %7d/%-4d" % (s, who, na, nc, ok, tot))
    say("\n%s %d session(s)%s" %
        ("wrote" if build else "found", len(best),
         " to recovered/" if build else " (--build to write them)"))

if __name__ == "__main__":
    main()
