"""Integration tests for GPT and tool execution."""
import pytest
from unittest.mock import ANY, patch, AsyncMock
from openai.types.chat import ChatCompletionMessage

from baskit.ai.errors import APIError, ValidationError, ToolExecutionError, ToolExecutionResult
from baskit.services.base_service import Result
from baskit.web.app import process_smart_input
from baskit.ai.models import GPTContext


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
                        'arguments': '{"name": "חלב", "quantity": 1, "unit": "יחידה"}'
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
            'name': 'חלב',
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
    tool_call = {
        'name': 'add_item',
        'arguments': {
            'name': 'חלב',
            'quantity': 1,
            'unit': 'יחידה',
            'list_name': 'רשימה ראשית'
        }
    }
    
    result = await tool_executor.execute(tool_call, gpt_context)
    
    assert result.success
    assert result.data['item']['name'] == 'חלב'
    assert mock_list_service.get_lists.called


@pytest.mark.asyncio
async def test_tool_executor_list_not_found(
    tool_executor,
    gpt_context,
    mock_list_service
):
    """Test handling of non-existent list."""
    mock_list_service.get_lists.return_value = Result.ok([])
    
    tool_call = {
        'name': 'add_item',
        'arguments': {
            'name': 'חלב',
            'list_name': 'רשימה לא קיימת'
        }
    }
    
    result = await tool_executor.execute(tool_call, gpt_context)
    
    assert not result.success
    assert 'לא נמצאה' in result.error
    assert len(result.suggestions) > 0


@pytest.mark.asyncio
async def test_tool_executor_invalid_hebrew(tool_executor, gpt_context):
    """Test handling of non-Hebrew text."""
    tool_call = {
        'name': 'add_item',
        'arguments': {
            'name': 'milk',  # Not Hebrew
            'quantity': 1
        }
    }
    
    result = await tool_executor.execute(tool_call, gpt_context)
    
    assert not result.success
    assert 'עברית' in result.error.lower()


@pytest.mark.asyncio
async def test_tool_executor_mark_bought(tool_executor, gpt_context):
    """Test mark_bought tool execution."""
    tool_call = {
        'name': 'mark_bought',
        'arguments': {
            'item_id': 1,
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
async def test_smart_input_processing_success(mocker, mock_streamlit):
    """Test successful processing of smart input."""
    # Arrange
    mock_gpt = mocker.Mock()
    mock_gpt.call_with_tools = AsyncMock(return_value=ToolExecutionResult(
        success=True,
        message="הוספתי טופו לרשימה",
        data={"item": {"name": "טופו", "quantity": 1}}
    ))
    
    # Act
    result = await process_smart_input(
        user_input="טופו",
        current_list="רשימת קניות",
        gpt_handler=mock_gpt
    )
    
    # Assert
    assert result.success
    assert "טופו" in result.message
    mock_gpt.call_with_tools.assert_called_once()

@pytest.mark.asyncio
async def test_smart_input_processing_failure(mocker, mock_streamlit):
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
        gpt_handler=mock_gpt
    )
    
    # Assert
    assert not result.success
    assert len(result.suggestions) > 0
    mock_gpt.call_with_tools.assert_called_once()

@pytest.mark.asyncio
async def test_smart_input_processing_error(mocker, mock_streamlit):
    """Test error handling in smart input processing."""
    # Arrange
    mock_gpt = mocker.Mock()
    mock_gpt.call_with_tools = AsyncMock(side_effect=Exception("Test error"))
    
    # Act
    result = await process_smart_input(
        user_input="טופו",
        current_list="רשימת קניות",
        gpt_handler=mock_gpt
    )
    
    # Assert
    assert not result.success
    assert "שגיאה" in result.message
    assert len(result.suggestions) > 0
    mock_gpt.call_with_tools.assert_called_once()

@pytest.mark.asyncio
async def test_smart_input_with_context(mocker, mock_streamlit):
    """Test smart input processing with list context."""
    # Arrange
    mock_gpt = mocker.Mock()
    mock_gpt.call_with_tools = AsyncMock(return_value=ToolExecutionResult(
        success=True,
        message="הוספתי טופו לרשימת שבת",
        data={"item": {"name": "טופו", "quantity": 1}}
    ))
    
    # Act
    result = await process_smart_input(
        user_input="טופו",
        current_list="רשימת שבת",
        gpt_handler=mock_gpt
    )
    
    # Assert
    assert result.success
    assert "רשימת שבת" in result.message
    mock_gpt.call_with_tools.assert_called_once()
    # Verify context was passed
    context = mock_gpt.call_with_tools.call_args[0][1]
    assert context.current_list == "רשימת שבת" 