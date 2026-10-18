# Grace's Spanish — diagnostic design (`gracees/content/diag.json`)

> Status: DESIGNED, not yet deployed · 2026-10-18
> Designed by: Fable (senior agent), from `docs/handoff/LANGUAGE_DIAGNOSTICS_PROMPT.md`
> Companion docs: `gracees-oral-protocol.md` (the spoken half),
> `gracees-rubric.md` (how to read the results).
>
> This file exists so a future reader can reconstruct the thinking
> without the chat (`decision-provenance`, open-concepts register).

## The learner, as known on design day

Grace, 10, Year 5. **Enthusiastic beginner**: a few words, several
family trips to Spain, no formal Spanish known to us. Style sheet
(CONTENT_GUIDE.md) is load-bearing: short sentences, one idea per
line, early wins first, `bigText` on, **never grade spelling**.

What we do NOT know (escalated, not guessed): whether her school
teaches any Spanish, and what it has covered if so. The diagnostic is
designed to be valid either way — if school Spanish exists, it shows
up as unexpected strength in strands 3–4 and the rubric says what to
do with that.

## What is being assessed, and why

The design question for a beginner is not "what level is she?" — she
is a beginner; the CEFR answer is already known to be ~A0. The real
questions, one per strand:

| # | Strand (section) | The actual question it answers |
|---|---|---|
| 1 | Words you've already got | What did the trips leave behind? (greetings/politeness) |
| 2 | The café menu | Does she have the **cognate instinct** — the single most leveraged beginner skill? |
| 3 | Numbers and euros | Number retention, and whether the money hook (her Grace & Co. identity) carries into Spanish |
| 4 | How Spanish fits together | Any grammar instinct at all: gender, me llamo, tengo X años. Expected mostly out of reach — that calibrates Unit 1's floor |
| 5 | The postcard | Can she extract meaning from a real connected text using context + planted words? |
| 6 | Survey | Enjoyment per strand, her own goals, and the full inventory of trip-words ("empty the suitcase") |

## Level bands

Kids' courses used school years; Spanish gets CEFR-ish bands because
that's what language curricula speak:

- **A0** — words a Spain-holiday child has inevitably met (hola,
  gracias, uno). Early-win territory; misses here are surprising.
- **A1** — core beginner vocabulary and production of single words
  (agua, tres, hola typed out).
- **A1+** — beginner stretch: known pieces in new combinations
  (cuatro euros, tengo diez años with the model visible).
- **A2** — genuinely beyond a beginner (la cuenta, cien, dónde está,
  mañana). **Built to be out of reach**; stated up front in section
  1's intro ("too hard to finish — that's on purpose. A skip tells us
  where to start. It is never a fail.").

Every question carries its band in `level`; the engine stores it
per question in the results detail, so the rubric can compute
per-strand top-out mechanically.

## What a given answer tells you (worked logic, per section)

- **s1 (A0 greetings)**: all six right = trips left a residue; start
  Unit 1 one notch up. Misses = true zero start, equally fine.
  s1q6 (produce "hola") is the first recognition-vs-production probe.
