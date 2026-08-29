import os
import logging
from typing import Optional
from dotenv import load_dotenv

def setup_logging(level: int = logging.INFO):
    """Standardized logging configuration."""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("DOE-Execution")

def load_env_vars(env_path: str = ".env") -> bool:
    """Safely load environment variables from a .env file."""
    if os.path.exists(env_path):
        load_dotenv(env_path)
        return True
    return False

def check_google_credentials() -> dict:
    """
    Placeholder function for checking Google API credentials.
    In a real scenario, this would validate the JSON key or service account.
    """
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    status = {
        "exists": False,
        "valid": False,
        "path": creds_path
    }
    
    if creds_path and os.path.exists(creds_path):
        status["exists"] = True
        # Logic to validate credential content would go here
        status["valid"] = True # Placeholder
        
    return status

if __name__ == "__main__":
    logger = setup_logging()
    logger.info("Utils module initialized.")
