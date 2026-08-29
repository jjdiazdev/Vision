# ISSUE STRUCTURE TEMPLATE

## User Story
As a user, I want my chat messages to be processed by the AI and the responses displayed in the chat window without a page reload.

## Goal
Create the `/agent/chat` Flask endpoint and use HTMX to handle message submission and response appending.

## Context
We need a bridge between the frontend chat UI and the backend Orchestrator. HTMX is ideal for this partial page update workflow.

## Scope
### Files to Create/Update:
- `dashboard_app/app/main/routes.py`
- `dashboard_app/app/templates/base.html`
- `dashboard_app/app/templates/partials/_chat_message.html`

### Events/Triggers (if applicable):
- Form submission in the chat window (`hx-post`).

## Expected Behavior
- `/agent/chat` endpoint (POST) receives the user's message.
- The endpoint calls the `Orchestrator` (Phase 2).
- The endpoint returns an HTML partial (`_chat_message.html`) containing the Agent's response.
- HTMX appends this partial to the chat history list using `hx-swap="beforeend"`.

## Future Contract
Enables real-time interaction with the AI. Sets the stage for OOB updates in Phase 5.

## Out of Scope
- Voice-to-text.
- Real-time UI syncing (Phase 5).

## Hard Constraints
- Do not move application code unless specified.
- Do not delete or migrate `.agent` content.
- Use HTMX for the communication pipeline.

## Definition of Done (DoD)
- [ ] `/agent/chat` route implemented in `routes.py`.
- [ ] Chat form in `base.html` configured with `hx-post`.
- [ ] Responses are correctly appended to the chat window.
- [ ] Final Issue Report created in the correct directory.

## Required Final Report
Path: `docs/reports/issues/10-htmx-messaging-pipeline.md`
Structure:
# Issue Report: HTMX Messaging Pipeline
## Summary
## Files Changed
## Validation Performed
## Known Limitations
## Follow-up Recommendations

## Prompt (Agent Instruction)
> Add a `/agent/chat` route to `dashboard_app/app/main/routes.py`. It should take a `message` from form data, call `Orchestrator().process_command()`, and return a rendered partial. Update the chat form in `base.html` to use `hx-post="/agent/chat"`.
