"""Test configuration and fixtures for BaskIt."""
import pytest
from unittest.mock import Mock, AsyncMock
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.engine import Engine
import sqlite3

from baskit.models import Base, User, GroceryList, GroceryItem
from baskit.services.list_service import ListService
from baskit.services.item_service import ItemService
from baskit.ai.call_gpt import GPTConfig, GPTContext, GPTHandler
from baskit.ai.handlers import ToolExecutor
from baskit.ai.tool_service import ToolService


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
def list_service(session, user):
    """Create a list service instance."""
    return ListService(session, user.id)


@pytest.fixture
def item_service(session, user):
    """Create an item service instance."""
    return ItemService(session, user.id)


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

@pytest.fixture
def mock_openai():
    """Create a mock OpenAI client."""
    mock = Mock()
    mock.chat.completions.create = AsyncMock()
    return mock

@pytest.fixture
def mock_gpt_config():
    """Create a test GPT configuration for mock mode."""
    return GPTConfig(
        model="mock",
        temperature=0.0,  # Not used in mock mode
        max_retries=1,    # Not used in mock mode
        timeout=1         # Not used in mock mode
    )

@pytest.fixture
def api_gpt_config():
    """Create a test GPT configuration for API mode."""
    return GPTConfig(
        model="gpt-4",
        temperature=0.0,  # Use zero temperature for deterministic results
        max_retries=3,
        timeout=10
    )

@pytest.fixture
def gpt_context():
    """Create a test GPT context."""
    return GPTContext(
        messages=[{
            'role': 'system',
            'content': 'אתה עוזר קניות בעברית.'
        }],
        current_list=None,
        last_item=None
    )

@pytest.fixture
def gpt_handler(mock_openai, mock_gpt_config):
    """Create a test GPT handler in mock mode by default."""
    handler = GPTHandler(mock_gpt_config)
    handler.client = mock_openai
    handler.use_mock = True  # Default to mock mode for safety
    return handler

@pytest.fixture
def api_gpt_handler(mock_openai, api_gpt_config):
    """Create a test GPT handler in API mode."""
    handler = GPTHandler(api_gpt_config)
    handler.client = mock_openai
    handler.use_mock = False  # Explicitly use API mode
    return handler

@pytest.fixture
def tool_executor(mock_item_service, mock_list_service):
    """Create a test tool executor."""
    return ToolExecutor(
        item_service=mock_item_service,
        list_service=mock_list_service
    )

@pytest.fixture
def mock_item_service():
    """Create a mock item service."""
    mock = Mock()
    mock.add_item = AsyncMock(return_value=Mock(success=True, data={'item': {
        'id': 1,
        'name': 'חלב',
        'quantity': 1,
        'unit': 'יחידה',
        'is_bought': False
    }}))
    mock.update_item = AsyncMock(return_value=Mock(success=True))
    mock.mark_bought = AsyncMock(return_value=Mock(success=True))
    mock.get_item_locations = AsyncMock(return_value=Mock(success=True))
    return mock

@pytest.fixture
def mock_list_service():
    """Create a mock list service."""
    mock = Mock()
    mock.create_list = AsyncMock(return_value=Mock(success=True))
    mock.delete_list = AsyncMock(return_value=Mock(success=True))
    mock.show_list = AsyncMock(return_value=Mock(success=True, data={
        'list': {
            'id': 1,
            'name': 'רשימת קניות',
            'items': [{
                'id': 1,
                'name': 'חלב',
                'quantity': 1,
                'unit': 'יחידה',
                'is_bought': False
            }]
        }
    }))
    mock.get_lists = AsyncMock(return_value=Mock(success=True, data=[{
        'id': 1,
        'name': 'רשימת קניות'
    }]))
    return mock

@pytest.fixture
def tool_service(session, user):
    """Create a tool service instance."""
    return ToolService(session, user.id)

@pytest.fixture
def hebrew_inputs():
    """Create test Hebrew inputs and expected outputs."""
    return [
        (
            'תוסיף חלב',
            {
                'name': 'add_item',
                'arguments': {
                    'name': 'חלב',
                    'quantity': 1,
                    'unit': 'יחידה'
                }
            }
        ),
        (
            'תוריד 2 ביצים',
            {
                'name': 'update_quantity',
                'arguments': {
                    'name': 'ביצים',
                    'quantity': 2,
                    'operation': 'reduce'
                }
            }
        ),
        (
            'סמן שקניתי חלב',
            {
                'name': 'mark_bought',
                'arguments': {
                    'name': 'חלב',
                    'is_bought': True
                }
            }
        )
    ] 