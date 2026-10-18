# Handoff brief — two new language courses (DIAGNOSTIC STAGE)

For a **senior/steering agent (Fable)**, not a content agent. This is
course *design* from a standing start: deciding what to assess and why,
which is explicitly escalation territory in `docs/CONTENT_GUIDE.md`
("Steering decisions — reading checkpoint results, reordering units,
changing course plans — are NOT content work"). Session production comes
after, as a separate content brief.

Paste everything from the line below into a chat with the senior agent,
with repo access.

---

You are designing the diagnostic stage for two new Knocbrac Learning
courses:

- **Grace's Spanish** — Grace is 10, Year 5, consolidating Y5/6. Her
  style sheet in `docs/CONTENT_GUIDE.md` is load-bearing, not advisory:
  short sentences, one idea per line, early wins, `bigText` on, never
  grade spelling. Her existing course is `graceco` (money and markets).
  Likely course id: `gracees`.
- **Timothy's Russian** — an adult learner. No prior adult course exists
  on this platform, so the pitch, session length and tone are yours to
  propose. `Russian_Kickoff_Prompt.md` exists in the claude.ai project
  files; treat it as input, not gospel.

**Read, in order, before designing anything:**
1. `CLAUDE.md` — platform invariants and the content schemas, especially
   `kind:"checkpoint"`.
2. `docs/CONTENT_GUIDE.md` — methodology, the plain-English hard rule,
   per-student style sheets, the QA checklist.
3. `docs/use_cases.md` — what the repo guarantees and which test proves
   each guarantee. Do not propose anything that breaks a listed criterion.
4. `Course_Creation_Playbook.md` (claude.ai project files) — designing
   whole courses from diagnostics, including its language addendum.
5. For tone and difficulty-ramp calibration: `ascent/content/w2s3.json`
   and `graceco/content/w2s2.json`.

## Use the platform's checkpoint engine, not a standalone app

The original maths and money diagnostics were bespoke HTML
(`Maths_Ascent_Jim_v4.html`, `Money_Makers_Grace_v2.html`). **Do not do
that again.** The platform now has `kind:"checkpoint"`: paged, skippable,
deferred marking, results posted to the family folder automatically. A
diagnostic authored as a checkpoint costs ZERO engine work, inherits the
theming and the Aa text toggle, and its results land where every other
result lands.

Schema is in `CLAUDE.md`. In short: `{id, kind:"checkpoint", title,
sections:[{id, name, intro?, questions:[{id, level, prompt, parts:[...]}]}]}`,
where a `type:"text"` part with no `accept` list becomes a human-reviewed
"review" answer — which is how you capture free writing without pretending
to mark it.

Marking-engine facts that matter for languages:
- Cyrillic and accented Latin text pass through the engine unharmed.
- `normText` lowercases, strips spaces and parentheses, maps `×` `*` `·`
  to `x`. It does NOT normalise accents, so `está` and `esta` are
  different strings — put both in `accept`, every time.
- A trailing `%` is read as a division by 100. Irrelevant here, but it is
  the trap that has bitten this codebase twice.
- Text parts that miss their `accept` list mark as "review", not "wrong".
  Use that deliberately: it is the difference between assessing and
  judging.
- **Never grade spelling for Grace.** For an adult Russian course,
  spelling IS the skill — so be explicit per part about which it is.

## What spoken language needs that the engine cannot do

Neither course can be assessed on reading and writing alone, and the
platform has no audio. So each diagnostic needs two pieces:

1. The **written checkpoint** (above), which the engine marks and stores.
2. A **human oral protocol** — a short script a parent or tutor runs
   aloud, with a simple scoring sheet. This is a committed markdown
   document, not a chat artefact. Say plainly in it what cannot be
   assessed without a human, so nobody mistakes the written score for the
   whole picture.

Per-question audio is a known platform gap, parked in `docs/TODO.md`
("needs asset hosting thought — keep static"). Do not design around audio
that does not exist; if you believe the courses need it, say so as a
recommendation with a cost.

## The requirement that exists because we lost the last one

The original diagnostic design for the maths and money courses was
deliberated in a claude.ai chat **that no longer exists** — those chats are
purged on a retention window, and the local JSONL backup
(`timothygalvin/tpc/SESSIONS.md`) was only set up afterwards. The
artefacts survived, in the Playbook and the live courses; the *reasoning*
did not. This is a known, registered failure mode:
`decision-provenance` in
`agileintegrator/home-agent-system/architecture/open-concepts.md`, open
since 13 Jul 2026.

So, non-negotiably, **the design must land in this repo as committed
files, not in the conversation**:

- `docs/plans/<course>-diagnostic.md` — what is being assessed and **why**,
  the level bands, what each question is diagnostic *of*, what a given
  answer would tell you about the learner, and the decision trail: options
  you considered and rejected, with reasons. A future reader must be able
  to reconstruct your thinking without the chat.
- `sites/knocbrac/learn/<course>/content/<id>.json` — the checkpoint
  itself, `kind:"checkpoint"`, every part carrying `_working`.
- `docs/plans/<course>-oral-protocol.md` — the human script and scoring
  sheet.
- `docs/plans/<course>-rubric.md` — how to read the results into a unit
  plan, so the next person (or agent) can steer without you.

If it only exists in the chat, treat it as lost already.

## Hard constraints

- A new course is **one folder plus one entry in `courses.json`** —
  `{id, student, title, tagline, icon, theme:{accent, soft, warm, bigText}}`.
  If your design needs an engine change, stop and escalate: that is a code
  release on a separate path, and it is not yours to make.
- **Ids contain no hyphens** (`gracees`, `w1s1`). The progress endpoint
  parses results filenames by splitting on hyphens.
- **First names only** in content, ids, filenames and results.
- `requires_code` in `courses.json` names the code MAJOR the content
  targets. Current code is `1.x`; content is `rN`. A content release never
  touches an engine file or the `?v=` tokens.
- Run `python3 tools/run_tests.py` and
  `python3 tools/deploy.py knocbrac --check` before handing back. Do not
  deploy; do not bump versions; do not touch `ascent` or `graceco`.
- Register new sessions in the manifest with `"soon": true` so pre-flight
  stays green while content is still being written.

## Definition of done

The four documents above, committed; the checkpoint passing pre-flight;
the completed QA checklist from the Content Guide; and an explicit list of
the design decisions you made, each with the reason, so Timothy can
overrule any of them cheaply. Open questions escalated, never guessed —
particularly anything about Grace's school Spanish curriculum or
Timothy's actual Russian starting point, neither of which is in the repo.
