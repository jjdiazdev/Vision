# ISSUE STRUCTURE TEMPLATE

## User Story
As a user, I want to dictate commands using my voice so that I can interact with the dashboard hands-free.

## Goal
Integrate the browser's Web Speech API with Alpine.js to enable voice transcription in the HUD.

## Context
The "Iron Man" dashboard experience is incomplete without voice commands. Modern browsers provide the `SpeechRecognition` API which we can leverage.

## Scope
### Files to Create/Update:
- `dashboard_app/app/static/js/voice.js`
- `dashboard_app/app/templates/base.html`

### Events/Triggers (if applicable):
- Clicking the Voice button in the HUD.

## Expected Behavior
- A JavaScript service that initializes `window.SpeechRecognition`.
- Alpine.js in `base.html` should be able to start/stop the recognition.
- Transcription results should be captured and stored in an Alpine.js variable.

## Future Contract
Provides the raw text input for the transcription pipeline (Phase 4.3).

## Out of Scope
- Backend processing of voice data (handled via text).
- Multilingual support (default to browser locale).

## Hard Constraints
- Do not move application code unless specified.
- Do not delete or migrate `.agent` content.
- Must handle "Permission Denied" errors gracefully.

## Definition of Done (DoD)
- [ ] `voice.js` implemented and included in `base.html`.
- [ ] Voice button in HUD toggles the recognition engine.
- [ ] Console log or UI feedback shows successful transcription.
- [ ] Final Issue Report created in the correct directory.

## Required Final Report
Path: `docs/reports/issues/12-web-speech-api-integration.md`
Structure:
# Issue Report: Web Speech API Integration
## Summary
## Files Changed
## Validation Performed
## Known Limitations
## Follow-up Recommendations

## Prompt (Agent Instruction)
> Create `dashboard_app/app/static/js/voice.js`. Implement a class or function that wraps `webkitSpeechRecognition`. Export it so Alpine.js in `base.html` can use it to start/stop recording.
