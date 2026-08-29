# Coding Standards

Style/naming conventions specific to this codebase, seeded from real incidents rather than
invented — extend this as new conventions get established, don't pre-populate speculatively.

## Never reuse an HTML `name` attribute between a row's controls and its filter bar

Applies to any table row whose controls share a form/`hx-include` scope with a filter bar above
it. A Tasks-table row's `status`/`employee_id` `<select>` controls once shared their `name` attribute
with the filter-bar `<select>` controls above them. Since the filter inputs are included in every
row-level update request via `hx-include=".task-filter-input"`, the server received **multiple**
values for the same form key — this silently broke status/assignee updates whenever a filter was
active (especially when a filter was set to "all"), because the wrong value in a multi-valued
field could win depending on parsing order. Fixed by giving filter inputs a distinct `f_`-prefixed
name (`f_status`, `f_employee_id`, `f_system_id`, `f_project_id`, `f_q`) so a row's own `status`
input never collides with the filter bar's. See `docs/reports/badge-status-update-fix.md` for the
full incident.

**Rule**: any new filter control added to a table with per-row `hx-include`d controls must use a
name that cannot collide with a row's own field names — the `f_` prefix convention above is
already established, keep using it.

## Clearing a nullable Task field through `agent_actions.update_task`

`update_task`'s optional parameters default to `None`, meaning "leave this field untouched" — but
a nullable field sometimes needs to be explicitly reset to `NULL`, which a plain `None` default
can't distinguish from "not mentioned." The established convention: repurpose an otherwise-invalid
value as the explicit-clear signal, per field type. `employee_id` uses `0` (an Employee can never
have id `0`). `github_review_state` (string/enum field) uses `""` (empty string, falsy but not
`None`). Reuse this pattern — don't introduce a new sentinel object — for the next nullable field
that needs the same three-state (untouched / set / explicitly cleared) behavior.

## Naming

- **Title Case** for the names of Systems, Projects, Tasks, and Employees — enforced by the LLM
  Orchestrator's system prompt (`orchestrator/prompts.py`) and expected consistently regardless of
  whether an entity was created via chat/voice, the CLI, or `github_sync`.
- Doc/report filenames use `NN-kebab-case-slug.md` (zero-padded two-digit sequence number, hyphens
  — not underscores) under `docs/reports/issues/` and `docs/reports/specs/`.
