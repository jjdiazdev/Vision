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

    # Admin password gate (see docs/architecture/02-admin-password-gate.md) — a Werkzeug
    # password hash, not a plaintext password. No fallback: unset means every login attempt fails.
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
