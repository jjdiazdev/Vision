# ADR 0001: Replace Project→Process→Task with System→Project→Task

## Status

Accepted

## Date

2026-08-27

## Context

The original data model was a 3-level hierarchy: `Project` (top-level container) → `Process`
(displayed in the UI as "Milestone") → `Task`. `Project` already had an optional `github_repo`
field (e.g. `"acme-org/firmware"`) populated by the read-only `github_sync` job, so in practice
every `Project` row already corresponded 1:1 to a single GitHub repository — but nothing in the
model represented the GitHub *organization* that owns multiple repos, and `Process`/"Milestone"
had become a pure pass-through: `github_sync` resolved new issues into a Process via
milestone-title matching or an auto-created "Unsorted" fallback, and it added no real grouping
value once a repo's Tasks were being tracked directly against GitHub issue state.

A first attempt at addressing this was **purely cosmetic**: relabel `Project`'s UI text to
"Systems" and `Process`'s to "Projects," with no schema change. This was explicitly rejected
mid-implementation once it became clear the user wanted `System` to be a real, independent entity
(one row per GitHub org, e.g. "Acme") that could own *multiple* Projects (repos) — not just a
different label painted on the existing `Project` row.

Two alternatives were considered and rejected:
- **Keep the cosmetic relabel** — rejected because it couldn't represent "one System owns many
  Projects" at all; a GitHub org with 2+ repos had no way to be modeled.
- **Add `System` without removing `Process`** (4-level hierarchy) — rejected as unnecessary
  complexity: `Process`/"Milestone" had no remaining purpose once Tasks could attach directly to
  their Project, and keeping it around would have meant maintaining GitHub milestone-matching
  logic that nothing downstream actually needed.

## Decision

Replace the hierarchy with `System` (a GitHub organization, e.g. "Acme") → `Project` (a GitHub
repository, unchanged meaning) → `Task`. `Process`/"Milestone" is retired completely: the model
class, the `process` DB table, the `agent_actions.py` CLI subcommand, the `orchestrator/manifest.py`
tool definitions, and every reference in code or docs are removed — not hidden, not deprecated,
gone.

`Task.process_id` becomes `Task.project_id` (required, direct FK). `Project` gains a nullable
`system_id` FK, auto-derived from the owner portion of `github_repo` on create/update
(`execution/agent_actions.py::_resolve_system_id`) unless explicitly overridden — so linking a
GitHub-imported repo to its System requires no manual step in the common case.

## Consequences

- **One-way, hand-written data migration** (`dashboard_app/migrations/versions/0026d61279ce_*.py`):
  derives one `System` row per distinct org found in existing `Project.github_repo` values,
  reassigns every existing `Task` from its (former) Process's Project directly to that Project,
  then drops the `process` table. The `downgrade()` can restore the *schema* shape but not the
  collapsed Process-level Task groupings or System derivation — a true rollback requires restoring
  the pre-migration DB backup, not running `flask db downgrade`.

  > **Update (2026-08-27):** the pre-migration backup this bullet refers to
  > (`dashboard_app/instance/app.db.pre_system_migration`, plus a `backups/` copy) was deleted
  > later in this same session, at the user's explicit request, once the migration was verified
  > successful. The rollback path above no longer has a backup file to restore from — noted here
  > rather than edited into the original bullet, since this ADR records what was true and planned
  > at acceptance time. Documentation reconciliation audit, same date.
- `github_sync.py` got **simpler, not more complex** — Task-to-Project resolution used to require
  milestone-title matching plus an "Unsorted" fallback; now a new issue's Task just attaches to
  whichever Project matches the repo already being polled. `_resolve_process_id` was deleted
  outright with no replacement needed.
- `execution/agent_actions.py`'s CLI, `orchestrator/manifest.py`'s tool list, and
  `orchestrator/prompts.py`'s system prompt all needed matching updates — `process`/`process_id`
  replaced with `system`/`project_id` throughout, since the orchestrator and Claude Code share the
  same underlying data contract (see `governance/01-development-workflow.md`).
- New UI surface: a `/systems` list and `/system/<id>` detail page (mirroring the existing
  `/projects` + former project-detail pattern one level up), and the Tasks table's filter gained a
  System→Project cascade replacing the old Project→Milestone one.
- `CLAUDE.md`'s data-operations contract, the GitHub read-only guardrail's "permitted flow"
  wording, and the delete-cascade description all needed updating to match — see
  `governance/01-development-workflow.md` and `architecture/01-github-readonly-guardrail.md`.
