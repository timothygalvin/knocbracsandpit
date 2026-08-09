# Handoff brief — Unit 2 completion (first outsourced unit)

Paste everything below into a chat with the content agent (Opus 4.8),
with repo access or the referenced files attached.

---

You are producing course content for the Knocbrac Learning platform.
This is production work against an approved plan — not course design.

**Read, in order, before writing anything:**
1. `CLAUDE.md` — platform invariants and content schemas
2. `docs/CONTENT_GUIDE.md` — the methodology, per-student style sheets,
   hard rules, and the QA checklist you must return completed
3. Gold standards: `sites/knocbrac/learn/ascent/content/w1s2.json` and
   `.../graceco/content/w1s2.json` (match this voice and rhythm)
4. Context for continuity: each course's other Unit 1–2 sessions, the
   two course-plan PDFs, and each student's diagnostic results JSON
   (for unavenged rematch questions)

**Deliverables — four session files:**
- `ascent/content/w2s2.json` — "The Position Machine": the nth term
  proper. Builds on w2s1's shortcut (start + jumps × gap) and the
  dinner-table derivation; names nth term; function machines; fixes the
  diagnostic C1c gap (rule-writing) and I2 gap (variable as any-number).
  End boss: an nth-term rematch of the diagnostic sequence.
- `ascent/content/w2s3.json` — "Summit Puzzle: The Staircase": one rich
  session-long problem applying sequences (a staircase/growing-pattern
  investigation with an elegant nth-term payoff). Must include a ★★ and
  a summit block worthy of the dinner table.
- `graceco/content/w2s2.json` — "The Margin": profit as a percentage of
  cost (rematch: diagnostic B4 profit-% question), margin as the number
  that judges whether profit is good; compare two businesses with same
  £-profit, different margins. Grace style sheet applies strictly.
- `graceco/content/w2s3.json` — "Market Story: Losing Money on Purpose":
  story session delivering on w2s1's Amazon summit; growth vs profit;
  simple numbers; her verdict as analyst. Ends Unit 2 with a
  UNIT 2 COMPLETE done-screen (see w1s3 files for the pattern).

**Also update** both course manifests: w2s2/w2s3 lose their "soon" flags
(w2s2 first if you deliver in stages).

**Do NOT**: touch engine files, other courses, the receiver, release
numbers, or anything under tools/. Do not deploy.

**Definition of done:** all four files pass
`python3 tools/run_tests.py` (29+ green); every question part has
`_working` with a full derivation; the completed QA checklist from the
Content Guide is returned with the delivery; open questions escalated
rather than guessed.

Your first delivery gets a full review — write accordingly.