- **s2 (cognates)**: s2q1 (chocolate/limonada/tomate) right but s2q2
  (helado/agua/leche) wrong = she can harvest lookalikes but has no
  stock — Unit 1 leads with the cognate reveal ("you already know
  hundreds of Spanish words"). Both right = real retained vocab.
  s2q3 re-asks agua as production two questions after showing it:
  a hit tests short-term carry, which predicts how fast sessions
  can move.
- **s3 (numbers)**: numeric parts, so spelling can't contaminate the
  signal. uno–diez recognition vs tres/nueve production vs quince/
  cien ceiling gives a clean three-step ramp. The euros framing is
  deliberate: if the enjoyment score for this section is high, the
  course gets a running money thread (prices, markets, her world).
- **s4 (grammar instinct)**: nothing here is teachable-by-question;
  it measures exposure instinct. s4q4 is the key design move — the
  model sentence («Tengo diez años», s4q3) is visible ON THE SAME
  PAGE, so s4q4 tests pattern-copying, not recall. That is the exact
  skill the reveal pattern trains, measured before the course starts.
- **s5 (postcard)**: every question isolates ONE unknown — the rest
  of each sentence is planted earlier in the checkpoint (helado,
  chocolate, la playa) or is a proper noun/cognate (Málaga, fútbol).
  So a wrong answer names its gap precisely. The Carmen character
  carries over from s4 (continuity; also gives the oral protocol a
  ready-made role-play partner).
- **s6 (survey)**: enjoyment 1–5 per strand as numeric `range` parts
  (any value marks correct — there is no wrong feeling); favourite
  question, "what do you want to DO", and the suitcase-emptying
  free-list as `text` parts with NO accept list, which the engine
  renders as textareas and marks "review" — free writing captured
  without pretending to mark it.

## Decisions made, with the trail (for cheap overruling)

1. **Course id `gracees`**, per the handoff brief's suggestion. No
   hyphens (progress-endpoint contract).
2. **Theme: travel/Spain world** — hub title «¡Vamos!», tagline
   "Grace's ticket to Spain", icon ☀️, terracotta/orange palette,
   `bigText: true` carried over from graceco. From her actual
   motivation (real trips, real pool, real menus) per Playbook Step 0
   — not from the subject. *Rejected:* extending the Grace & Co.
   company world into Spanish (a Spanish branch office…) — cute, but
   it would make Spanish feel like more maths-course, and the survey
   can still surface the money hook if it's there (s3 + enjoyment).
3. **Diagnostic framed as "The Suitcase"** — an inventory of what's
   already packed. Chosen over "test/quiz" framing for the same
   reason the kids' diagnostics were themed: skips must feel like
   packing notes, not failure.
4. **Checkpoint engine, not bespoke HTML** — mandated by the brief;
   zero engine work, results land in the family folder, Aa toggle
   and bigText inherited.
5. **Recognition-heavy, production-light** — most answers are in
   ENGLISH (she translates INTO her strong language). Production
   (typing Spanish) appears exactly five times, all single words or
   a copyable pattern. *Why:* she's a beginner AND spelling is never
   graded; heavy Spanish typing would measure spelling anxiety, not
   Spanish. *Rejected:* a dictation-style strand (no audio on the
   platform) and any accent-mark requirement (the engine does not
   normalise accents — está ≠ esta — so accents in ACCEPT lists are
   always paired with accentless twins; her typing an accent is never
   required).
6. **No multiple-choice** — the engine has no MC widget; where a
   closed choice is wanted (el/la) the prompt says "type el or la".
   *Rejected:* requesting an MC engine feature — that's a code
   release on a separate path, explicitly not this task's to make.
7. **Spelling policy implemented as accept-list generosity +
   review-not-wrong**: text parts that miss their accept list mark
   "review" (engine fact), and every production part's accept list
   carries phonetic misspellings (grasias, ola, trez, tengo dies
   anos…). The rubric instructs the reader to credit review answers
   on meaning. This is the mechanical form of "never grade spelling".
8. **ñ and accents on tablets**: every accept list containing ñ or an
   accent has ASCII twins (anos, malaga). Trade-off consciously
   accepted: "anos" is a different (rude) word in real Spanish —
   irrelevant at marking time, worth a giggle-proof glance at review.
9. **Length: 6 sections, 30 questions, 43 parts, ~35 min** with
   skips. Grace's style sheet: a strong 35 beats a fading 45.
   *Rejected:* covering listening/speaking in the written half at
   all — see the oral protocol, and the audio note below.
10. **Survey placed last and unmarked** (framed "no wrong answers"),
   with the strand ratings keyed to section names she just saw.

## The audio gap (recommendation with a cost, as the brief requires)

A language course without audio is teaching from behind glass.
Per-question audio is parked in TODO ("needs asset hosting thought —
keep static"). Recommendation: **static mp3 assets per content file**
(`<course>/content/audio/<id>-<q>.mp3`, pre-generated TTS, shipped by
the content artefact like any other file) would cover ~80% of the
need with no engine change beyond an optional `audio` field renderers
ignore today. Cost: a one-time TTS generation step in the content
pipeline, ~50–100 small files per course, and a schema addition that
needs a code MINOR (renderer support). Not blocking either diagnostic;
both are designed to be valid without it (the oral protocols carry
listening). Decision stays with Timothy.

## QA checklist (CONTENT_GUIDE.md), completed for this delivery

- [x] Every accepted answer re-derived independently in `_working`
      (every one of 43 parts carries `_working` with the translation
      and the accept-list rationale; validated by script)
- [x] Every hint tested — n/a: checkpoint mode has no hints (engine
      renders hints only in practice mode)
- [x] Accept lists generous (accent/ASCII twins, punctuation variants,
      phonetic misspellings, both-language answers where fair)
- [x] Rematches labelled — n/a for a diagnostic (it is the source of
      future rematches; the rubric extracts the rematch list)
- [x] Reveal earns its surprise / summit discussable — n/a block
      types for checkpoints; the "surprise" duty is carried by the
      suitcase framing and s4q4's copy-the-pattern move
- [x] Grace only: sentence length, big text, no prose burden —
      prompts are 1–2 short sentences; one idea per line (`<br>`);
      answers are single words/numbers; free writing only in the
      unmarked survey
- [x] Manifest updated (diag live; Unit 1 placeholder empty, nothing
      falsely "soon")
- [x] run_tests.py green; content version NOT bumped (not shipping —
      brief forbids version bumps and deploys)
- [x] Done-screen names the gain — n/a: checkpoints use the engine's
      own results screen ("the full picture goes to the family
      folder")
