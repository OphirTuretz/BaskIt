"""Database session management for BaskIt."""
from contextlib import contextmanager
from typing import Generator, Optional
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.engine import Engine
from datetime import datetime, UTC
import sqlite3

from baskit.config.settings import get_settings

settings = get_settings()

# Enable SQLite to handle timezone-aware datetimes
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Configure SQLite connection."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# Register custom datetime handlers for SQLite
def adapt_datetime(dt: datetime) -> str:
    """Convert datetime to string for SQLite storage."""
    return dt.isoformat()

def convert_datetime(s: bytes) -> datetime:
    """Convert string from SQLite to datetime."""
    dt = datetime.fromisoformat(s.decode())
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)

# Register the adapters with SQLite
sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("timestamp", convert_datetime)

# Create engine with timezone support
engine = create_engine(
    settings.DB_URL,
    echo=settings.DB_ECHO,
    connect_args={"detect_types": sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES}
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_session() -> Session:
    """Get a new database session."""
    return SessionLocal()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class TransactionManager:
    """Manages database transactions with error handling."""
    
    def __init__(self, session: Session):
        self.session = session
    
    @contextmanager
    def transaction(self, *, auto_commit: bool = True) -> Generator[Session, None, None]:
        """
        Context manager for database transactions.
        
        Args:
            auto_commit: Whether to automatically commit on success
        
        Yields:
            Session: The database session
        
        Raises:
            Exception: Any exception that occurs during the transaction
        """
        try:
            yield self.session
            if auto_commit:
                self.session.commit()
        except Exception:
            self.session.rollback()
            raise 