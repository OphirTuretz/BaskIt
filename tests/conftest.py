"""Test configuration and fixtures for BaskIt."""
import pytest
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.engine import Engine
import sqlite3

from baskit.models import Base, User, GroceryList, GroceryItem


@pytest.fixture(scope="session")
def engine():
    """Create a test database engine."""
    # Enable SQLite foreign keys
    def _fk_pragma_on_connect(dbapi_con, con_record):
        if isinstance(dbapi_con, sqlite3.Connection):
            dbapi_con.execute('PRAGMA foreign_keys=ON')

    # Create in-memory database
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={
            "detect_types": sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            "check_same_thread": False
        }
    )
    
    # Enable foreign key support
    event.listen(test_engine, 'connect', _fk_pragma_on_connect)
    
    return test_engine


@pytest.fixture(scope="session")
def tables(engine):
    """Create all database tables."""
    # Create tables
    Base.metadata.create_all(engine)
    yield
    # Drop tables in correct order to avoid foreign key issues
    inspector = inspect(engine)
    # Get all table names
    table_names = inspector.get_table_names()
    # Drop tables in reverse order (children first)
    for table in reversed(table_names):
        Base.metadata.tables[table].drop(engine)


@pytest.fixture(scope="function")
def session(engine, tables):
    """Create a new database session for a test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    
    # Create tables
    Base.metadata.create_all(connection)
    
    yield session
    
    session.close()
    # Only rollback if transaction is still active
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture
def user(session) -> User:
    """Create a test user."""
    user = User()
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def grocery_list(session, user) -> GroceryList:
    """Create a test grocery list."""
    list_ = GroceryList(
        name="רשימת קניות",
        owner_id=user.id,
        created_by=user.id,
    )
    session.add(list_)
    session.commit()
    session.refresh(list_)
    return list_


@pytest.fixture
def grocery_item(session, grocery_list) -> GroceryItem:
    """Create a test grocery item."""
    item = GroceryItem(
        name="טופו",
        normalized_name="טופו",
        quantity=1,
        unit="חבילה",
        list_id=grocery_list.id,
        created_by=grocery_list.owner_id,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return item 