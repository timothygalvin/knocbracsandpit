#!/usr/bin/env python3
"""Seed server-side learner state from recovered results.

Why this exists: in-progress work used to live only in a tablet's
localStorage, so clearing browser data lost every typed answer while the
course map still showed ticks (those sync from the results folder). Jim
hit exactly that. The answers were never truly gone — each finished
session POSTs its full detail to the family folder — so this rebuilds the
work from those results and pushes it into the state store added in code
1.1.0, after which the tablet picks it up on next load (KB.bestWork).

    python3 tools/recover_state.py --build          # results -> recovered/
    python3 tools/seed_state.py ascent --dry-run       # show what would seed
    python3 tools/seed_state.py ascent                 # push it

Requires code 1.1.0 to be deployed (the ?state= endpoint). Safe to re-run:
the store is keyed by session, so seeding overwrites only those sessions.
Nothing here is destructive to results files.
"""
import sys, os, json, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECOVERED = os.path.join(ROOT, "recovered")
ENDPOINT = "http://www.knocbrac.com/learn/api/submit.php"

def say(m): print(m, flush=True)

def states_for(course):
    """Recovered per-session state files for one course."""
    if not os.path.isdir(RECOVERED):
        raise SystemExit("no recovered/ directory — run recover_state.py first")
    out = {}
    for f in sorted(os.listdir(RECOVERED)):
        if not (f.startswith(course + "-") and f.endswith(".json")):
            continue
        session = f[len(course) + 1:-len(".json")]
        with open(os.path.join(RECOVERED, f), encoding="utf-8") as fh:
            out[session] = json.load(fh)
    return out

def push(course, session, work, tries=3, timeout=90):
    """Seeding is idempotent (keyed by session), so a timeout is always
    safe to retry — and this host gets throttled, which is exactly how the
    first live run lost one session."""
    body = json.dumps({"kind": "state", "course": course,
                       "session": session, "work": work}).encode()
    last = None
    for attempt in range(1, tries + 1):
        req = urllib.request.Request(ENDPOINT, data=body,
                                     headers={"Content-Type": "application/json",
                                              "User-Agent": "seed_state/1"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:
            last = e
            if attempt < tries:
                say("    (attempt %d/%d failed: %s — retrying)"
                    % (attempt, tries, type(e).__name__))
    raise last

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv[1:]
    if not args:
        raise SystemExit("usage: seed_state.py <course> [--dry-run]")
    course = args[0]
    states = states_for(course)
    if not states:
        raise SystemExit("nothing recovered for course %r" % course)
    say("=== seeding %s: %d session(s) ===" % (course, len(states)))
    for session, work in sorted(states.items()):
        n = len(work.get("answers", {}))
        if dry:
            say("  would seed %-6s %d answer(s) (from %s)"
                % (session, n, work.get("_recovered_from", "?")))
            continue
        try:
            r = push(course, session, work)
            say("  %-6s %d answer(s) -> %s"
                % (session, n, "ok" if r.get("ok") else r))
        except Exception as e:
            say("  %-6s FAILED: %s: %s" % (session, type(e).__name__, e))
    if dry:
        say("— dry run: nothing sent —")
    else:
        say("Now open a session on the tablet: KB.bestWork pulls this back.")

if __name__ == "__main__":
    main()
