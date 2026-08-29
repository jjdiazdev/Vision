# ISSUE STRUCTURE TEMPLATE

## User Story
As a user, I want a persistent chat interface in the HUD so that I can interact with the AI agent from any page.

## Goal
Implement chat window state management using Alpine.js and update the HUD UI to include a chat panel.

## Context
The Iron Man HUD currently has a chat button but no functional window. We need to manage the `chatOpen` state globally in `base.html`.

## Scope
### Files to Create/Update:
- `dashboard_app/app/templates/base.html`
- `dashboard_app/app/static/css/style.css`

### Events/Triggers (if applicable):
- Clicking the Chat button in the HUD.

## Expected Behavior
- Alpine.js `x-data` in `base.html` updated to include `chatOpen: false`.
- A chat window component added to `base.html` that toggles visibility based on `chatOpen`.
- The chat window should be positioned appropriately within the HUD layout.

## Future Contract
Prepares the UI for the messaging pipeline (Phase 3.2).

## Out of Scope
- Implementing the backend `/agent/chat` endpoint.
- Adding voice recognition.

## Hard Constraints
- Do not move application code unless specified.
- Do not delete or migrate `.agent` content.
- HUD rings and core must remain functional.

## Definition of Done (DoD)
- [ ] `base.html` updated with Alpine.js state.
- [ ] Chat window UI added and styled.
- [ ] Clicking the chat button toggles the window correctly.
- [ ] Final Issue Report created in the correct directory.

## Required Final Report
Path: `docs/reports/issues/09-hud-state-management.md`
Structure:
# Issue Report: HUD State Management
## Summary
## Files Changed
## Validation Performed
## Known Limitations
## Follow-up Recommendations

## Prompt (Agent Instruction)
> Update `dashboard_app/app/templates/base.html`. Add `chatOpen` to the `x-data` object in the HUD container. Create a chat window `div` that uses `x-show="chatOpen"`. Style it in `style.css` to fit the "Iron Man" aesthetic.
