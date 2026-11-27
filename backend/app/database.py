import os
import uuid
import logging
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

logger = logging.getLogger(__name__)

db_url = settings.DATABASE_URL
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
default_sqlite_path = os.path.join(backend_dir, "hr_audit.db").replace("\\", "/")

if db_url.startswith("sqlite:///./") or db_url == "sqlite:///hr_audit.db":
    db_file = db_url.replace("sqlite:///./", "").replace("sqlite:///", "")
    resolved_path = os.path.join(backend_dir, db_file).replace("\\", "/")
    db_url = f"sqlite:///{resolved_path}"

connect_args = {}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False, "timeout": 30.0}

try:
    if db_url.startswith("postgresql://") and "+psycopg2" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    engine = create_engine(
        db_url,
        connect_args=connect_args,
        echo=(settings.LOG_LEVEL == "DEBUG"),
    )
    if "postgresql" in db_url:
        with engine.connect():
            pass
except Exception as e:
    logger.warning("Database connection to %s failed (%s). Falling back to SQLite at %s", db_url, e, default_sqlite_path)
    db_url = f"sqlite:///{default_sqlite_path}"
    connect_args = {"check_same_thread": False, "timeout": 30.0}
    engine = create_engine(
        db_url,
        connect_args=connect_args,
        echo=(settings.LOG_LEVEL == "DEBUG"),
    )

# Configure SQLite concurrency: WAL mode once at startup, busy_timeout (30s) and synchronous NORMAL on each connection
if db_url.startswith("sqlite") and ":memory:" not in db_url:
    try:
        import sqlite3
        raw_db_file = db_url.replace("sqlite:///", "")
        _init_con = sqlite3.connect(raw_db_file, timeout=5)
        _init_con.execute("PRAGMA journal_mode=WAL")
        _init_con.close()
    except Exception as _e:
        logger.debug("Failed to set WAL mode on startup: %s", _e)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if "sqlite" in db_url:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
