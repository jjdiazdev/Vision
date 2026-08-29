# Issue Report: Ollama Model Preparation

## Summary
The Ollama service has been enhanced with an automated model preparation mechanism. An entrypoint script now ensures that the required AI model is pulled and ready for use as soon as the container starts.

## Files Changed
- `docker/ollama/entrypoint.sh`: A new bash script that:
    - Starts the Ollama server in the background.
    - Waits for the server to become responsive.
    - Checks if the model specified in `OLLAMA_MODEL` exists.
    - Pulls the model if it is missing.
    - Brings the server process to the foreground to keep the container alive.
- `docker-compose.yml`:
    - Mounted the `entrypoint.sh` script into the `ollama` container.
    - Configured the `ollama` service to use the script as its entrypoint.
    - Set `OLLAMA_HOST=0.0.0.0` for the `ollama` service to allow cross-container communication.
    - Added `env_file: .env` to pass configuration variables.

## Validation Performed
- **Automated Pull**: Observed the `ollama` container logs during startup; verified that it correctly identified the missing `phi3.5` model and initiated the pull process.
- **Service Availability**: Confirmed that the server listens on `[::]:11434`, making it accessible to the `web` service.
- **Idempotency**: The script checks for the model's existence before pulling, preventing redundant downloads on subsequent restarts.

## Known Limitations
- Model pulling can be time-consuming depending on the model size and network speed. The service is only fully "ready" once the pull completes.
- Disk space: Ensure the host has enough space for the models in the `ollama_data` volume.

## Follow-up Recommendations
- Consider using a faster or smaller model for initial development/testing to reduce startup time.
- Implement health checks in `docker-compose.yml` for the `ollama` service so that the `web` service waits until the model is fully pulled.
