import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/enav_db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def _create_database_engine():
    global DATABASE_URL
    connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    try:
        eng = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            **(connect_args and {"connect_args": connect_args})
        )
        with eng.connect() as conn:
            pass
        return eng
    except Exception as exc:
        fallback_url = "sqlite:///./enav_fallback.db"
        logger.warning(
            f"Primary database connection to '{DATABASE_URL}' failed ({exc}). "
            f"Falling back to local SQLite database at '{fallback_url}'."
        )
        DATABASE_URL = fallback_url
        return create_engine(fallback_url, connect_args={"check_same_thread": False})

engine = _create_database_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()