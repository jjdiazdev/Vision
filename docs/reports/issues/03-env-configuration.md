# Issue Report: Environment Configuration

## Summary
The environment configuration has been standardized to support AI-powered features, specifically focusing on Ollama integration. A centralized `.env` system is now in place, and the Flask application has been updated to parse and expose these settings.

## Files Changed
- `.env.example`: Updated at the root to include all necessary environment variables, including `OLLAMA_MODEL` and `OLLAMA_HOST`.
- `.env`: Created at the root (based on `.env.example`) to provide local development defaults.
- `dashboard_app/config.py`: Updated the `Config` class to include `OLLAMA_MODEL` and `OLLAMA_HOST` as attributes. Improved `.env` loading logic to look for the file in both the application directory and the project root.
- `dashboard_app/app/__init__.py`: Added a debug-level log to confirm that AI-related configuration variables are successfully loaded on application startup.

## Validation Performed
- **Manual Verification**: Created a script `verify_config.py` that successfully imported the `Config` class and confirmed it correctly read the values from the root `.env` file.
- **Log Check**: Verified that the application logic includes configuration logging when running in debug mode.
- **Root .env**: Confirmed that the project root is now the primary source for environment variables, simplifying configuration for both local and Docker-based deployments.

## Known Limitations
- The `.env` file is excluded from version control (via `.gitignore`), so developers must manually create it using `.env.example`.
- If both `dashboard_app/.env` and `.env` (root) exist, variables in the application-level `.env` might override or be overridden depending on the `load_dotenv` sequence (currently root is loaded last, so it takes precedence).

## Follow-up Recommendations
- Ensure CI/CD pipelines are updated to provide these environment variables in their respective environments.
- As more AI services are added (e.g., custom model parameters), continue to centralize them in the root `.env` and `Config` class.
