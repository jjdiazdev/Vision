# ISSUE STRUCTURE TEMPLATE

## User Story
As a developer, I want a containerized environment so that the web app and AI services run consistently across different machines.

## Goal
Create a `docker-compose.yml` to orchestrate the Flask web application and the Ollama AI service.

## Context
The project is currently running locally. To integrate AI capabilities reliably, we need a stable, isolated environment where the Flask app can communicate with the Ollama service. Data persistence for the SQLite database is critical.

## Scope
### Files to Create/Update:
- `docker-compose.yml`
- `Dockerfile` (Web service)
- `.dockerignore`

### Events/Triggers (if applicable):
- Manual deployment or CI/CD pipeline trigger.

## Expected Behavior
- `docker-compose up` should build and start two services: `web` and `ollama`.
- The `web` service should run the Flask app on port 5000.
- The `ollama` service should be accessible by the `web` service.
- Shared volumes should be configured for `dashboard_app/instance/app.db` to ensure data persists.

## Future Contract
Sets the stage for AI-orchestration by providing the necessary compute infrastructure. Networking between services is established here.

## Out of Scope
- Implementing the AI logic itself.
- Production-grade security hardening (SSL, etc.).

## Hard Constraints
- Do not move application code unless specified.
- Do not delete or migrate `.agent` content.
- Do not add unapproved dependencies.
- Ensure SQLite database is shared correctly via volumes.

## Definition of Done (DoD)
- [ ] `docker-compose.yml` created and functional.
- [ ] `Dockerfile` for the web service builds successfully.
- [ ] Services can communicate over the internal network.
- [ ] SQLite database persists after container restart.
- [ ] Final Issue Report created in the correct directory.

## Required Final Report
Path: `docs/reports/issues/01-docker-compose-setup.md`
Structure:
# Issue Report: Docker Compose Setup
## Summary
## Files Changed
## Validation Performed
## Known Limitations
## Follow-up Recommendations

## Prompt (Agent Instruction)
> Create a `docker-compose.yml` file in the root directory. Define a `web` service using a `Dockerfile` (to be created) and an `ollama` service using the official `ollama/ollama` image. Ensure volumes are mapped for the SQLite database and Ollama models. Test that both services start correctly.
