# ISSUE STRUCTURE TEMPLATE

## User Story
As a user, I want my voice transcripts to be automatically sent to the Agent so that I can command the dashboard by voice alone.

## Goal
Connect the voice transcription output to the `/agent/chat` HTMX pipeline.

## Context
Once we have the text transcript from the Web Speech API, we need to treat it exactly like a text message sent via the chat window.

## Scope
### Files to Create/Update:
- `dashboard_app/app/templates/base.html`
- `dashboard_app/app/static/js/voice.js`

### Events/Triggers (if applicable):
- `SpeechRecognition` result event.

## Expected Behavior
- When a transcript is finalized, Alpine.js should populate the chat input.
- Alpine.js should then trigger the `hx-post="/agent/chat"` request automatically.
- The Agent's response should appear in the chat window as if it were a typed command.

## Future Contract
Completes the voice-to-action loop.

## Out of Scope
- TTS (Text-to-Speech) for the Agent's response.
- Offline recognition.

## Hard Constraints
- Do not move application code unless specified.
- Do not delete or migrate `.agent` content.
- Must reuse the existing HTMX pipeline for consistency.

## Definition of Done (DoD)
- [ ] `voice.js` updated to trigger an event with the transcript.
- [ ] `base.html` updated to listen for this event and trigger HTMX.
- [ ] Voice command successfully creates a project or updates a task.
- [ ] Final Issue Report created in the correct directory.

## Required Final Report
Path: `docs/reports/issues/14-transcription_pipeline.md`
Structure:
# Issue Report: Transcription Pipeline
## Summary
## Files Changed
## Validation Performed
## Known Limitations
## Follow-up Recommendations

## Prompt (Agent Instruction)
> In `voice.js`, on the `onresult` event, dispatch a custom event `voice-transcript` with the text. In `base.html`, listen for this event, set the chat input value, and use `htmx.trigger('#chat-form', 'submit')`.
