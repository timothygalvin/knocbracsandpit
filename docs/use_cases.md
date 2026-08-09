# Use cases — Knocbrac sites repo

Three shared use cases, each with acceptance criteria (AC) that are
executable: every AC names the automated test that verifies it. Run the
whole suite with:

    python3 -m unittest discover -s tools/tests -v

Tests degrade honestly: anything needing an optional binary (php-cgi,
node) reports SKIPPED with a reason rather than passing vacuously.

---

## UC1 — Update content
An author (human or agent) adds or edits course content: a session file,
a checkpoint, or a course manifest. Engine files are not touched.

| # | Acceptance criterion | Verified by |
|---|---|---|
| 1.1 | Every JSON file in the site tree parses. | test_checks.ChecksTree.test_valid_tree_passes / test_broken_json_detected |
| 1.2 | Session and course ids contain no hyphens (progress-endpoint contract). | test_checks.ChecksTree.test_hyphen_id_detected |
| 1.3 | Every non-"soon" session listed in a manifest has a content file (no tappable 404s — the Jim bug). | test_checks.ChecksTree.test_missing_content_detected |
| 1.4 | Session content uses only known block types and marking fields the engine understands. | test_checks.ChecksTree.test_schema_violation_detected |
| 1.5 | Adding a whole course = one folder + one registry entry; no engine edits required. | test_pipeline.LocalDeploy.test_new_course_needs_no_engine_change |

## UC2 — Test content (and platform)
Anyone can run the full test suite headlessly, before any deploy, with
no server and no credentials.

| # | Acceptance criterion | Verified by |
|---|---|---|
| 2.1 | The suite runs with Python stdlib only; optional tools skip loudly. | the suite itself (unittest discover; skip messages) |
| 2.2 | PHP files destined for knocbrac pass the PHP 5.6 gate (no `??`, no `fn(`), and `php -l` where available. | test_checks.ChecksTree.test_php7_token_detected |
| 2.3 | The marking engine gives the documented verdicts (money symbols, fractions, mixed numbers, percentages, the pctOk bare-percent rule, Cyrillic text matching). | test_marking.MarkingEngine (skips without node) |
| 2.4 | The receiver round-trips: POST → file saved → index rebuilt → correct JSON; GET → "receiver alive"; GET ?progress= → completed session ids. | test_receiver.Receiver (skips without php-cgi) |
| 2.5 | Receiver responses are always HTTP 200 (ErrorDocument-proof). | test_receiver.Receiver.test_all_responses_are_200 |

## UC3 — Deploy content
A deployer pushes the current tree to a site. The pipeline is identical
for every site/transport; only the transport differs.

| # | Acceptance criterion | Verified by |
|---|---|---|
| 3.1 | Pre-flight failure blocks the deploy entirely. | test_pipeline.LocalDeploy.test_preflight_failure_blocks_deploy |
| 3.2 | Only changed files are transferred; an immediate re-deploy transfers nothing. | test_pipeline.LocalDeploy.test_delta_and_idempotence |
| 3.3 | Protected paths (learn/results/*) are never touched by deploy; --init adds only the declared placeholders. | test_pipeline.LocalDeploy.test_results_protected |
| 3.4 | A deploy through any transport produces a target byte-identical to the deployable set (transport equivalence — this is how rsync/SFTP get *proven* before first use). | test_pipeline.LocalDeploy.test_local_deploy_byte_identical |
| 3.5 | Post-deploy verification checks the live receiver and that the live release matches local. | verify() probes in site.json (exercised manually against the live site; logic covered by test_pipeline.LocalDeploy.test_verify_probe_logic) |

### Transport proof procedure (the "prove it" for rsync/SFTP)
1. Implement the transport against the `Transport` contract in deploy.py.
2. Point it at a scratch target (a temp dir over ssh-to-localhost, or a
   scratch dir on the new platform).
3. Run the same test_pipeline suite with the new transport substituted:
   it must pass 3.1–3.4 unchanged, and the byte-identity check (3.4) is
   the proof. Only then does it earn a site.json entry.
