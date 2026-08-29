# ISSUE STRUCTURE TEMPLATE

## User Story
As a user, I want to receive HUD alerts for background events so that I'm aware of errors or successful completion of long-running tasks.

## Goal
Implement a "HUD Alert" component in Alpine.js that displays temporary notifications in the corner of the screen.

## Context
While the chat window shows the dialogue, some actions might require a more "system-level" notification (e.g., "Database Backup Complete" or "Error: Ollama Offline").

## Scope
### Files to Create/Update:
- `dashboard_app/app/templates/base.html`
- `dashboard_app/app/static/css/style.css`

### Events/Triggers (if applicable):
- Custom JS events or HTMX headers.

## Expected Behavior
- An `alerts` array in Alpine.js.
- A notification container in `base.html` that loops through `alerts`.
- Styled to match the HUD's futuristic aesthetic.
- Alerts should auto-dismiss after 5 seconds.

## Future Contract
Provides a generic notification system for all future agentic features.

## Out of Scope
- Persistent notification history.
- Sound effects (SFX).

## Hard Constraints
- Do not move application code unless specified.
- Do not delete or migrate `.agent` content.
- Must not block the main HUD buttons.

## Definition of Done (DoD)
- [ ] Alert component implemented in `base.html`.
- [ ] CSS animations for entrance/exit added.
- [ ] Successfully triggered an alert from a JS console command.
- [ ] Final Issue Report created in the correct directory.

## Required Final Report
Path: `docs/reports/issues/18-notification-system.md`
Structure:
# Issue Report: Notification System
## Summary
## Files Changed
## Validation Performed
## Known Limitations
## Follow-up Recommendations

## Prompt (Agent Instruction)
> Create a notification system using Alpine.js in `base.html`. Add an `alerts` list to the `x-data`. Use `x-for` to render them in a styled container. Add a function `addAlert(message, type)` to the global scope.
