# ISSUE STRUCTURE TEMPLATE

## User Story
As a user, I want the dashboard to update automatically when the Agent performs an action so that I always see the latest data.

## Goal
Modify the `/agent/chat` response to include Out-of-Band (OOB) HTML updates for relevant UI components.

## Context
When the Agent creates a project or updates a task, the chat message confirms the action, but the UI tables might still show old data. HTMX OOB allow us to update multiple parts of the page in a single response.

## Scope
### Files to Create/Update:
- `dashboard_app/app/main/routes.py`
- `dashboard_app/app/templates/partials/_projects_table.html`
- `dashboard_app/app/templates/partials/_tasks_table.html`

### Events/Triggers (if applicable):
- Agent action completion.

## Expected Behavior
- If the Agent's action affects projects, the `/agent/chat` response should include the updated `_projects_table.html` partial with `hx-swap-oob="true"`.
- If it affects tasks, include `_tasks_table.html`.
- The frontend should automatically replace the corresponding elements.

## Future Contract
Ensures the dashboard feels like a "Live" system.

## Out of Scope
- WebSockets or Server-Sent Events (keeping it simple with HTMX).
- Optimistic UI updates.

## Hard Constraints
- Do not move application code unless specified.
- Do not delete or migrate `.agent` content.
- Must use `hx-swap-oob`.

## Definition of Done (DoD)
- [ ] `/agent/chat` route updated to conditionally include OOB partials.
- [ ] Partials verified to have `hx-swap-oob="true"`.
- [ ] UI updates correctly after an Agent command.
- [ ] Final Issue Report created in the correct directory.

## Required Final Report
Path: `docs/reports/issues/16-htmx-oob-updates.md`
Structure:
# Issue Report: HTMX OOB Updates
## Summary
## Files Changed
## Validation Performed
## Known Limitations
## Follow-up Recommendations

## Prompt (Agent Instruction)
> Modify `dashboard_app/app/main/routes.py`. Based on the `action` executed by the `Orchestrator`, render the relevant dashboard partials alongside the chat message. Ensure the partials have the `hx-swap-oob="true"` attribute.
