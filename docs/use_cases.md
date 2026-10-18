# Use cases — Knocbrac sites repo

Three shared use cases, each with acceptance criteria (AC) that are
executable: every AC names the automated test that verifies it. Run the
whole suite with:

    python3 tools/run_tests.py          # with pass/fail/skip tally\n    python3 -m unittest discover -s tools/tests -v   # plain unittest also works

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
| 3.6 | Release integrity: every shipped HTML asset include is version-locked to the courses.json release, and a Cache-Control policy exists — a stale cached script can never run against a fresh page (the mergedDone TypeError class). | test_checks: test_unversioned_asset_detected / test_version_mismatch_detected / test_missing_cache_header_detected / test_receiver_results_page_exempt |

## UC4 — Deploy content and code separately
Course content and the engine are two artefacts on one site. A content
release ships without touching an engine file; an engine release ships
without touching course data. Declared per site in site.json
`artefacts`; the scheme is site-agnostic (agileintegrator.com will
declare its own globs against the same machinery).

| # | Acceptance criterion | Verified by |
|---|---|---|
| 4.1 | Every deployable file belongs to exactly one artefact: the two paths are disjoint, and together they cover the full deployable set. | test_pipeline.LocalDeploy.test_artefact_paths_are_disjoint_and_complete |
| 4.2 | A file belonging to neither path (or to both) blocks the deploy at pre-flight, rather than becoming invisible to split deploys. | test_pipeline: test_uncovered_file_detected / test_overlapping_artefacts_detected |
| 4.3 | A split deploy is authoritative only for its own artefact: the upload manifest keeps the other artefact's entries, so shipping content leaves the code path with nothing to do (and cannot trigger a full re-upload). | test_pipeline.LocalDeploy.test_split_deploy_preserves_other_artefact_in_manifest |
| 4.4 | A split deploy forgets deleted files from its own artefact only. | test_pipeline.LocalDeploy.test_split_deploy_prunes_within_its_artefact |
| 4.5 | `--manifest` records the release: every file with sha256 and size, which of them this push actually ships, and the sessions contained. | test_pipeline.LocalDeploy.test_release_manifest_records_shipping_set |

Note on ordering: content is safe to ship ahead of code because content
declares no engine feature beyond the schema the live engine already
renders (UC1.4 enforces this). Since the cache token moved to a
code-owned file (UC5), the reverse holds too — the two paths are
symmetric and neither ships a file belonging to the other.

## UC5 — Version the two artefacts separately
Code is semantic (MAJOR.MINOR.PATCH) in a code-owned version file;
content is a simple `rN` in courses.json and names the code MAJOR it was
authored against. A code MAJOR bump is the only change that can
invalidate content. There is no combined package version.

| # | Acceptance criterion | Verified by |
|---|---|---|
| 5.1 | The asset cache token comes from the code-owned version file, so an engine bump never edits a content file. | test_checks.ChecksTree.test_cache_token_comes_from_code_not_content |
| 5.2 | A code minor or patch bump never invalidates content. | test_checks.ChecksTree.test_compat_accepts_minor_and_patch_bumps |
| 5.3 | A code MAJOR bump blocks the deploy until the content side declares the new major. | test_checks.ChecksTree.test_compat_rejects_major_bump_without_content_update |
| 5.4 | Malformed versions are rejected: code must be MAJOR.MINOR.PATCH, content must be rN. | test_checks.ChecksTree.test_compat_rejects_malformed_versions |
| 5.5 | A missing code version file is reported, never a silent pass. | test_checks.ChecksTree.test_missing_code_version_file_is_not_a_silent_pass |
| 5.6 | A split deploy verifies only its own artefact's marker; a flat probe list still works for sites that declare one. | test_pipeline.LocalDeploy.test_verify_probes_select_by_artefact |

## UC6 — A child's work survives a device change
Typed answers are mirrored server-side, so clearing browser data or
moving tablet loses nothing. The Python receiver carries the same logic
as the live PHP one, which is what makes this verifiable without
optional binaries.

| # | Acceptance criterion | Verified by |
|---|---|---|
| 6.1 | Work POSTed for a session can be read back intact (answers, try counts, a server `savedAt` stamp). | test_receiver.StateStorePython.test_state_round_trip |
| 6.2 | State accumulates across sessions; re-saving a session overwrites only that session. | test_receiver.StateStorePython.test_state_accumulates_and_last_write_wins |
| 6.3 | Courses never share state (Jim's work cannot appear in Grace's course). | test_receiver.StateStorePython.test_courses_do_not_share_state |
| 6.4 | A course with no saved work returns empty, not an error. | test_receiver.StateStorePython.test_empty_state_is_not_an_error |
| 6.5 | State files share the results folder but are never read as submitted results — not by `?progress=`, not by the family index. | test_receiver: test_state_never_pollutes_the_family_index / test_state_never_pollutes_progress_or_the_family_index |
| 6.6 | A hostile course id cannot write outside the results folder. | test_receiver.StateStorePython.test_state_cannot_escape_the_results_folder |
| 6.7 | The two receivers do not drift apart on the state contract. | test_receiver.StateStorePython.test_php_and_python_receivers_agree_on_the_contract |

The PHP receiver has the same suite under `Receiver` (6.1, 6.2, 6.5,
6.6 and server-side stamping), which SKIPS without `php-cgi`. Install
php-cgi before trusting a receiver change — see the note in TODO.

### Transport proof procedure (the "prove it" ritual)
1. Implement the transport against the `Transport` contract in deploy.py.
2. Prove the transport LOGIC: add/extend tools/tests/test_transports.py so
   the full pipeline runs through the real transport class against a fake
   endpoint, asserting byte-identity (3.4) and protection (3.3).
3. First live run against the real host is the shakedown (--dry-run, then
   deploy, then the verifier). Only after 1–3 does it earn a site.json.

Status: ftp — proven + live. sftpcli (system OpenSSH, zero deps,
key-auth; knocbrac default) — batch logic proven by
test_transports.SftpCliProof. sftp (paramiko, password auth fallback) —
logic proven by test_transports.SftpProof. rsync-over-ssh — future option
for the new platform; must pass the same ritual.
