# ISSUE STRUCTURE TEMPLATE

## User Story
As a user, I want the dashboard to know when I've finished speaking so that I don't have to manually click "Send" for voice commands.

## Goal
Implement client-side silence detection to automatically finalize voice input after a period of inactivity.

## Context
A truly seamless voice experience doesn't require "push-to-talk" for ending a command. Automatic detection makes the agent feel more natural.

## Scope
### Files to Create/Update:
- `dashboard_app/app/static/js/voice.js`

### Events/Triggers (if applicable):
- `SpeechRecognition` continuous mode / timer.

## Expected Behavior
- Use a timer that resets on every `speechstart` or `result` event.
- If no speech is detected for 2 seconds, call `recognition.stop()`.
- Ensure this doesn't trigger on minor pauses (fine-tune the threshold).

## Future Contract
Refines the UX for all voice-driven interactions.

## Out of Scope
- Server-side VAD (Voice Activity Detection).
- Background noise cancellation.

## Hard Constraints
- Do not move application code unless specified.
- Do not delete or migrate `.agent` content.
- Threshold must be configurable.

## Definition of Done (DoD)
- [ ] Silence detection logic added to `voice.js`.
- [ ] Voice input automatically stops and sends after a pause.
- [ ] No false-positive triggers during normal speech.
- [ ] Final Issue Report created in the correct directory.

## Required Final Report
Path: `docs/reports/issues/15-silence-detection.md`
Structure:
# Issue Report: Silence Detection
## Summary
## Files Changed
## Validation Performed
## Known Limitations
## Follow-up Recommendations

## Prompt (Agent Instruction)
> Implement a `setTimeout` based silence detector in `voice.js`. Reset the timer on `onspeechstart`. When the timer expires (2s), stop the recognition and let the transcription pipeline handle the result.
