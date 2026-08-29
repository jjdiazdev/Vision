# ISSUE STRUCTURE TEMPLATE

## User Story
As a user, I want a clear visual indicator that the dashboard is listening to my voice so that I don't start speaking too early or too late.

## Goal
Create a "Recording" UI state in the HUD that activates during voice recognition.

## Context
Voice interaction requires immediate visual feedback to feel responsive and high-tech.

## Scope
### Files to Create/Update:
- `dashboard_app/app/templates/base.html`
- `dashboard_app/app/static/css/style.css`

### Events/Triggers (if applicable):
- `recording` state change in Alpine.js.

## Expected Behavior
- When `recording` is true, the Voice button in the HUD should glow red or have a unique animation.
- A "Listening..." tooltip or overlay should appear.
- The HUD core could also change color (e.g., from blue to orange/red).

## Future Contract
Enhances the "Iron Man" HUD aesthetic and improves usability.

## Out of Scope
- Actually sending the transcript (Phase 4.3).
- Advanced audio visualization (oscilloscopes, etc.).

## Hard Constraints
- Do not move application code unless specified.
- Do not delete or migrate `.agent` content.
- Must not interfere with existing HUD animations.

## Definition of Done (DoD)
- [ ] CSS styles for "recording" state added.
- [ ] Alpine.js in `base.html` toggles the visual state correctly.
- [ ] User testing confirms the feedback is clear.
- [ ] Final Issue Report created in the correct directory.

## Required Final Report
Path: `docs/reports/issues/13-visual-voice-feedback.md`
Structure:
# Issue Report: Visual Voice Feedback
## Summary
## Files Changed
## Validation Performed
## Known Limitations
## Follow-up Recommendations

## Prompt (Agent Instruction)
> Update `style.css` with a `.hud-recording` class that changes the HUD core's glow color and adds a pulse to the mic icon. Link this class to the `recording` variable in `base.html`.
