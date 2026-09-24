import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
# Try loading from dashboard_app/ and also the project root
load_dotenv(os.path.join(basedir, '.env'))
load_dotenv(os.path.join(os.path.dirname(basedir), '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Ollama Configuration
    OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL') or 'llama3.1'
    OLLAMA_HOST = os.environ.get('OLLAMA_HOST') or 'http://localhost:11434'

    # Picovoice Configuration
    PICOVOICE_ACCESS_KEY = os.environ.get('PICOVOICE_ACCESS_KEY')

    # Display timezone (IANA name, e.g. "America/Caracas"). Storage stays naive UTC — this
    # only affects rendering, plus the local-calendar-day boundary that decides when a
    # Repeat_* Task resets. See docs/adr/0002-store-utc-display-local.md. An invalid value
    # degrades to UTC with an error logged at startup; it never prevents boot.
    DISPLAY_TIMEZONE = os.environ.get('DISPLAY_TIMEZONE') or 'UTC'

    # Admin password gate (see docs/architecture/02-admin-password-gate.md) — a Werkzeug
    # password hash, not a plaintext password. No fallback: unset means every login attempt fails.
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
