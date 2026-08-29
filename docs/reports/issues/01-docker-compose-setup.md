# Issue Report: Docker Compose Setup

## Summary
The project has been containerized using Docker and Docker Compose. This setup includes two services:
- `web`: A Flask-based web application running in a Python 3.11 environment.
- `ollama`: The official Ollama AI service for running local LLMs.

The setup ensures that both the SQLite database and Ollama models are persisted using Docker volumes.

## Files Changed
- `Dockerfile`: Multi-stage-like build for the Flask application.
- `docker-compose.yml`: Orchestration file for the `web` and `ollama` services.
- `.dockerignore`: Optimized to keep the build context clean and fast.

## Validation Performed
- **Build Success**: `docker-compose build` completed without errors.
- **Service Orchestration**: `docker-compose up -d` successfully starts both services.
- **Connectivity**: Verified that the `web` service can reach the `ollama` service at `http://ollama:11434` using `requests` inside the container.
- **Persistence**: 
    - Verified that `dashboard_app/instance/app.db` on the host is correctly mapped to the container.
    - Verified that changes made in the container's `instance` folder reflect on the host.
- **Port Conflict Resolution**: Mapped host port `5001` to container port `5000` to avoid conflicts with macOS system services (AirPlay Receiver).

## Known Limitations
- The `ollama` service starts without any pre-loaded models. Models must be pulled manually or via a future entrypoint script (planned for Milestone 01.04).
- The Flask application is running using the development server (`flask run`).

## Follow-up Recommendations
- Implement `02_db_wal_verification.md` to ensure SQLite's Write-Ahead Logging is compatible with the containerized volume.
- Implement `03_env_configuration.md` to standardize environment variables like `OLLAMA_MODEL` and `OLLAMA_HOST` in `config.py`.
- Implement `04_ollama_model_prep.md` to automate model pulling on container startup.
