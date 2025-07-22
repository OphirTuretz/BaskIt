"""Integration tests for GPT and tool execution."""
import pytest
from unittest.mock import ANY, patch, AsyncMock, Mock
from openai.types.chat import ChatCompletionMessage

from baskit.ai.errors import APIError, ValidationError, ToolExecutionError, ToolExecutionResult
from baskit.services.base_service import Result
from baskit.web.app import process_smart_input
from baskit.ai.models import GPTContext
from baskit.models import GroceryList, GroceryItem
from baskit.ai.handlers import ToolExecutor
from baskit.services.item_service import ItemLocation


@pytest.mark.asyncio
async def test_gpt_handler_mock_mode(
    gpt_handler,  # Uses mock mode by default
    gpt_context,
    hebrew_inputs
):
    """Test GPT handler in mock mode."""
    text, expected = hebrew_inputs[0]  # Use first test case
    
    # Ensure mock mode is enabled
    gpt_handler.use_mock = True
    
    result = await gpt_handler.call_with_tools(text, gpt_context)
    
    assert result.success
    assert result.data['tool_calls'][0]['name'] == expected['name']
    assert result.data['tool_calls'][0]['arguments'] == expected['arguments']
    assert result.data['confidence'] == 1.0  # Mock mode always uses 1.0 confidence
    assert result.metadata['mock_mode'] is True


@pytest.mark.asyncio
async def test_gpt_handler_api_mode(
    api_gpt_handler,
    gpt_context,
    hebrew_inputs
):
    """Test GPT handler in API mode."""
    text, expected = hebrew_inputs[0]  # Use first test case
    
    # Setup mock response
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
                        'name': expected['name'],
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
    api_gpt_handler.client.chat.completions.create.return_value.choices = [mock_choice]
    
    result = await api_gpt_handler.call_with_tools(text, gpt_context)
    
    assert result.success
    assert result.data['tool_calls'][0]['name'] == expected['name']
    assert result.data['tool_calls'][0]['arguments'] == expected['arguments']
    assert result.data['confidence'] == 1.0  # Using temperature=0.0
    assert result.metadata['mock_mode'] is False


@pytest.mark.asyncio
async def test_gpt_handler_api_error(api_gpt_handler, gpt_context):
    """Test handling of API errors."""
    api_gpt_handler.client.chat.completions.create.side_effect = APIError(
        "יותר מדי בקשות, נסה שוב בעוד מספר שניות",
        suggestions=["המתן מעט ונסה שוב"]
    )
    
    result = await api_gpt_handler.call_with_tools("תוסיף חלב", gpt_context)
    
    assert not result.success
    assert "יותר מדי בקשות" in result.error
    assert len(result.suggestions) > 0


@pytest.mark.asyncio
async def test_tool_executor_add_item(tool_executor, gpt_context):
    """Test add_item tool execution."""
    tool_call = {
        'name': 'add_item',
        'arguments': {
            'item_name': 'חלב',
            'quantity': 1,
            'unit': 'יחידה'
        }
    }
    
    result = await tool_executor.execute(tool_call, gpt_context)
    
    assert result.success
    assert result.data['item']['name'] == 'חלב'
    assert result.data['item']['quantity'] == 1
    assert result.data['item']['unit'] == 'יחידה'


@pytest.mark.asyncio
async def test_tool_executor_add_item_to_list(
    tool_executor,
    gpt_context,
    mock_list_service
):
    """Test adding item to specific list."""
    # Mock the tool service to return a valid list
    tool_executor.tool_service.resolve_list.return_value = Result(
        success=True,
        data=1  # List ID
    )
    
    tool_call = {
        'name': 'add_item',
        'arguments': {
            'item_name': 'חלב',
            'quantity': 1,
            'unit': 'יחידה',
            'list_name': 'רשימה ראשית'
        }
    }
    
    result = await tool_executor.execute(tool_call, gpt_context)
    
    assert result.success
    assert result.data['item']['name'] == 'חלב'


@pytest.mark.asyncio
async def test_tool_executor_list_not_found(
    tool_executor,
    gpt_context,
    mock_list_service
):
    """Test handling of non-existent list."""
    # Mock the tool service to return a list not found error
    tool_executor.tool_service.resolve_list.return_value = Result(
        success=False,
        error="לא נמצאה רשימה בשם 'רשימה לא קיימת'",
        suggestions=["בדוק את שם הרשימה"]
    )
    
    tool_call = {
        'name': 'add_item',
        'arguments': {
            'item_name': 'חלב',
            'list_name': 'רשימה לא קיימת'
        }
    }
    
    result = await tool_executor.execute(tool_call, gpt_context)
    
    assert not result.success
    assert 'לא נמצאה' in result.error


@pytest.mark.asyncio
async def test_tool_executor_invalid_hebrew(tool_executor, gpt_context):
    """Test handling of non-Hebrew text."""
    # Mock the tool service to raise a validation error
    tool_executor.tool_service.resolve_list.side_effect = ValidationError(
        "Text must be in Hebrew",
        suggestions=["נסה לכתוב בעברית"]
    )
    
    tool_call = {
        'name': 'add_item',
        'arguments': {
            'item_name': 'milk',  # Not Hebrew
            'quantity': 1,
            'unit': 'יחידה'
        }
    }
    
    result = await tool_executor.execute(tool_call, gpt_context)
    
    assert not result.success
    assert 'hebrew' in result.error.lower() or 'עברית' in result.error.lower()


