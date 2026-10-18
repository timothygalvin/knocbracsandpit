# Timothy's Russian — oral protocol (the spoken half)

> Status: READY TO RUN · 2026-10-18 · Runner: Claude, in a chat
> session (voice mode if available — see limitations). Run AFTER the
> written checkpoint. ~25–35 minutes. The paste-ready prompt is at
> the bottom; this document is the protocol it executes.

## Why this exists, and what it cannot do

The written checkpoint cannot assess conversation — and conversation
is the goal. This protocol covers speaking-range, interaction and
repair strategies. **Honest limitation:** run as TEXT chat it still
assesses neither listening to running speech nor pronunciation —
Timothy's self-reported weakest skill is precisely listening. So:

- **Best**: run it in Claude's voice mode (phone app) — then it is a
  true oral diagnostic.
- **Acceptable**: text chat — treat results as conversation-range
  data, and note LISTENING AS UNASSESSED in the findings. It then
  needs a human check (a Russian-speaking acquaintance, or even
  Russian-language video with comprehension self-rating) before the
  course plan claims anything about listening.

Either way the findings must not be read as the whole picture without
the written results, and vice versa.

## Design: complementary to the written half, not a repeat

The written half measured forms in isolation with time to think. This
half measures what surfaces under conversational pressure: fluency
(keeping going), interaction (turn-taking, asking back), repair
(what he does when stuck — the skill that actually carries bar
conversations). It deliberately re-enters territory the checkpoint
scored (introductions, work, the bar) so scored-vs-spontaneous can be
compared on the same ground — and it pushes PAST the written ceiling
(opinion, narration, abstract topics) because conversation is where
B1/B2 discrimination actually happens.

## The ladder (Claude escalates one rung at a time)

| Rung | Territory | CEFR probe | Claude does |
|---|---|---|---|
| 1 | Greetings, how-are-you | A1 | Scripted small talk, slow |
| 2 | Introductions: name, origin, work, where he lived | A2 | Asks the questions the checkpoint planted (работаю архитектором, жил в Москве) — does the scored grammar appear spontaneously? |
| 3 | The past: his two years in Russia — where, what, who | A2/B1 | Past-tense narration; follow-up questions |
| 4 | Opinions: remote work? Moscow vs Bristol? | B1 | Opinion + justification (потому что…); mild disagreement to force defence |
| 5 | His field: explain what a data architect does, to a smart barman | B1/B2 | Abstract/professional register; paraphrase when vocabulary runs out |
| 6 | Free conversation on one of his v8q5 bar topics | B2 probe | Genuine exchange; Claude stops scaffolding |

Rules of engagement for Claude (encoded in the prompt below):
- Russian only from rung 1; English only in the debrief.
- One rung at a time; climb only when the current rung is working.
- **Push until he breaks, then one rung back** — end on a rung he
  can hold, never on the break.
- When he's stuck: first wait, then rephrase simpler IN RUSSIAN,
  then offer the word. Log every rescue — rescues per rung is the
  fluency measure.
- Corrections: NONE mid-conversation (flow is the point); collect
  errors silently for the debrief.
- ~25 minutes of Russian, then the debrief in English.

## Scoring grid (Claude fills this in the debrief)

Per rung reached: **Held / Held with rescues (n) / Broke** — plus:

| Dimension | 1–5 anchor |
|---|---|
| Fluency | 1 = word-by-word · 3 = sentences with long searches · 5 = keeps going, self-repairs in Russian |
| Comprehension (of Claude's Russian) | 1 = needs every line rephrased · 3 = gets rephrased-simple · 5 = first-pass understanding at natural register |
| Grammar under pressure | 1 = none survives · 3 = cases/aspect attempted, ~half land · 5 = reflexive |
| Range | 1 = formulae only · 3 = everyday topics · 5 = abstract/professional comfortably |
| Repair strategy | 1 = switches to English · 3 = asks for words in Russian · 5 = paraphrases around gaps unprompted |

Debrief must also list: the rung map, 5–10 collected errors WITH what
he was trying to say, vocabulary he reached for and lacked (future
unit fuel), and three verbatim quotes of his best Russian (early-win
callbacks for Unit 1).

## Where the results go

The debrief output gets committed as
`docs/results/vozvrat-oral-YYYYMMDD.md` (create `docs/results/` on
first use). If run in a claude.ai chat: copy it out THAT DAY — chats
are purged on a retention window, and losing deliberation to that
window is this platform's registered failure mode
(`decision-provenance`). The rubric reads written + oral together.

---

## Paste-ready prompt (give Claude this, verbatim)

```
You are running the oral half of a Russian diagnostic for Timothy, an
adult returner (lived in Russia two years, ~a year rusty, reading
stronger than listening, goal: comfortable complex conversation).
Protocol: docs/plans/vozvrat-oral-protocol.md in the knocbracsandpit
repo — follow its ladder: (1) greetings, (2) introductions incl. work
and where he lived, (3) narrating his Russia years, (4) opinions with
gentle pushback, (5) explaining his data-architecture work to a smart
barman, (6) free conversation on a topic he names. Russian only, one
rung at a time, push until he breaks then step one rung back and end
on a rung he holds. When he is stuck: wait, then rephrase simpler in
Russian, then give the word — and silently count every rescue. No
corrections during the conversation. Keep your Russian one notch
above his. After ~25 minutes, debrief in English: rung map
(held/rescued/broke per rung), the five 1–5 scores from the
protocol's grid with one-line evidence each, 5–10 collected errors
with what he meant, vocabulary he lacked, three verbatim quotes of
his best Russian, and — if this was text chat — the explicit line
"LISTENING UNASSESSED: text mode". Format the whole debrief as a
markdown file ready to commit as
docs/results/vozvrat-oral-YYYYMMDD.md. Start at rung 1 now, in
Russian.
```
