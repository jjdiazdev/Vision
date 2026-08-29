# ISSUE STRUCTURE TEMPLATE

## User Story
As a developer, I want to ensure the AI doesn't perform dangerous or invalid actions so that the system remains stable.

## Goal
Implement a validation layer within the Orchestrator to sanitize and verify LLM-generated commands.

## Context
LLMs can hallucinate or produce malformed JSON. We need a "Sanity Check" before executing any Python code.

## Scope
### Files to Create/Update:
- `orchestrator/brain.py` (Update)
- `orchestrator/validator.py`

### Events/Triggers (if applicable):
- Post-LLM response, Pre-execution.

## Expected Behavior
- Validate that the `action` exists in the manifest.
- Validate that `params` match the function signature.
- Handle malformed JSON gracefully by returning an error message to the user instead of crashing.

## Future Contract
Improves system reliability and security by preventing "Prompt Injection" or "Hallucination-driven" errors.

## Out of Scope
- Full-scale security audit.
- Advanced parameter type checking (keep it simple for now).

## Hard Constraints
- Do not move application code unless specified.
- Do not delete or migrate `.agent` content.
- Must not block valid commands.

## Definition of Done (DoD)
- [ ] Validation logic implemented in `orchestrator/validator.py`.
- [ ] Orchestrator updated to use the validator.
- [ ] Test with "bad" JSON to ensure it is caught.
- [ ] Final Issue Report created in the correct directory.

## Required Final Report
Path: `docs/reports/issues/08-action-validation-layer.md`
Structure:
# Issue Report: Action Validation Layer
## Summary
## Files Changed
## Validation Performed
## Known Limitations
## Follow-up Recommendations

## Prompt (Agent Instruction)
> Create `orchestrator/validator.py`. Implement checks for action existence and parameter counts. Integrate this into the `Orchestrator.process_command` loop in `brain.py`.
