# Timothy's Russian — diagnostic design (`vozvrat/content/diag.json`)

> Status: DESIGNED, not yet deployed · 2026-10-18
> Designed by: Fable (senior agent), from
> `docs/handoff/LANGUAGE_DIAGNOSTICS_PROMPT.md` +
> `Russian_Kickoff_Prompt.md` (input, not gospel) + Timothy's answers
> in-session (2026-10-18).
> Companion docs: `vozvrat-oral-protocol.md`, `vozvrat-rubric.md`.
> This file carries the decision trail (`decision-provenance`).

## The learner, as known on design day

Timothy, adult, self-directed, technically comfortable, happy to be
pushed. **Lived in Russia two years**, took lessons, found the
grammar hard. Self-report (2026-10-18): can make himself understood;
comprehension limited to basic phrases and questions; reads Cyrillic,
reading was his stronger skill; ~1 year since last real use, "very
rusty". Time budget: 15 min/day + 1 h at the weekend.

**Level contradiction, escalated and resolved as follows.** The
self-assessments contradict themselves twice: "probably at B2 …
goal A2 within a year" (2026-10-18) and "solid B2, pushing into A1"
(kickoff prompt). B2 > A2 > A1, so these cannot be literal. Working
interpretation, stated to Timothy in-session with no objection, and
consistent with the described profile: **current level roughly A2
production / B1 reading; goal B2 conversation within a year, pushing
toward C1/professional use** ("comfortable conversation in a bar
about relatively complex topics; ultimately take work in my technical
field"). The diagnostic doesn't depend on the resolution: per the
kickoff's own instruction it assumes nothing and probes A0 → B1+.
If the interpretation is wrong, overruling it costs one line in the
course plan, not a redesign.

## Theme (Timothy's pick, 2026-10-18)

**The Return («Возвращение»)** — going back to a city you once lived
in — with two emphases he set: (1) meeting new people and getting to
know them; (2) centred on a **software/data business** (he is an
enterprise data/domain architect; the course's recurring company
makes a data platform). Rejected alternatives, offered and declined:
"The Bureau" (engineering-bureau framing — survives inside The
Return as the data company instead) and "The Correspondent"
(journalist framing). The diagnostic is themed as the first walk
through the old neighbourhood — an inventory of what survived the
rusty year — with a recurring character, Dima, an old friend who now
works at a data-platform company; he carries the reading section and
both free-writing tasks, and is built to recur through the course.

Course id: **`vozvrat`** (возврат/возвращение = return; no hyphens).
Hub entry: title "The Return", icon 🧳, dusty-blue palette,
`bigText: false`. Headings stay Latin because the display font
(Fredoka) has no Cyrillic glyphs; Cyrillic lives in body text, where
Nunito covers it (verified in base.css — Playbook addendum's font
check).

## What is being assessed, and why

Playbook language addendum strands, mapped to his profile:

| # | Strand (section) | The actual question it answers |
|---|---|---|
| 1 | The signs are still readable | Is Cyrillic fluent or rusty? (Also: Cyrillic keyboard shakedown before grammar needs it) |
| 2 | People — meeting and knowing | Social vocabulary: recognition vs retrieval, A1→B1 |
| 3 | The bar and the street | Same, for the course's destination register |
| 4 | Cases — the old enemy | WHERE exactly the case system broke: per-case, per-band map |
| 5 | Verbs — getting things moving | Conjugation intact? Motion verbs? Is ASPECT understood as a concept? |
| 6 | A message from Dima | Reading: can he leverage known roots to crack unknown forms in connected text? |
| 7 | Your turn to speak — on paper | Production: scored translations + two free-writing tasks a human/AI reads |
| 8 | Debrief | Enjoyment per strand + fond-memory harvest + self-diagnosis + bar-topic targets |

Design principle threaded throughout: **recognition and retrieval are
split on purpose** (e.g. пиво appears Ru→En in v3q1a and En→Ru in
v3q3a). In a rusty speaker recognition survives while retrieval
decays; the GAP between the two, per strand, is the main measure of
rust vs true gaps — and it decides whether the course's early
sessions are reactivation (fast) or teaching (slow).

Second principle: **plants**. Words taught by the checkpoint itself
reappear later in it (рядом → Dima's «бар рядом с офисом»; знаком- →
«познакомлю»; работаю архитектором in v4 → the self-introduction in
v7q4). Reading questions isolate one unknown each; production tasks
re-elicit forms scored earlier, so scored-vs-spontaneous can be
compared on the same grammar.

## Level bands

- **A0** — Cyrillic decoding of international words.
- **A1** — core vocabulary, baseline conjugation, в + prepositional.
- **A1+/A2** — everyday vocabulary, accusative/genitive, past tense,
  motion-verb basics, short scored translations.
- **B1** — dative/instrumental, aspect choice, perfective future,
  nuance vocabulary (знакомый, собеседник), inference in reading.
- **B1+** — genitive plural, adjective agreement under case,
  conditional, stacked-clause reading. **Built to be out of reach**;
  stated up front in v1's intro. A clean B1+ performance would mean
  the ceiling is wrong and the oral protocol must probe B2.

Bands ride in each question's `level` field into the results JSON.

## Decisions made, with the trail

1. **Checkpoint engine, not bespoke HTML** — mandated; inherits
   save/resume via the state mirror, which his 15-min/day budget
   makes essential: the intro says "do it in short sittings" and the
   course manifest sets expectations the same way.
2. **Cyrillic input required** for production answers. *Rejected:*
   accepting transliteration — typing Cyrillic is part of the stated
   job goal, he can already read, and translit accept-lists would
   double every list while muddying the signal. Cost accepted: he
   must enable a Russian keyboard; v1q3 is deliberately a zero-stakes
   keyboard shakedown (интернет, водка) before anything that matters
   needs it. Overrule cheaply by adding translit twins to accepts.
3. **ё policy**: every accept list containing ё carries an е twin
   (счёт/счет, пошёл бы/пошел бы) because `normText` does NOT map
   ё→е. Stated to the learner in v1's intro ("е for ё is always
   accepted") so he doesn't self-censor.
4. **Gender forms**: feminine past/conditional forms (была, пошла бы)
   are in the accept lists even though Timothy is male — a gender
   slip is a smaller error than failing the construction, and the raw
   answer is stored for the review read to catch it. *Rejected:*
   marking была wrong — it would conflate two different errors.
5. **Grammar sections ask for THE WORD, not the sentence** — one
   ending per part, dictionary form in brackets. Keeps the engine's
   exact-match marking honest (one unknown per part) and his typing
   load low. Parentheses in prompts are safe: normText strips ( )
   from answers.
6. **Aspect tested as a concept, not a memory**: v5q4's pair uses
   наконец (forces perfective) and два часа (forces imperfective) —
   two unambiguous signals, so consistent success means the
   completion-vs-process model is intact, while one-right-one-wrong
   means guessing. This single pair determines whether aspect gets
   its own early unit.
7. **Free writing captured, not machine-marked**: v7q3/v7q4 are
   `text` parts with no accept list → textarea → "review" (the
   engine's documented mechanism for exactly this). *Rejected:*
   accept-list "marking" of multi-sentence Russian — pretending to
   mark free production is worse than not marking it.
8. **Spelling for an adult IS the skill** (brief requirement, per
   part): scored translation parts (v7q1–q2) and grammar endings
   require correct forms, with only deliberate, named leniencies
   (ё/е everywhere; пожалуста for пожалуйста in v3q3b; -тся/-ться in
   v2q3c — each justified in its `_working`). Grace's
   never-grade-spelling rule explicitly does NOT apply here.
9. **Survey includes self-diagnosis** (v8q4 "what exactly broke you")
   to triangulate against measured results — agreement locates Unit
   1; disagreement diagnoses a confidence problem rather than a
   knowledge problem (different treatment, see rubric).
10. **Length: 8 sections, 36 questions, 79 parts** — sized as 5–7
   sittings of ~15 min, or two longer ones. *Rejected:* trimming to
   one sitting (would force dropping either the recognition/retrieval
   split or a grammar band, both load-bearing) — save/resume exists
   precisely for this.
11. **No listening strand** — platform has no audio. The oral
   protocol carries listening/speaking. Audio recommendation + cost:
   see `gracees-diagnostic.md` (same analysis, one write-up; for
   Russian the need is sharper because his stated weakness IS
   comprehension of running speech).

## QA checklist (CONTENT_GUIDE.md), completed for this delivery

- [x] Every accepted answer re-derived in `_working` (79/79 parts;
      script-validated; grammar forms derived rule-by-rule in place)
- [x] Hints — n/a in checkpoint mode
- [x] Accept lists generous (ё/е twins, UK/US spellings, either-script
      answers where fair, both word orders for пошёл бы, apostrophe
      variants in English answers)
- [x] Rematches — n/a for a diagnostic; rubric extracts the list
- [x] Reveal/summit — n/a block types; the narrative duty is carried
      by the walk framing and Dima
- [x] Grace-only items — n/a
- [x] Manifest updated (diag live, Unit 1 placeholder empty)
- [x] run_tests.py green; no version bump (not shipping)
- [x] Done-screen — n/a (engine results screen)
