"""Database connection layer: engine, session factory, Base, get_db() and init_db()."""
import re

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

DATABASE_URL = settings.sqlalchemy_url
IS_SQLITE = DATABASE_URL.startswith("sqlite")
SCHEMA = settings.database_schema

connect_args = {"check_same_thread": False} if IS_SQLITE else {}
if SCHEMA and not IS_SQLITE:
    if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", SCHEMA):
        raise ValueError("DATABASE_SCHEMA must be lowercase letters, digits or underscores")
    # Every connection looks in this schema first, so all of this app's tables live there.
    # That lets several apps share one PostgreSQL database without their tables mixing.
    connect_args["options"] = f"-csearch_path={SCHEMA}"

# pool_pre_ping drops dead connections (free-tier Postgres closes idle ones).
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)

if IS_SQLITE:
    # SQLite ignores foreign keys unless asked, so ON DELETE CASCADE would silently do nothing.
    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

SessionLocal = sessionmaker(autoflush=False, autocommit=False, bind=engine)
Base = declarative_base()


def get_db():
    """Give a route a session, and always close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create the schema (if configured) and any missing tables."""
    if SCHEMA and not IS_SQLITE:
        with engine.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"'))
    Base.metadata.create_all(bind=engine)
