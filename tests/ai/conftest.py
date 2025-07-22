"""Test fixtures for GPT integration."""
import os
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessage

from baskit.services.item_service import ItemService
from baskit.services.list_service import ListService
from baskit.services.base_service import Result
from baskit.models import GroceryList, GroceryItem
from baskit.ai.models import GPTConfig, GPTContext
from baskit.ai.call_gpt import GPTHandler
from baskit.ai.handlers import ToolExecutor


# Set mock API key for testing
os.environ['OPENAI_API_KEY'] = 'sk-test-key'


@pytest.fixture
def mock_openai():
    """Mock OpenAI client."""
    mock = AsyncMock(spec=AsyncOpenAI)
    mock.chat.completions.create = AsyncMock()
    return mock


@pytest.fixture
def gpt_config():
    """GPT configuration for testing."""
    return GPTConfig(
        model="gpt-4",
        temperature=0.7,
        max_retries=1,
        timeout=5
    )


@pytest.fixture
def gpt_context():
    """GPT context for testing."""
    return GPTContext(
        messages=[
            {
                'role': 'system',
                'content': 'אתה עוזר קניות בעברית.'
            }
        ]
    )


@pytest.fixture
def mock_item_service():
    """Mock item service."""
    mock = Mock(spec=ItemService)
    
    # Add required attributes for ToolService
    mock.session = Mock()
    mock.user_id = 1
    
    # Create a default item
    default_item = GroceryItem(
        id=1,
        name="חלב",
        quantity=1,
        unit="יחידה",
        list_id=1,
        is_bought=False
    )
    
    # Create a default list
    default_list = GroceryList(
        id=1,
        name="רשימה ראשית",
        owner_id=1,
        items=[default_item]
    )
    
    # Setup default behaviors with proper data structures
    mock.add_item.return_value = Result(
        success=True,
        data=default_item,
        error="",
        suggestions=[]
    )
    
    mock.remove_item.return_value = Result(
        success=True,
        data=None,
        error="",
        suggestions=[]
    )
    
    mock.update_item.return_value = Result(
        success=True,
        data=GroceryItem(
            id=1,
            name="חלב",
            quantity=2,
            unit="יחידה",
            list_id=1,
            is_bought=False
        ),
        error="",
        suggestions=[]
    )
    
    mock.mark_bought.return_value = Result(
        success=True,
        data=GroceryItem(
            id=1,
            name="חלב",
            quantity=1,
            unit="יחידה",
            list_id=1,
            is_bought=True
        ),
        error="",
        suggestions=[]
    )
    
    # Setup get_item_locations with proper data structure
    mock.get_item_locations.return_value = Result(
        success=True,
        data=[(default_item, default_list)],
        error="",
        suggestions=[]
    )
    
    return mock


@pytest.fixture
def mock_list_service():
    """Mock list service."""
    mock = Mock(spec=ListService)
    
    # Create a default list
    default_list = GroceryList(
        id=1,
        name="רשימה ראשית",
        owner_id=1,
        items=[]
    )
    
    # Setup default behaviors with proper data structures
    mock.get_lists.return_value = Result(
        success=True,
        data=[default_list],
        error="",
        suggestions=[]
    )
    
    mock.get_default_list.return_value = Result(
        success=True,
        data=default_list,
        error="",
        suggestions=[]
    )
    
    mock.create_list.return_value = Result(
        success=True,
        data=GroceryList(
            id=2,
            name="רשימה חדשה",
            owner_id=1,
            items=[]
        ),
        error="",
        suggestions=[]
    )
    
    mock.show_list.return_value = Result(
        success=True,
        data=GroceryList(
            id=1,
            name="רשימה ראשית",
            owner_id=1,
            items=[
                GroceryItem(
                    id=1,
                    name="חלב",
                    quantity=1,
                    unit="יחידה",
                    list_id=1,
                    is_bought=False
                )
            ]
        ),
        error="",
        suggestions=[]
    )
    
    return mock


@pytest.fixture
def mock_tool_service():
    """Mock tool service."""
    mock = Mock()
    
    # Create a default list
    default_list = GroceryList(
        id=1,
        name="רשימה ראשית",
        owner_id=1,
        items=[]
    )
    
    # Setup default behaviors with proper data structures
    mock.resolve_list.return_value = Result(
        success=True,
        data=default_list.id,
        error="",
        suggestions=[]
    )
    
    mock.resolve_item.return_value = Result(
        success=True,
        data=(1, default_list),
        error="",
        suggestions=[]
    )
    
    return mock


@pytest.fixture
def gpt_handler(mock_openai, gpt_config):
    """GPT handler for testing."""
    handler = GPTHandler(gpt_config)
    handler.client = mock_openai
    handler.use_mock = False  # Disable mock mode for tests
    
    # Mock tool_calls attribute
    mock_tool_calls = [
        type(
            'ToolCall',
            (),
            {
                'type': 'function',
                'function': type(
                    'Function',
                    (),
                    {
                        'name': 'add_item',
                        'arguments': '{"item_name": "חלב", "quantity": 1, "unit": "יחידה"}'
                    }
                )
            }
        )
    ]
    
    # Mock message attribute
    mock_message = type(
        'Message',
        (),
        {
            'tool_calls': mock_tool_calls
        }
    )
    
    # Mock choice attribute
    mock_choice = type(
        'Choice',
        (),
        {
            'message': mock_message
        }
    )
    
    # Set up mock response
    mock_openai.chat.completions.create.return_value = type(
        'ChatCompletion',
        (),
        {
            'choices': [mock_choice]
        }
    )
    
    return handler


@pytest.fixture
def tool_executor(mock_item_service, mock_list_service, mock_tool_service):
    """Tool executor for testing."""
    executor = ToolExecutor(
        item_service=mock_item_service,
        list_service=mock_list_service
    )
    executor.tool_service = mock_tool_service  # Override the tool service
    executor.allow_duplicates = True  # Allow duplicates for testing
    return executor


@pytest.fixture
def hebrew_inputs():
    """Sample Hebrew inputs for testing."""
    return [
        (
            "תוסיף חלב",
            {
                'name': 'add_item',
                'arguments': {
                    'item_name': 'חלב',
                    'quantity': 1,
                    'unit': 'יחידה'
                }
            }
        ),
        (
            "תוריד 2 ביצים",
            {
                'name': 'update_quantity',
                'arguments': {
                    'item_name': 'ביצים',
                    'quantity': 2,
                    'unit': 'יחידה'
                }
            }
        ),
        (
            "סמן שקניתי חלב",
            {
                'name': 'mark_bought',
                'arguments': {
                    'item_name': 'חלב',
                    'is_bought': True
                }
            }
        )
    ] 