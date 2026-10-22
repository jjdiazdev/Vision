# Issue Report: Plan-scoped progress and live dependency graph (roadmap 8.1)

## Summary

The dashboard measured progress as `Done / every Task` of a repo, mixing the current plan with the
whole backlog, and had no view of how the plan's issues depend on each other. An implementation
plan (the issues of one cycle across an org's repos, plus their dependency DAG) can now be
imported as validated JSON. While it is active, a Project's percentage counts only its plan issues
(merged or closed = done, per the PM decision of 2026-10-22), the Tasks list shows only those
issues, and a new Tasks → Graph view draws the plan as a horizontal Mermaid graph per repo. Each
node is colored and marked with a glyph according to the plan documents' status rule (no PR / PR
open / CI failing or changes requested / merged with issue open / closed). The graph updates live
from a third `github-sync` cadence. Since new GitHub queries were added, the read-only guardrail is
now enforced in code. Decision record: ADR 0003.

## Files Changed

- `dashboard_app/app/models.py` — `PlanStatusEnum`, `Plan`, `PlanItem`, `PlanEdge`.
- `dashboard_app/migrations/versions/d5e6f7a8b9c0_add_plan_tables.py` — the three tables (new
  tables only).
- `execution/plan_import.py` — pure spec validator: schema, acyclicity, same-org repos,
  same-repo-only stack edges.
- `execution/plan_sync.py` — `PLAN_ITEM_FIELDS`, `compute_plan_snapshot`/`compute_plan_status`,
  `sync_plan_once`.
- `execution/github_sync.py` — `graphql_query` (single exit point) plus `assert_read_only` /
  `GitHubWriteAttempt`; every existing request now goes through it.
- `execution/github_sync_worker.py` — third cadence `PLAN_SYNC_INTERVAL_SECONDS` (15s), under the
  same rate-limit pause.
- `execution/agent_actions.py` — `import_plan`, `activate_plan`, `deactivate_plan`, `delete_plan`,
  `list_plans`, `link_plan_item_tasks`, plus the `plan` CLI subcommand.
- `orchestrator/manifest.py` — `list_plans`, `activate_plan`, `deactivate_plan` for the HUD LLM.
- `dashboard_app/app/utils/plan_graph.py` — pure progress math and Mermaid source builder (escaping,
  edge relaxing, status classes).
- `dashboard_app/app/utils/plan_context.py` — per-request active-plan scope; `project_progress`
  context helper.
- `dashboard_app/app/main/routes.py` — `filter_tasks()` replaces three copies of the Tasks filter
  logic and adds `f_plan`; `?view=graph`; `GET /api/plans/graph`.
- Templates: `tasks.html`, `partials/_tasks_table.html` (header row, plan scope select, view
  switch), new `partials/_plan_graph.html` and `partials/_tasks_view_toggle.html`, and the
  projects/system-detail progress cells.
- `static/js/plan_graph.js` (new Alpine component, lazy-loads pinned Mermaid 11.4.1), `static/js/main.js`
  (progress bars grow from their previous width on SSE swaps instead of jumping), `static/css/style.css`
  (plan tokens and graph view), `base.html` (script include).
- `.env.example`, `docker-compose.yml` — `PLAN_SYNC_INTERVAL_SECONDS`.
- Tests: `tests/test_plan_status.py`, `tests/test_plan_import.py`, `tests/test_plan_graph.py`,
  `tests/test_plan_progress.py`.
- Docs: ADR 0003, `skills/import-plan/SKILL.md`, all five `domains/` files, the guardrail doc,
  `governance/01`, `memory/knowledge_base.md`, `01-roadmap.md`, `README.md`.

## Validation Performed

- Host virtualenv with the project's pinned dependencies (Python 3.14; the container runs 3.11):
  - `python -m unittest tests.test_plan_status` — 20 OK
  - `python -m unittest tests.test_plan_import` — 13 OK
  - `python -m unittest tests.test_plan_graph` — 11 OK
  - `python -m unittest tests.test_plan_progress` — 9 OK
  - `python -m unittest tests.test_github_sync` — 16 OK (unchanged after routing through
    `graphql_query`)
  - `python -m unittest tests.test_task_ordering` — 12 OK (after `filter_tasks` refactor)
- Migration `d5e6f7a8b9c0`: stamped a schema at `c4d5e6f7a8b9`, then `flask db upgrade` created the
  three tables and `flask db downgrade` removed them again.
- Visual review, headless Chrome against a demo server seeded with a synthetic `acme-org` plan
  (23 nodes, all six statuses): default view, a node selected with cross-repo conditions shown, a
  live transition captured mid-animation (two DB rows changed → only those two nodes swept, the
  stacked edge relaxed, 32 % → 37 %), the filtered Tasks list, the projects table with "N/M in
  plan", and the narrow-screen fallback at 700 px. Three rendering problems found this way were
  fixed: Mermaid's undersized `viewBox`, subgraphs ordering bottom-up, and subgraphs falling back
  to top-down without `direction LR`.
- **Not run**: the containers (no V.I.S.I.O.N. container was running on this machine) and the
  plan query against the real GitHub API.

## Known Limitations

- `PLAN_ITEM_FIELDS` (`statusCheckRollup`, `includeClosedPrs`, `stateReason`) has been verified
  only against synthetic payloads. The first real sync will confirm it.
- A PR that cross-references `#N` without implementing it counts as linked. Only same-repo PRs
  count.
- Running a full `flask db upgrade` from an empty database fails at an earlier migration
  (`NoSuchTableError: chat_message`). This predates this change, since the chain breaks before
  `d5e6f7a8b9c0`, but it contradicts the README's "created from scratch on first run" claim.
- Plans are imported only through the CLI or an agent, not from the HUD chat. Editing a plan
  means re-importing it.
- Mermaid is loaded from jsdelivr. If that CDN is unreachable, the graph shows the error state;
  the list view is unaffected.

## Follow-up Recommendations

- Run the plan sync once against a real org repo and confirm the CI and review fields.
- Fix the pre-existing from-scratch migration failure (a separate issue).
- Consider a plan burndown, e.g. a `status_changed_at` history table, if the PM wants trends.
