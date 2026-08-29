# ISSUE STRUCTURE TEMPLATE

## User Story
As a developer, I want a Python service that handles the LLM interaction loop so that I can easily process user commands.

## Goal
Develop the `Orchestrator` class that bridges user input, Ollama API, and `agent_actions.py`.

## Context
The Orchestrator is the central hub. it sends the prompt to Ollama, receives JSON, and executes the corresponding Python function.

## Scope
### Files to Create/Update:
- `orchestrator/brain.py`

### Events/Triggers (if applicable):
- `/agent/chat` endpoint call (Phase 3).

## Expected Behavior
- `Orchestrator` class with a `process_command(user_input)` method.
- It should call the Ollama API using `requests` or an official library.
- It should parse the JSON response.
- It should dynamically call functions in `execution/agent_actions.py` based on the `action` key.

## Future Contract
Acts as the engine for all AI-driven actions in the dashboard.

## Out of Scope
- Frontend UI.
- Complex error recovery (dealt with in 2.4).

## Hard Constraints
- Do not move application code unless specified.
- Do not delete or migrate `.agent` content.
- Ensure efficient API usage.

## Definition of Done (DoD)
- [ ] `orchestrator/brain.py` implemented.
- [ ] Successfully parses a "test" JSON from the LLM.
- [ ] Successfully calls a real function in `agent_actions.py` (e.g., `list_projects`).
- [ ] Final Issue Report created in the correct directory.

## Required Final Report
Path: `docs/reports/issues/07-orchestrator-class-impl.md`
Structure:
# Issue Report: Orchestrator Class Implementation
## Summary
## Files Changed
## Validation Performed
## Known Limitations
## Follow-up Recommendations

## Prompt (Agent Instruction)
> Implement `orchestrator/brain.py`. Create an `Orchestrator` class. Use `requests` to talk to Ollama. Use the system prompt and tool manifest. Dynamically execute functions from `execution.agent_actions`.
