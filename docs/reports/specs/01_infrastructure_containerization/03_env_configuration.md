# ISSUE STRUCTURE TEMPLATE

## User Story
As a developer, I want a centralized configuration system so that I can easily change AI models and service endpoints without modifying code.

## Goal
Setup and standardize `.env` files and configuration logic to handle Ollama and container-specific settings.

## Context
We need to manage environment-specific variables like `OLLAMA_API_BASE`, `OLLAMA_MODEL`, and database paths. Using `.env` files is the standard approach for this.

## Scope
### Files to Create/Update:
- `.env` (Root)
- `dashboard_app/config.py`
- `.env.example`

### Events/Triggers (if applicable):
- Application startup.

## Expected Behavior
- `.env` file contains `OLLAMA_MODEL=llama3.1` (or similar).
- `config.py` reads these variables and makes them available to the Flask app.
- Clear `.env.example` provided for new developers.

## Future Contract
Provides the foundation for Phase 2 (Orchestrator) to know which model to use and where to find the Ollama API.

## Out of Scope
- Creating the Orchestrator logic.
- Storing secrets (API keys) in version control.

## Hard Constraints
- Do not move application code unless specified.
- Do not delete or migrate `.agent` content.
- Do not commit actual `.env` files to git.

## Definition of Done (DoD)
- [ ] `.env` and `.env.example` updated with AI-related variables.
- [ ] `dashboard_app/config.py` updated to parse these variables.
- [ ] App starts and logs (in debug mode) that it has loaded the configuration.
- [ ] Final Issue Report created in the correct directory.

## Required Final Report
Path: `docs/reports/issues/03-env-configuration.md`
Structure:
# Issue Report: Environment Configuration
## Summary
## Files Changed
## Validation Performed
## Known Limitations
## Follow-up Recommendations

## Prompt (Agent Instruction)
> Update the `.env.example` and create a `.env` file with `OLLAMA_MODEL` and `OLLAMA_HOST`. Update `dashboard_app/config.py` to include these as class attributes.
