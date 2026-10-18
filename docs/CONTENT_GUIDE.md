# Content Guide — producing sessions for Knocbrac Learning

For any agent (or human) writing course content. The Course Creation
Playbook covers designing whole courses from diagnostics; THIS file covers
the narrower, outsourceable job: **turning an approved unit plan into
session JSON files** that match the platform's voice and quality bar.

Read first: CLAUDE.md (schemas, invariants), one gold-standard session per
student — `ascent/content/w1s2.json` and `graceco/content/w1s2.json` are
the reference for tone, difficulty ramp, and block rhythm.

## Hard rules (non-negotiable)
1. **Touch only `sites/knocbrac/learn/<course>/`** — content files and that
   course's manifest. Never engine files, never the receiver, never another
   course. If the task seems to need more, stop and escalate.
2. **First names only.** No surnames, school names, locations, or family
   details anywhere in content, ids, or filenames.
3. **Ids**: no hyphens, pattern `w<week>s<session>`. Every non-"soon"
   manifest entry must have a content file (pre-flight enforces).
4. **Every question part carries a `"_working"` key** with the full
   derivation of every accepted answer. The engine ignores underscore keys;
   reviewers and tests depend on them. A session without workings is
   rejected unread.
5. Run `python3 tools/run_tests.py` before handing anything back. 29+
   green or it isn't done.

## The session shape (rhythm matters as much as content)
A session is 30–45 min and follows this arc — see the gold standards:

    read      one idea, grounded in the course's world, short
    q         warm-up in the comfort zone (early win)
    q         the idea in use
    reveal    the surprise — learner completes a pattern/story BEFORE the
              rule is stated ("the pattern doesn't care what we think")
    q         the idea now works harder
    q (boss)  hardest applied question, often multi-part
    q ★       optional stretch, genuinely hard, skippable with dignity
    summit    dinner-table block: discussable with a human, open-ended,
              plants the seed for the next session
    done      names what was gained + teases what's next

House patterns, used deliberately:
- **Rematch**: questions the student missed on the diagnostic reappear as
  boss questions, labelled as rematches ("this exact question was on your
  diagnostic"). Check the course plan for which misses remain unavenged.
- **Reveal**: rules are forced by pattern or story, never handed down.
- **Summit**: the human conversation is the engine; the platform is the
  truck. Every summit must be genuinely worth discussing at dinner.
- **Continuity**: reference earlier sessions' skills paying off ("Unit 1's
  negatives, earning their keep").

## Plain English (hard rule, added 2026-10 after a real failure)
Write for a ten-year-old reading on a tablet with no adult beside them.
**No LLM-style shorthand or jargon.** Specifically banned in anything a
learner reads (prompt, label, hint, read/reveal text):
- arrows for change or calculation — `revenue £50 → £100`, `60 → 6`.
  Write the sentence: "in year 1 it makes £50, and in year 2 it makes
  £100"; "the digits slide one place, so 60 becomes 6".
- label-colon data lines — `**A:** costs £40, margin 50%`. Write
  "Business A spends £40, and its margin is 50%".
- fill-in-the-blank underscores in a form label — `The revenue is ___`.
  Ask the question: "What is the revenue doing each year? (one word)".
- bare negative currency in a list of figures (`Tue −£5`) unless the
  minus sign is itself what the session is teaching at that moment.
**Tabular data gets prose AND a table** — the sentences first, then the
table so the numbers can be compared at a glance. Never the table alone.
Use the inline-styled pattern in graceco w2s1–w2s3 (`overflow-x:auto`
wrapper, `var(--accent)` header rule, `var(--track)` row rules) — it is
deliberately content-only, so a clarity fix never needs an engine release.
Short sentences are a rule about *sentence construction*, not a licence
to explain less: Grace's sessions ran at a third of Jim's teaching words
per question, which is how this went wrong.

## Per-student style sheets

### Jim (ascent — The Ascent, climbing world)
- Year 5, working at Y7–8 when reasoning is rewarded. Pitch at productive
  struggle, not comfort. He likes SURPRISE: patterns with stings, ideas
  from above his year smuggled in with a name-drop ("you've just met a
  Year 8 idea").
- Trial-and-error is his instinct — honour it, then show the tool that
  beats it. Loves elegance; summit puzzles should have elegant solutions.
- Chemistry/biology hooks land (Unit 3 uses mixtures). Avoid coding-based
  framings. Sentences can be full; wit welcome.

### Grace (graceco — Grace & Co., money & markets world)
- Year 5, consolidating Y5/6, self-aware about percentages. Early wins
  first, always. She is sharp about PEOPLE and MONEY: every question
  should have a commercial reason to exist; "analyst" framing empowers.
- **Accessibility is load-bearing**: short sentences. One idea per line.
  Big round numbers where the maths allows. Prose answers optional —
  prefer numeric parts or short text with generous accept lists. Never
  grade spelling.
- Loss/debt/negatives connect to her contagion knowledge — use it.
- Sessions ~35 min; a strong 35 beats a fading 45.

## Marking-engine notes (read CLAUDE.md schemas first)
- Numeric accepts: engine normalises £/€/%, fractions, mixed numbers.
  Probability parts MUST set `"pctOk": true` (bare "50" = 50%).
- Text accepts: lower-cased, spaces stripped, ×/* → x. Be GENEROUS:
  include ×-variants, common phrasings ("same","thesame","equal"...).
  A too-narrow list marks a right child wrong — the worst failure.
- Numeric parts require accept or range (schema check enforces).
- Hints appear after 2 failed tries: hints scaffold the METHOD, never
  reveal the answer.

## QA checklist (attach to every delivery)
- [ ] Every accepted answer re-derived independently in `_working`
- [ ] Every hint tested: helps method, doesn't leak answer
- [ ] Accept lists generous (units, %, word variants)
- [ ] Rematches labelled and cross-checked against the course plan
- [ ] Reveal earns its surprise; summit is genuinely discussable
- [ ] Grace only: sentence length, big text friendliness, no prose burden
- [ ] Manifest updated (new session live, next ones "soon": true)
- [ ] run_tests.py green; content `version` (rN) in courses.json bumped if
      shipping. Content releases never touch ?v= or any engine file — that
      token belongs to the code artefact (CLAUDE.md § Versioning)
- [ ] Done-screen names the gain and teases the next session

## Review protocol for new agents
First unit from any new content agent gets a full human/senior review
before deploy. After a clean first unit, review drops to spot checks of
`_working` and the summit blocks. Steering decisions — reading checkpoint
results, reordering units, changing course plans — are NOT content work;
escalate those.
