# ISSUE STRUCTURE TEMPLATE

## User Story
As a developer, I want to ensure the LLM correctly maps user requests to actions so that the system is reliable and predictable.

## Goal
Create a suite of test sentences to evaluate and improve the intent matching of the Orchestrator.

## Context
Natural language is messy. We need to ensure that different ways of saying the same thing (e.g., "Add John" vs "Create a new employee named John") all lead to the correct function call.

## Scope
### Files to Create/Update:
- `tests/test_intents.py`
- `orchestrator/prompts.py` (Refine based on tests)

### Events/Triggers (if applicable):
- Running the test suite.

## Expected Behavior
- A Python test script that loops through a list of input sentences.
- It compares the LLM's output `action` and `params` against an expected "Golden Set."
- Results should be logged to track accuracy.

## Future Contract
Ensures regression testing for the AI's "brain" as we update models or prompts.

## Out of Scope
- End-to-end UI testing.
- Load testing.

## Hard Constraints
- Do not move application code unless specified.
- Do not delete or migrate `.agent` content.
- Must run without requiring a GPU (if testing against remote/local API).

## Definition of Done (DoD)
- [ ] `tests/test_intents.py` implemented.
- [ ] At least 20 test cases covering projects, tasks, and employees.
- [ ] Prompt refined until accuracy is >90% for core actions.
- [ ] Final Issue Report created in the correct directory.

## Required Final Report
Path: `docs/reports/issues/19-intent-testing.md`
Structure:
# Issue Report: Intent Testing
## Summary
## Files Changed
## Validation Performed
## Known Limitations
## Follow-up Recommendations

## Prompt (Agent Instruction)
> Create `tests/test_intents.py`. Use `unittest` or `pytest`. Define a list of strings and their expected JSON tool calls. Run them through `Orchestrator.process_command` and assert equality.
