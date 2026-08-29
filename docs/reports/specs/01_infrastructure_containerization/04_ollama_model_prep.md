# ISSUE STRUCTURE TEMPLATE

## User Story
As a developer, I want the AI service to be ready as soon as the containers start so that I don't have to manually pull models.

## Goal
Create an entrypoint script for the Ollama container to automatically pull the configured model on startup.

## Context
The Ollama Docker image starts empty. To ensure the orchestrator works immediately, we need a way to automate the `ollama pull [model]` command.

## Scope
### Files to Create/Update:
- `docker/ollama/entrypoint.sh`
- `docker-compose.yml` (Update to use entrypoint)

### Events/Triggers (if applicable):
- Ollama container startup.

## Expected Behavior
- When the `ollama` container starts, it should check if the model specified in `OLLAMA_MODEL` exists.
- If not, it should pull the model from the Ollama registry.
- The service should remain running and ready to accept API calls.

## Future Contract
Ensures a "zero-config" startup experience for the entire AI-powered dashboard.

## Out of Scope
- Fine-tuning models.
- Handling multiple models simultaneously (for now).

## Hard Constraints
- Do not move application code unless specified.
- Do not delete or migrate `.agent` content.
- Ensure the script is executable.

## Definition of Done (DoD)
- [ ] `entrypoint.sh` created and tested.
- [ ] `docker-compose.yml` configured to use the entrypoint.
- [ ] Verified that `docker-compose up` results in the model being pulled and service becoming ready.
- [ ] Final Issue Report created in the correct directory.

## Required Final Report
Path: `docs/reports/issues/04-ollama-model-prep.md`
Structure:
# Issue Report: Ollama Model Preparation
## Summary
## Files Changed
## Validation Performed
## Known Limitations
## Follow-up Recommendations

## Prompt (Agent Instruction)
> Create `docker/ollama/entrypoint.sh`. The script should start the ollama server in the background, wait for it to be ready, run `ollama pull $OLLAMA_MODEL`, and then bring the server process to the foreground. Update `docker-compose.yml` accordingly.