@pytest.mark.asyncio
async def test_tool_executor_mark_bought(tool_executor, gpt_context):
    """Test mark_bought tool execution."""
    # Mock the tool service to return a valid item
    default_item = GroceryItem(
        id=1,
        name="חלב",
        quantity=1,
        unit="יחידה",
        list_id=1,
        is_bought=False
    )
    default_list = GroceryList(
        id=1,
        name="רשימה ראשית",
        owner_id=1,
        items=[default_item]
    )
    tool_executor.tool_service.resolve_item.return_value = Result(
        success=True,
        data=(1, ItemLocation(
            item_id=1,
            list_id=default_list.id,
            list_name=default_list.name,
            quantity=default_item.quantity,
            unit=default_item.unit,
            is_bought=False
        )),
        error="",
        suggestions=[]
    )
    
    tool_call = {
        'name': 'mark_bought',
        'arguments': {
            'item_name': 'חלב',
            'is_bought': True
        }
    }
    
    result = await tool_executor.execute(tool_call, gpt_context)
    
    assert result.success
    assert result.data['item']['is_bought']


@pytest.mark.asyncio
async def test_tool_executor_show_list(tool_executor, gpt_context):
    """Test show_list tool execution."""
    tool_call = {
        'name': 'show_list',
        'arguments': {
            'list_id': 1,
            'include_bought': True
        }
    }
    
    result = await tool_executor.execute(tool_call, gpt_context)
    
    assert result.success
    assert 'list' in result.data
    assert len(result.data['list']['items']) > 0


@pytest.mark.asyncio
async def test_tool_executor_create_list(tool_executor, gpt_context):
    """Test create_list tool execution."""
    tool_call = {
        'name': 'create_list',
        'arguments': {
            'name': 'רשימה חדשה'
        }
    }
    
    result = await tool_executor.execute(tool_call, gpt_context)
    
    assert result.success
    assert result.data['list']['name'] == 'רשימה חדשה'


@pytest.mark.asyncio
async def test_tool_executor_unsupported_tool(tool_executor, gpt_context):
    """Test handling of unsupported tool."""
    tool_call = {
        'name': 'unsupported_tool',
        'arguments': {}
    }
    
    result = await tool_executor.execute(tool_call, gpt_context)
    
    assert not result.success
    assert 'לא נתמך' in result.error
    assert len(result.suggestions) > 0


@pytest.mark.asyncio
async def test_end_to_end_flow(
    gpt_handler,  # Uses mock mode by default
    tool_executor,
    gpt_context,
    hebrew_inputs
):
    """Test complete flow from GPT to tool execution."""
    text, expected = hebrew_inputs[0]
    
    # Ensure mock mode is enabled
    gpt_handler.use_mock = True
    
    # Get tool calls from GPT
    gpt_result = await gpt_handler.call_with_tools(text, gpt_context)
    assert gpt_result.success
    assert gpt_result.data['confidence'] == 1.0  # Mock mode always uses 1.0 confidence
    assert gpt_result.metadata['mock_mode'] is True
    
    # Execute tool calls
    tool_calls = gpt_result.data['tool_calls']
    assert len(tool_calls) == 1
    
    tool_result = await tool_executor.execute(tool_calls[0], gpt_context)
    assert tool_result.success
    assert tool_result.data['item']['name'] == 'חלב'
    assert tool_result.data['item']['quantity'] == 1
    assert tool_result.data['item']['unit'] == 'יחידה' 


@pytest.fixture
def mock_streamlit():
    """Mock Streamlit session state."""
    with patch('streamlit.session_state') as mock_state:
        mock_state.session_id = 'test_session'
        yield mock_state

@pytest.mark.asyncio
async def test_smart_input_processing_success(mocker, mock_streamlit, mock_item_service, mock_list_service):
    """Test successful processing of smart input."""
    # Arrange
    mock_gpt = mocker.Mock()
    mock_gpt.call_with_tools = AsyncMock(return_value=ToolExecutionResult(
        success=True,
        message="הוספתי טופו לרשימה",
        data={
            "tool_calls": [
                {
                    "name": "add_item",
                    "arguments": {
                        "item_name": "טופו",
                        "quantity": 1,
                        "unit": "יחידה"
                    }
                }
            ]
        }
    ))
    
    # Set up default list
    default_list = GroceryList(
        id=1,
        name="רשימת קניות",
        owner_id=1,
        items=[]
    )
    mock_list_service.get_default_list.return_value = Result(
        success=True,
        data=default_list,
        error="",
        suggestions=[]
    )
    mock_list_service.show_list.return_value = Result(
        success=True,
        data=default_list,
        error="",
        suggestions=[]
    )
    mock_list_service.get_lists.return_value = Result(
        success=True,
        data=[default_list],
        error="",
        suggestions=[]
    )
    
    # Mock the tool service to return a valid list
    mock_tool_service = Mock()
    mock_tool_service.resolve_list.return_value = Result(
        success=True,
        data=default_list.id,
        error="",
        suggestions=[]
    )
    mock_tool_service.resolve_item.return_value = Result(
        success=True,
        data=(1, ItemLocation(
            item_id=1,
            list_id=default_list.id,
            list_name=default_list.name,
            quantity=1,
            unit="יחידה",
            is_bought=False
        )),
        error="",
        suggestions=[]
    )
    
    # Create a tool executor with the mocked services
    tool_executor = ToolExecutor(
        item_service=mock_item_service,
        list_service=mock_list_service
    )
    tool_executor.tool_service = mock_tool_service
    
    # Act
    result = await process_smart_input(
        user_input="טופו",
        current_list="רשימת קניות",
        gpt_handler=mock_gpt,
        item_service=mock_item_service,
        list_service=mock_list_service,
        tool_executor=tool_executor
    )
    
    # Assert
    assert result.success
    assert "טופו" in result.message

