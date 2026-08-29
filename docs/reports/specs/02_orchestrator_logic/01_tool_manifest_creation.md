# ISSUE STRUCTURE TEMPLATE

## User Story
As a developer, I want a structured list of available agent actions so that the LLM knows exactly what tools it can use.

## Goal
Create a `manifest.json` or a Python dictionary that describes all functions in `execution/agent_actions.py`.

## Context
The LLM needs to know the names, descriptions, and required arguments of our Python functions to generate the correct JSON routing commands. This manifest acts as the "Tool Specification" for the AI.

## Scope
### Files to Create/Update:
- `orchestrator/manifest.py` (or `manifest.json`)
- `execution/agent_actions.py` (Verify function signatures)

### Events/Triggers (if applicable):
- Orchestrator initialization.

## Expected Behavior
- A structured data object containing all relevant actions from `agent_actions.py`.
- Each action should have: `name`, `description`, and `parameters` (with types).
- Example: `create_project(name, status)` -> `{ "name": "create_project", "description": "Creates a new project", "parameters": { "name": "string", "status": "string" } }`

## Future Contract
Enables the Orchestrator to dynamically generate system prompts and validate LLM outputs against known tools.

## Out of Scope
- Implementing the LLM routing logic.
- Adding new functions to `agent_actions.py`.

## Hard Constraints
- Do not move application code unless specified.
- Do not delete or migrate `.agent` content.
- Ensure the manifest stays in sync with `agent_actions.py`.

## Definition of Done (DoD)
- [ ] `orchestrator/manifest.py` created and populated.
- [ ] All functions in `agent_actions.py` are represented.
- [ ] Data structure is clean and easy for an LLM to parse.
- [ ] Final Issue Report created in the correct directory.

## Required Final Report
Path: `docs/reports/issues/05-tool-manifest-creation.md`
Structure:
# Issue Report: Tool Manifest Creation
## Summary
## Files Changed
## Validation Performed
## Known Limitations
## Follow-up Recommendations

## Prompt (Agent Instruction)
> Analyze `execution/agent_actions.py`. Create `orchestrator/manifest.py` containing a list of dictionaries describing each function. Focus on `name`, `description`, and `parameters`.
