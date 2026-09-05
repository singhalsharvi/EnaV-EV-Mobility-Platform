"""
Unified services database module that re-exports the central application database engine.
Ensures single-source-of-truth metadata, shared connection pooling, and identical table definitions.
"""

from app.database import engine, SessionLocal, Base, get_db

__all__ = ["engine", "SessionLocal", "Base", "get_db"]