@pytest.mark.asyncio
async def test_smart_input_processing_failure(mocker, mock_streamlit, mock_item_service, mock_list_service):
    """Test failed processing of smart input."""
    # Arrange
    mock_gpt = mocker.Mock()
    mock_gpt.call_with_tools = AsyncMock(return_value=ToolExecutionResult(
        success=False,
        message="לא הצלחתי להבין את הבקשה",
        suggestions=["נסה לכתוב בעברית בלבד"]
    ))
    
    # Act
    result = await process_smart_input(
        user_input="milk",  # Non-Hebrew input
        current_list="רשימת קניות",
        gpt_handler=mock_gpt,
        item_service=mock_item_service,
        list_service=mock_list_service
    )
    
    # Assert
    assert not result.success
    assert len(result.suggestions) > 0
    mock_gpt.call_with_tools.assert_called_once()

@pytest.mark.asyncio
async def test_smart_input_processing_error(mocker, mock_streamlit, mock_item_service, mock_list_service):
    """Test error handling in smart input processing."""
    # Arrange
    mock_gpt = mocker.Mock()
    mock_gpt.call_with_tools = AsyncMock(side_effect=Exception("Test error"))
    
    # Act
    result = await process_smart_input(
        user_input="טופו",
        current_list="רשימת קניות",
        gpt_handler=mock_gpt,
        item_service=mock_item_service,
        list_service=mock_list_service
    )
    
    # Assert
    assert not result.success
    assert "שגיאה" in result.message
    assert len(result.suggestions) > 0
    mock_gpt.call_with_tools.assert_called_once()

@pytest.mark.asyncio
async def test_smart_input_with_context(mocker, mock_streamlit, mock_item_service, mock_list_service):
    """Test smart input processing with list context."""
    # Arrange
    mock_gpt = mocker.Mock()
    mock_gpt.call_with_tools = AsyncMock(return_value=ToolExecutionResult(
        success=True,
        message="הוספתי טופו לרשימת שבת",
        data={
            "tool_calls": [
                {
                    "name": "add_item",
                    "arguments": {
                        "item_name": "טופו",
                        "quantity": 1,
                        "unit": "יחידה",
                        "list_name": "רשימת שבת"
                    }
                }
            ]
        }
    ))
    
    # Set up lists
    target_list = GroceryList(
        id=2,
        name="רשימת שבת",
        owner_id=1,
        items=[]
    )
    default_list = GroceryList(
        id=1,
        name="רשימה ראשית",
        owner_id=1,
        items=[]
    )
    mock_list_service.get_lists.return_value = Result(
        success=True,
        data=[default_list, target_list],
        error="",
        suggestions=[]
    )
    mock_list_service.show_list.return_value = Result(
        success=True,
        data=target_list,
        error="",
        suggestions=[]
    )
    mock_list_service.get_default_list.return_value = Result(
        success=True,
        data=default_list,
        error="",
        suggestions=[]
    )
    
    # Mock the tool service to return a valid list
    mock_tool_service = Mock()
    mock_tool_service.resolve_list.return_value = Result(
        success=True,
        data=target_list.id,
        error="",
        suggestions=[]
    )
    mock_tool_service.resolve_item.return_value = Result(
        success=True,
        data=(1, ItemLocation(
            item_id=1,
            list_id=target_list.id,
            list_name=target_list.name,
            quantity=1,
            unit="יחידה",
            is_bought=False
        )),
        error="",
        suggestions=[]
    )
    
    # Create a tool executor with the mocked services
    tool_executor = ToolExecutor(
        item_service=mock_item_service,
        list_service=mock_list_service
    )
    tool_executor.tool_service = mock_tool_service
    
    # Act
    result = await process_smart_input(
        user_input="טופו",
        current_list="רשימת שבת",
        gpt_handler=mock_gpt,
        item_service=mock_item_service,
        list_service=mock_list_service,
        tool_executor=tool_executor
    )
    
    # Assert
    assert result.success
    assert "טופו" in result.message
    assert "רשימת שבת" in result.message 