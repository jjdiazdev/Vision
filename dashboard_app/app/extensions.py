from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import event
from sqlalchemy.engine import Engine

db = SQLAlchemy()
migrate = Migrate()

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        print(f"[SQLite] journal_mode set to: {mode}")
    except Exception as e:
        # This might fail for non-sqlite engines if they are ever added
        pass
    finally:
        cursor.close()
