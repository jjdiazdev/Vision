# Fix Report: Task Status Badge Colors and Update Logic

**Date**: 2026-08-24 (migrated from `.agent/memory/badge_fix_strategy.md` during the docs "second
brain" migration; original content preserved below with the acted-on plan, not rewritten)

## Summary

Task-status badges in the Tasks table weren't updating dynamically. Two causes, both fixed:

1. **Name clash**: the `status`/`employee_id` inputs used in each Tasks-table row collided with
   the same names used in the filter row. Since filter inputs are included in every row update
   request via `hx-include=".task-filter-input"`, the server received multiple values for those
   keys — the update frequently failed (especially with a filter set to "all"), leaving the DB
   unchanged and the old badge color displayed.
2. **CSS override**: `style="background: transparent;"` on the status `<select>` elements
   explicitly overrode the background color defined by the `.badge-*` CSS classes.

## Files changed

- `dashboard_app/app/templates/partials/_tasks_table.html` — renamed filter inputs to the `f_`
  prefix (`f_q`, `f_status`, `f_employee_id`, and originally `f_process_id`, since renamed to
  `f_project_id`/`f_system_id` — see [ADR 0001](../adr/0001-system-project-task-hierarchy.md));
  removed the `background: transparent;` override from status `<select>` elements.
- `dashboard_app/app/main/routes.py` — `api_tasks_updates` updated to read the new `f_`-prefixed
  filter parameter names.
- Same background-transparent fix applied to `_projects_table.html` and (at the time)
  `_project_detail_content.html` for consistency, though the Projects table didn't have the name
  clash (no shared filter row).

## Validation performed

Manually verified: changing a Task's status to "Done" turned the badge green including
background; changing status with a filter active updated correctly without losing the filter
selection; the Projects table's badges continued working with backgrounds now showing correctly
too.

## Known limitations

None noted at the time.

## Follow-up recommendations

None noted at the time — but see `memory/coding_standards.md`, which extracted the durable lesson
from this fix (the `f_`-prefix naming convention for filter inputs) so future tables avoid the
same class of bug.
