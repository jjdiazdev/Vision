# ISSUE STRUCTURE TEMPLATE

## User Story
As a user, I want the dashboard to remain functional even if the AI service is down or slow so that my experience isn't interrupted by technical glitches.

## Goal
Implement robust error handling for Ollama API failures, timeouts, and malformed model responses.

## Context
Local LLMs can be resource-intensive and might fail or time out. The UI should handle these cases without crashing.

## Scope
### Files to Create/Update:
- `orchestrator/brain.py`
- `dashboard_app/app/main/routes.py`

### Events/Triggers (if applicable):
- Network failure, Ollama crash, or Model timeout.

## Expected Behavior
- Orchestrator should catch `requests.exceptions.RequestException`.
- Implement a 30-second timeout for LLM calls.
- Return a user-friendly error message (via the Notification System) if the service is unavailable.

## Future Contract
Improves the overall resilience of the Agentic SPA.

## Out of Scope
- Implementing an offline fallback model.
- Automatic service restart.

## Hard Constraints
- Do not move application code unless specified.
- Do not delete or migrate `.agent` content.
- Error messages must not leak internal stack traces.

## Definition of Done (DoD)
- [ ] Error handling added to `brain.py`.
- [ ] Timeout logic implemented.
- [ ] Tested by stopping the Ollama container and verifying the UI alert.
- [ ] Final Issue Report created in the correct directory.

## Required Final Report
Path: `docs/reports/issues/20-error-handling-robustness.md`
Structure:
# Issue Report: Error Handling Robustness
## Summary
## Files Changed
## Validation Performed
## Known Limitations
## Follow-up Recommendations

## Prompt (Agent Instruction)
> Wrap the `requests.post` call in `brain.py` with a `try/except` block. Handle `Timeout` and `ConnectionError`. Return a specific error JSON that the route can use to trigger a HUD alert.
