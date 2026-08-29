import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from dashboard_app.app.models import db, Task, Employee, System, Project, StatusEnum

# Path to the database file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'dashboard_app', 'instance', 'app.db')
DEFAULT_DATABASE_URL = f'sqlite:///{DB_PATH}'
DATABASE_URL = os.environ.get('DATABASE_URL', DEFAULT_DATABASE_URL)

engine = create_engine(DATABASE_URL)

# Enable WAL mode for SQLite and verify
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA journal_mode")
    mode = cursor.fetchone()[0]
    print(f"[DB Client] SQLite journal_mode set to: {mode}")
    cursor.close()

SessionLocal = sessionmaker(bind=engine)

def get_session():
    return SessionLocal()
