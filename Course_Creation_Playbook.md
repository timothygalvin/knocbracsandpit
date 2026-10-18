# Course Creation Playbook — Knocbrac Learning

The repeatable process behind The Ascent (Jim) and Grace & Co. (Grace).
Use it to spin up any new course: Timothy's Russian, Grace's Spanish, whatever
comes next. Each step names its deliverable. Technical details live in
CLAUDE.md; this file is the process.

## Step 0 — Define the learner and the goal
Fill this in before anything else:

    LEARNER:        (name, age/stage, relevant traits e.g. dyslexia-friendly
                     design needed, attention pattern, device)
    DOMAIN:         (e.g. maths, Spanish, Russian)
    STARTING POINT: (what's known/suspected about current level)
    GOAL:           (what "working" looks like in 10 weeks)
    MOTIVATION:     (what the learner actually cares about — the theme and
                     framing come from here, not from the subject)
    TIME BUDGET:    (hours/week, session length that fits their focus)
    CONSTRAINTS:    (household/tech constraints; self-serve requirement?)

## Step 1 — Design the diagnostic
- Pick 4–9 strands that between them cover the domain.
- Each strand ramps through 3–4 difficulty levels (kids: school years;
  adults/languages: CEFR-style A0→B1 or similar). The top level should be
  genuinely out of reach — "built to be too hard to finish" is stated up
  front and skipping is framed as information, not failure.
- Include an enjoyment rating per strand (1–5) and 2 free-text survey
  questions: favourite question + what do you want to learn. The survey
  drives tailoring as much as the scores do.
- Theme the whole thing in the learner's motivation language (climbing for
  Jim, company-building for Grace). Never generic.
- For languages: the written diagnostic covers script, vocabulary, grammar
  and reading. Speaking/listening is assessed separately in a live chat
  with Claude (see the language addendum below).
  Deliverable: a self-contained assessment web app using the platform's
  checkpoint schema (see CLAUDE.md), with save/resume and results export.

## Step 2 — Run it, then interpret
Feed the exported results JSON back to Claude. The reading looks for:
- Per-strand top-out: last level comfortable, first level of struggle,
  first out of reach. Course pitches at the struggle point.
- Method, not just marks: right answers by trial-and-error vs by tooling
  tell different stories. Read the free-text working.
- Ability–enjoyment gaps both ways: high skill + low joy → defer and
  re-enter through an interest; low skill + high joy → lead with it.
- The learner's own words in the survey — self-named gaps are gold
  (Grace named percentages herself; that became Unit 1).
- Marking artefacts: check "incorrect" answers for format issues before
  believing them (Grace's bare "50" for 50%).
  Deliverable: a short findings summary + strand/priority table.

## Step 3 — The course plan
- ~10 weeks, ~5 units, ordered so early wins land fast (open with either
  a quick unlock or the learner's self-named gap).
- Weekly rhythm sized to the learner's focus (3 × 30–40 min for Grace;
  3 × 45–60 for Jim). Name the session types — every course has:
  (a) a new-idea session, (b) a practice session woven into the theme,
  (c) a discussion/story session designed to be talked about with a
  human afterwards. The human conversation is the engine; the platform
  is the truck.
- Schedule checkpoints (reusing the assessment engine) after ~unit 2 and
  ~unit 4, plus a final. Same ids scheme: <course>-checkpoint-1 etc.
- Note accommodations explicitly (text size, sentence length, oral
  answers instead of written, etc.).
  Deliverable: a course-plan PDF (see the two existing plans for the shape:
  findings → strand table → architecture → unit-by-unit → notes for the
  supervising adult, titled "Notes for Timothy").

## Step 4 — Produce sessions iteratively
- Write 1–2 sessions at a time, deploy, watch results, adjust. Never
  batch-produce the whole course: the results files steer.
- The rematch pattern: questions missed on the diagnostic reappear as
  boss questions in sessions, labelled as rematches. Learners love
  beating a question that beat them.
- The reveal pattern: new rules are forced by a pattern or story the
  learner completes themselves, never handed down ("the pattern doesn't
  care what we think should happen next").
- Every session ends with a summit/market-story block for the dinner
  table, and a done-screen that names what was just gained and teases
  the next session.
- Placeholder sessions in the manifest get "soon": true so they're
  visibly coming but locked.
## Language-course addendum
- Written diagnostic strands: script/reading fluency, core vocabulary,
  grammar (for Russian: cases and verb aspect are the spine), reading
  comprehension, short writing/translation.
- Oral diagnostic: a separate live conversation with Claude in the
  target language, graduated from greetings up to open conversation,
  with Claude switching to English to debrief. Findings merge with the
  written results in Step 2.
- Marking: the engine's text-matching handles Cyrillic/accented input
  fine (answers are normalised lower-case, spaces stripped), but keep
  accept-lists generous for spelling variants, and prefer multiple
  shorter answers over long free text.
- Check display fonts support the script before shipping (Nunito covers
  Cyrillic; verify any display font or fall back to system).