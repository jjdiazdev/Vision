# ISSUE STRUCTURE TEMPLATE

## User Story
As a developer, I want a robust system prompt so that the LLM reliably outputs structured JSON for function execution.

## Goal
Design and implement a specialized System Prompt that constrains the LLM to act as a "JSON-only Router."

## Context
Llama 3.1 and Phi-3.5 are capable but need clear instructions to avoid conversational filler and ensure they only return the expected JSON format for tool calls.

## Scope
### Files to Create/Update:
- `orchestrator/prompts.py`

### Events/Triggers (if applicable):
- LLM API call.

## Expected Behavior
- `prompts.py` contains a constant `SYSTEM_PROMPT`.
- The prompt instructs the LLM to analyze user input and select a tool from the manifest.
- The prompt forces a JSON output: `{"action": "...", "params": {...}}`.
- No additional text should be returned by the LLM.

## Future Contract
Provides the "brain" of the system with its core instructions. Can be refined later for better intent matching.

## Out of Scope
- Implementing the Python Orchestrator class.
- Frontend integration.

## Hard Constraints
- Do not move application code unless specified.
- Do not delete or migrate `.agent` content.
- Prompt must be model-agnostic where possible.

## Definition of Done (DoD)
- [ ] `orchestrator/prompts.py` created.
- [ ] `SYSTEM_PROMPT` is descriptive and restrictive.
- [ ] Tested with sample inputs to ensure JSON-only output.
- [ ] Final Issue Report created in the correct directory.

## Required Final Report
Path: `docs/reports/issues/06-prompt-engineering.md`
Structure:
# Issue Report: Prompt Engineering
## Summary
## Files Changed
## Validation Performed
## Known Limitations
## Follow-up Recommendations

## Prompt (Agent Instruction)
> Create `orchestrator/prompts.py`. Write a `SYSTEM_PROMPT` that includes the tool manifest (import from `manifest.py`) and explicit instructions to return ONLY JSON in the format `{"action": "...", "params": {...}}`.
