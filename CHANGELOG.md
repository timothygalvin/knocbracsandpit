# Changelog — Knocbrac sites

Human-readable release notes. Two independently versioned artefacts per
site (see CLAUDE.md § Versioning): **code** is semantic, **content** is a
simple `rN`. They ship on separate paths and appear in separate sections
below. Machine-readable manifests of what each release contained — every
file with its sha256 — are written to `releases/` by
`deploy.py --manifest`.

Newest first. A release is listed once it has been deployed; staged
work-in-progress lives in `docs/TODO.md`.

---

## code 1.1.1 — 18 Oct 2026 (staged)

**Every dash a child can type now marks correctly.** `parseNumeric` passed
the answer to `parseFloat`, which understands only the plain hyphen —
every other dash returned `NaN` and the part marked "review" instead of
correct. Our own prompts print the typographically correct minus (U+2212),
so a child who copied the sign out of the question was marked wrong.
**16 answer parts across 8 shipped sessions were affected**, including all
of Jim's directed-number work and three of Grace's.

- One line in `assets/shared.js` folds true minus, figure dash, en dash,
  em dash, horizontal bar, hyphen bullet, small and fullwidth hyphen-minus
  down to `-`. A bare dash still correctly fails to become a number.
- Guarded twice: the full dash set through the real engine under node
  (`test_receiver.MarkingEngine.test_every_dash_a_child_can_type_is_accepted`,
  skips without node), plus `MarkingEngineSource`, which runs everywhere and
  asserts the fold is still present in the source — the same anti-drift
  trick as the PHP/Python receiver test, without duplicating engine logic.
- Found while QA-ing Jim's checkpoint, which has three negative answers in
  its first section. A patch, so by the compatibility rule it cannot
  invalidate content and needs no content release.

## code 1.1.0 — 11 Oct 2026

**Learner work now survives a device change.** Previously only *completion*
synced from the server; every answer a child had typed lived in that
tablet's `localStorage` alone. Clearing browser data lost the lot while the
course map still showed ticks — which is exactly what happened to Jim, who
lost a whole unit's typed work.

- `api/submit.php`: new `GET ?state=<course>` and `POST kind:"state"`,
  merging per session into `results/state-<course>.json`. Named so it can
  never match the progress glob `<course>-*.json` nor the family index.
- `api/submit.py`: same logic, keeping the documented fallback at parity —
  and it is what makes the feature testable without `php-cgi`.
- `assets/shared.js`: `saveWork` writes localStorage instantly then mirrors
  to the server on a 2.5s debounce; `bestWork()` returns whichever of
  device/server is newer. Work saved by the pre-1.1.0 engine carries no
  timestamp, so with nothing to compare it keeps whichever side has more
  typed answers rather than silently discarding a child's work.
- `app/session.html`: boots from `bestWork()` instead of `loadWork()`.
- Fixed before release, caught by the receiver tests the moment `php-cgi`
  was available: PHP encodes an empty `array()` as `[]`, not `{}`, so the
  empty-state response broke its own contract. The Python twin had it right.
- Verified on the live host afterwards, which is the only proof that counts
  here: a brew-installed PHP is 8.x while the server runs 5.6.36.

Tools, not shipped to the server: `tools/recover_state.py` rebuilds work
from submitted results, `tools/seed_state.py` pushes it into the store.
Both were used to restore all six sessions for each child.

## code 1.0.0 — 11 Oct 2026

Versioning split into two artefacts so content and engine stop dragging
each other along.

- Code version moved to `assets/version.json`, **code-owned**, which is
  what lets an engine release avoid touching any content file. The `?v=`
  asset token now matches it. Supersedes the old `r1`–`r6` asset counter
  (`r6` == `1.0.0`).
- `courses.json` keeps its number but the key splits in two: `version`
  (content `rN`) and `requires_code` (the code MAJOR the content targets).
- New `compat` pre-flight check: code must be `MAJOR.MINOR.PATCH`, content
  must be `rN`, and a code MAJOR bump blocks the deploy until the content
  side declares it. Minor and patch can never invalidate content.
- `deploy.py --content` / `--code` split paths, `--manifest` release
  records, and a `coverage` check that refuses to deploy any file belonging
  to neither path. The upload manifest now merges rather than replaces, so a
  split deploy cannot make the pipeline forget the other artefact.
- Withdrew `learn/README.md` from deployment: a stale r3 manual guide
  containing the `.htpasswd` example password, which had been publicly
  served at `/learn/README.md`. Its content moved to the repo-root README.

