# ISSUE STRUCTURE TEMPLATE

## User Story
As a user, I want a visual indicator when the Agent is "thinking" so that I know my command is being processed.

## Goal
Implement a "Pulse" animation in the HUD Core using Alpine.js and CSS that activates during HTMX requests to the Agent.

## Context
AI responses can take a few seconds. A visual feedback loop prevents the user from thinking the app has frozen.

## Scope
### Files to Create/Update:
- `dashboard_app/app/templates/base.html`
- `dashboard_app/app/static/css/style.css`

### Events/Triggers (if applicable):
- `htmx:configRequest` and `htmx:afterRequest` events.

## Expected Behavior
- A `processing` state in Alpine.js toggled by HTMX events.
- When `processing` is true, the `hud-core` should have a "pulsing" CSS animation.
- The animation should stop once the response is received.

## Future Contract
Improves perceived performance and UX.

## Out of Scope
- Updating actual dashboard data.
- Voice feedback.

## Hard Constraints
- Do not move application code unless specified.
- Do not delete or migrate `.agent` content.
- Animation must be performant.

## Definition of Done (DoD)
- [ ] CSS "pulse" animation added to `style.css`.
- [ ] Alpine.js logic in `base.html` listens for HTMX events and toggles a `processing` class.
- [ ] Visual verification of the pulse during chat interaction.
- [ ] Final Issue Report created in the correct directory.

## Required Final Report
Path: `docs/reports/issues/11-hud-pulse-loading.md`
Structure:
# Issue Report: HUD Pulse Loading State
## Summary
## Files Changed
## Validation Performed
## Known Limitations
## Follow-up Recommendations

## Prompt (Agent Instruction)
> Define a `@keyframes pulse` in `style.css`. In `base.html`, use `htmx:beforeRequest` to set `processing = true` and `htmx:afterRequest` to set it to `false`. Apply the animation to `.hud-core` when `processing` is true.
