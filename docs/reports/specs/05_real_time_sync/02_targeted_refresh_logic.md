# ISSUE STRUCTURE TEMPLATE

## User Story
As a user, I want only the relevant parts of the UI to refresh when a change occurs so that the app remains fast and responsive.

## Goal
Refine the OOB update logic to be more targeted (e.g., updating a single row instead of an entire table).

## Context
Full table refreshes can be jarring if the user is interacting with another part of the table. Targeted refreshes improve the SPA feel.

## Scope
### Files to Create/Update:
- `dashboard_app/app/main/routes.py`
- `dashboard_app/app/templates/partials/_task_row.html` (New)

### Events/Triggers (if applicable):
- Specific task or project update.

## Expected Behavior
- Create smaller partials for individual components (like a single task row).
- Update the Orchestrator/Routes to return these specific partials with OOB.
- Use DOM IDs to ensure HTMX targets the correct element.

## Future Contract
Optimizes performance for large data sets.

## Out of Scope
- Batch updates (handle one by one for now).
- Client-side DOM diffing.

## Hard Constraints
- Do not move application code unless specified.
- Do not delete or migrate `.agent` content.
- Must maintain consistent IDs between the full table and the row partials.

## Definition of Done (DoD)
- [ ] `_task_row.html` partial created.
- [ ] Route updated to return single row OOB.
- [ ] Verified that only the affected row flashes/updates in the UI.
- [ ] Final Issue Report created in the correct directory.

## Required Final Report
Path: `docs/reports/issues/17-targeted-refresh-logic.md`
Structure:
# Issue Report: Targeted Refresh Logic
## Summary
## Files Changed
## Validation Performed
## Known Limitations
## Follow-up Recommendations

## Prompt (Agent Instruction)
> Create `dashboard_app/app/templates/partials/_task_row.html`. Extract the `<tr>` logic from `_tasks_table.html`. Update the `/agent/chat` route to return this row partial with `hx-swap-oob="true"` using the task's ID as the target.
