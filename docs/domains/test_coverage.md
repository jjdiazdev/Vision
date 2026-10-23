# Test Coverage

Twelve test files under `tests/`, all `unittest`-based, plus one manual diagnostic script that lives
outside `tests/` entirely. None of `tests/` is wired into the Docker image (`tests/` isn't copied
at build time) — run them by `docker cp`-ing the folder in first, or on a host Python environment
with the project's dependencies installed.

## What's covered

- **`tests/test_timezone.py`** (18 tests) — `dashboard_app/app/utils/timezone_utils.py`:
  naive→local conversion, aware input idempotence, `None`/non-`datetime` rendering as `''`, an
  unresolvable zone degrading to UTC without raising, the UTC short-circuit not touching
  `zoneinfo`, and a date-only format shifting a calendar day. **DB-free and `create_app`-free on
  purpose**, so it is exempt from the two-files-one-process conflict noted under Known gaps
  below and can be run alongside anything.
- **`tests/test_task_ordering.py`** (12 tests) — `sort_tasks()`'s two-level order: status buckets
  unchanged, newest-`github_created_at`-first within a bucket, NULLs last in their bucket,
  same-second ties broken by issue number, `created_at=None` and mixed naive/aware values not
  raising, and output independence from input order. Stub objects, no DB.
- **`tests/test_plan_status.py`** (24 tests) — `execution/plan_sync.py`'s plan status rule
  (every `PlanStatusEnum` branch: draft, red CI, changes requested, unreadable CI, merged with the
  issue open, PR linking — `Refs`-only PRs found by branch, a cross-reference that only *mentions*
  the issue ignored, cross-references that close it counted, `pr_is_about` branch/title matching
  without false hits on `#77`/`#170` — not-planned/duplicate, abandoned-only PRs,
  open-beats-merged, other-repo PRs ignored, case-insensitive repo match) and
  `github_sync.assert_read_only` (every project query passes; `mutation`/`subscription`
  rejected, including after a query in the same document; the word inside strings, comments
  and field names allowed). Synthetic payloads, DB-free.
- **`tests/test_plan_import.py`** (13 tests) — `execution/plan_import.py`: normalization,
  cycles (reported with their path, including through cross-repo edges), duplicate keys and
  issues, unknown endpoints, same-repo-only edge kinds, org boundary, base-edge rules, and that
  all errors come back together. DB-free.
- **`tests/test_plan_graph.py`** (13 tests) — `dashboard_app/app/utils/plan_graph.py`: edge
  notation (stacked/after-merge relaxing to `-->` once the parent is merged or closed), each repo's
  Mermaid holding only its own nodes and same-repo edges with plan-wide ids, `cross_edges` for the
  overlay, node glyphs and status classes, untrusted text unable to break out of a Mermaid label,
  and `plan_progress` (merged counts as done, not-planned leaves the denominator, never-synced
  counts as not done). DB-free.
- **`tests/test_plan_progress.py`** (9 tests) — end to end on its own temp DB
  (`test_plan_app.db`) with `fetch_issues_by_number` and `trigger_ui_refresh` patched:
  `import_plan` (Task linking, activation, rejecting unlinked repos, one active plan per System),
  `sync_plan_once` (first sync silent, one toast per transition, quiet cycle emits nothing), and
  through Flask's test client: plan-scoped `/projects` progress, the Tasks plan filter on
  `/tasks` and `/api/updates/tasks`, `/api/plans/graph` JSON, the graph page and the 401 gate.
  This is also the first committed route-level coverage of the Tasks filters.
- **`tests/test_notification_retention.py`** (5 tests) — Notification History retention on its
  own temp DB (`test_notification_app.db`): `prune_notifications` at the 0/499/500/501 boundaries,
  keeping the newest ids, and the 500 cap holding after an insert from each writer —
  `record_notification` and both `trigger_ui_refresh` copies (`agent_actions`, `log_progress`; the
  notify thread is patched out). Run in its own process.
- **`tests/test_repetitions.py`** (7 tests) — `execution/repetition_processor.py`'s daily/weekly
  (Monday-only)/monthly (1st-only) reset logic, using a real temp SQLite DB
  (`dashboard_app/instance/test_app.db`) and a mocked `today` date. Two of the seven are the
  timezone-boundary proof: the *same* stored `02:00Z` value and the *same* `mock_today` yield no
  reset under `tz_name='UTC'` and a reset under `tz_name='America/Caracas'`, which is what
  demonstrates the boundary is the local calendar day rather than UTC midnight.
  **Pinned to `DISPLAY_TIMEZONE=UTC`** at import time so the assertions cannot depend on ambient
  container env.
- **`tests/test_edge_cases.py`** (6 tests) — the same reset logic's edge cases: month/year
  boundaries, leap-year Feb 29, and "don't double-reset a Task already reset today."
  **Also pinned to `DISPLAY_TIMEZONE=UTC`**, and this one is not optional:
  `test_no_double_reset_same_day` uses a midnight `updated_at`, which is precisely the value
  that flips under a negative-offset zone.
- **`tests/test_intents.py`** (1 test, ~20 sub-cases) — an LLM intent-accuracy regression suite:
  feeds natural-language sentences through the real Orchestrator (`orchestrator/brain.py`, actions
  mocked out) and asserts the *first* tool call matches the expected `action`/`params`. Requires a
  live LLM backend (`TEST_BACKEND` env var, defaults to `local`/Ollama) — this is the only one of
  the four that makes real inference calls, so it's slow and non-deterministic across model
  versions in a way the others aren't.
