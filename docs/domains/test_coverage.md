# Test Coverage

Four test files under `tests/`, all `unittest`-based, plus one manual diagnostic script that lives
outside `tests/` entirely. None of `tests/` is wired into the Docker image (`tests/` isn't copied
at build time) — run them by `docker cp`-ing the folder in first, or on a host Python environment
with the project's dependencies installed.

## What's covered

- **`tests/test_repetitions.py`** (5 tests) — `execution/repetition_processor.py`'s daily/weekly
  (Monday-only)/monthly (1st-only) reset logic, using a real temp SQLite DB
  (`dashboard_app/instance/test_app.db`) and a mocked `today` date.
- **`tests/test_edge_cases.py`** (6 tests) — the same reset logic's edge cases: month/year
  boundaries, leap-year Feb 29, and "don't double-reset a Task already reset today."
- **`tests/test_intents.py`** (1 test, ~20 sub-cases) — an LLM intent-accuracy regression suite:
  feeds natural-language sentences through the real Orchestrator (`orchestrator/brain.py`, actions
  mocked out) and asserts the *first* tool call matches the expected `action`/`params`. Requires a
  live LLM backend (`TEST_BACKEND` env var, defaults to `local`/Ollama) — this is the only one of
  the four that makes real inference calls, so it's slow and non-deterministic across model
  versions in a way the others aren't.
- **`tests/test_github_sync.py`** (10 tests) — `_compute_review_state`'s full decision matrix via
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

**Known gotcha**: `test_repetitions.py` and `test_edge_cases.py` cannot run in the same `unittest`
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
  during development of recent features (System/Project restructure, task sort order, blocked-
  project task hiding).
- No coverage of the SSE flow (`domains/flows.md`) or the HTMX partial-swap wiring.

## Next-session testing priorities

1. Extend `tests/test_github_sync.py` with `_compute_status`/`_should_auto_update`'s full decision
   matrix with synthetic GraphQL payloads (no live network calls) — the matrix already exists
   informally as ad-hoc verification scripts run during development; formalizing it is mostly
   transcription.
2. A `tests/test_routes.py` using Flask's test client for the Tasks-view filters (System→Project
   cascade, Blocked-project exclusion) and the `refresh=system` vs. default branch of
   `update_project_status`.