---

## content r12 — 18 Oct 2026 (staged)

Two things, both driven by evidence rather than a roadmap. (r10 and r11
were intermediate local bumps, superseded before deployment; r9 is live.)

- **Jim's w2s2 "The Position Machine" rewritten.** His submitted result
  showed m1 and m2 correct then m3–m6 entirely blank, with w2s3 completed
  in full fourteen minutes later — so the session lost him rather than
  defeating him. The inverse ("run the machine backwards") moved from
  mandatory question 3-of-6 to an optional ★ at 5-of-5, carrying its own
  worked example inside the prompt so it stands alone. Rule-writing, which
  was asked cold, is now scaffolded: gap, then zeroth term, then the rule.
  Six questions became five. New question ids (`p1`–`p5`) so his seeded
  state cannot pre-fill stale answers into restructured questions.
- **Checkpoint 1 for both children**, outstanding since August and the
  instrument that should steer Unit 4. Authored as `kind:"checkpoint"` —
  paged, skippable, deferred marking, results posted to the family folder —
  so they cost no engine work at all, unlike the bespoke HTML diagnostics
  they replace.
  * `ascent/cp1` "Everything So Far": 17 questions, 37 parts, four sections,
    levels banded 4/8/5. Section 3 deliberately under-weights the backwards
    move, measuring what Jim has rather than re-running what defeated him.
  * `graceco/cp1` "The Audit": 16 questions, 32 parts, levels 6/6/4, five
    tables, prose before every one of them.
  * Each carries two **human-review** parts — a text part with no accept
    list, asking for one sentence of reasoning. They cannot be marked wrong,
    and a skip on them is as informative as an answer. For Grace, whether
    she spots unprompted that revenue quadrupled while the loss shrank to a
    third is the most advanced signal in the file.

## content r9 — 18 Oct 2026 (deployed)

- **Grace's Unit 3 · The Bank opens**: Rent on Money, The Snowball,
  Market Story: The 0% Offer. Interest as rent on money running both ways,
  compound interest discovered before the word is used, the same snowball
  rolling against her as debt, and a real 0% credit-card offer taken apart —
  transfer fee, the month-13 cliff, and why a minimum payment barely moves
  a balance.
- Written against `docs/plans/graceco-unit3.md`, which is built from her
  *actual* submitted results rather than guesswork: the plan quotes her
  typing "i dont know" nine times on a question written in shorthand, and
  answering the year-4 figures for a year-3 question. Hence prose before
  every table, every period named in full in its label, and teaching
  density at 62–75 words per question against 14–29 in her old Unit 2.
- One fix during review: w3s3's verdict question asked "who should take
  this offer?" but accepted only the number `50`, so a child typing
  `priya` would have been told "Not yet — try again". Now a text part
  accepting the name, its misspellings and the figure. That is the exact
  defect r7 existed to remove, caught before it reached her.

## content r8 — 18 Oct 2026

- **Jim's Unit 3 · The Proportion Problem opens**: The Mixing Room,
  Scaling the Recipe, Summit Puzzle: The Oxygen Mix. Ratio as parts,
  equivalent ratios, simplest form, sharing a total, the unitary method,
  cost per unit, the things that do not scale, and a blend that is provably
  impossible with whole cylinders.
- Designed against `docs/plans/ascent-unit3.md`, which is built around why
  w2s2 failed: one new idea per session, introduced in the first third, and
  no second conceptual turn after halfway.

## content r7 — 11 Oct 2026

- **Grace's sessions rewritten for clarity.** Her submitted results showed
  her typing "i dont know" nine times on a question whose data was written
  as `revenue £50 → £100`, and "i dont understand" on another. Every such
  shorthand across all six of her sessions is now plain English, with a
  table alongside the prose wherever the data is tabular — nine tables
  added. Period boundaries are named in full after she answered the year-4
  figures for a year-3 question.
- The rule is now a hard rule in `docs/CONTENT_GUIDE.md` so it cannot be
  relearned the hard way: no arrows for change, no `A:` data lines, no
  `___` blanks, and short sentences are about sentence *construction*, not
  an excuse to explain less.

## content r6 and earlier

Not separately noted; `r6` is the state at which Units 1 and 2 of both
courses went live (Jim through The Staircase, Grace through Losing Money on
Purpose). Earlier history is in git from "3: Initial Commit" onward, and in
the pre-git `knocbrac-learning-r1/r2/r3` drops.