- **`tests/test_github_sync.py`** (16 tests) — six of them cover
  `execution/agent_actions.py`'s `parse_github_timestamp` (the single parser feeding
  `Task.github_created_at`): `Z` suffix and explicit offsets normalized to naive UTC, datetimes
  passed through or normalized, and `None`/unparseable input returning `None` rather than
  raising — a malformed field must not be able to kill a sync cycle. The other ten cover
  `_compute_review_state`'s full decision matrix via
  synthetic GraphQL payload dicts (no live network calls): outstanding vs. superseded
  `CHANGES_REQUESTED` review, commit-after vs. before the request, per-author dedup (same reviewer
  later approving), a second reviewer's outstanding request overriding another's approval, no
  reviews, all-approved, missing `pr_number`, no matching PR ref, and a deleted-account (`null`
  `author`) review.
- **`tests/test_errors.py`** (4 tests across 2 classes) — `TestErrorHandling` covers Ollama
  timeout/connection-error/API-error handling; `TestOrchestratorErrors` covers error propagation
  from the Orchestrator. **Known bug, discovered during the 2026-08-27 documentation reconciliation
  audit**: `TestOrchestratorErrors.setUp` references `Orchestrator()`, but that name is only
  imported inside this file's `if __name__ == '__main__':` guard — running it via
  `python -m unittest tests.test_errors` (rather than `python tests/test_errors.py` directly) raises
  `NameError: name 'Orchestrator' is not defined`. Not fixed as part of this audit (out of scope —
  a documentation pass doesn't rewrite test code), but flagged here so it isn't mistaken for
  passing coverage.
- **`orchestrator/test_gateway.py`** (not part of `tests/`, not `unittest`-based) — a manual,
  `__main__`-run diagnostic script that makes a real network call to NVIDIA NIM to verify cloud
  connectivity and the Ollama fallback path. Unlike everything under `tests/`, this file physically
  ships inside the built Docker image, since `orchestrator/` is copied wholesale — see
  `domains/system_architecture.md`'s module map.

**Known gotcha**: `test_repetitions.py`, `test_edge_cases.py` and `test_plan_progress.py` cannot run in the same `unittest`
process/invocation — both `setUpClass`/`tearDownClass` create and drop tables on the same global
Flask-SQLAlchemy `db` singleton against two different temp DB files, and running both in one
process produces a `sqlite3.OperationalError: disk I/O error` on the second `tearDownClass`. Run
each file as its own separate `python -m unittest` invocation.

## Known gaps

- **`execution/github_sync.py`** — `_compute_review_state` now has coverage (`test_github_sync.py`,
  above), but `_compute_status`, `_should_auto_update`, `_compute_pr_number`, and
  `_abandoned_pr_refs` (the closed-issue priority logic, the In-Progress advance-only rule, the
  abandoned-PR-detection via `timelineItems`) still have none — verified manually against live
  GitHub data and synthetic payload matrices during development, but none of that is captured as a
  regression test yet. Still the highest-value remaining gap to close in this module.
- **`execution/agent_actions.py`**'s CLI/function surface (create/update/delete/list/search for
  every entity, `_resolve_system_id`'s find-or-create logic) has no test coverage — only manual
  `docker exec` verification.
- **`dashboard_app/app/main/routes.py`** — no route-level tests (e.g. via Flask's test client)
  exist as committed test files, despite the routes being exercised manually via the test client
  during development of recent features (System/Project restructure, blocked-project task
  hiding). `sort_tasks()`'s *logic* is now covered by `test_task_ordering.py`, but that is a
  unit test on stub objects — there is still no route-level test proving the three Tasks-view
  endpoints actually apply it end-to-end with filters attached.
- No coverage of the SSE flow (`domains/flows.md`) or the HTMX partial-swap wiring.
- **`static/js/plan_graph.js`** has no automated test: it was verified with headless Chrome
  against a synthetic `acme-org` plan — screenshots of all statuses, a node selected, cross edges
  on and a narrow viewport; real mouse drags of two repo panels through CDP, a reload keeping the
  layout and the cross edges anchored, arrow-key moves, Reset layout, and
  `document.getAnimations()` reporting zero animations inside the graph card; full screen through
  a real click on its button (native: `document.fullscreenElement` is `.plan-graph-focus`, `F`
  toggles it, exiting restores the canvas height and keeps the layout) and the overlay fallback
  with the Fullscreen API disabled (1600×857 above the HUD, pan and group drag working inside,
  `Esc` closing it), with zero animations in full screen. The real GraphQL shape of
  `PLAN_ITEM_FIELDS` (notably `statusCheckRollup` and `includeClosedPrs`) is covered only by
  synthetic payloads until it runs against GitHub.

## Next-session testing priorities

1. Extend `tests/test_github_sync.py` with `_compute_status`/`_should_auto_update`'s full decision
   matrix with synthetic GraphQL payloads (no live network calls) — the matrix already exists
   informally as ad-hoc verification scripts run during development; formalizing it is mostly
   transcription.
2. A `tests/test_routes.py` using Flask's test client for the Tasks-view filters (System→Project
   cascade, Blocked-project exclusion) and the `refresh=system` vs. default branch of
   `update_project_status`.
