import pytest
import json
from unittest.mock import patch, MagicMock
from ai_parser import parse_input_to_action, ParsingError

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client responses."""
    responses = {
        "add two tomatoes": {
            "action": "add",
            "item": "tomatoes",
            "quantity": 2,
            "list_name": None
        },
        "bought milk": {
            "action": "remove",
            "item": "milk",
            "quantity": None,
            "list_name": None
        },
        "switch to party list": {
            "action": "switch_list",
            "item": None,
            "quantity": None,
            "list_name": "party"
        },
        "create birthday list": {
            "action": "create_list",
            "item": None,
            "quantity": None,
            "list_name": "birthday"
        },
        "delete work list": {
            "action": "delete_list",
            "item": None,
            "quantity": None,
            "list_name": "work"
        }
    }
    
    class MockCompletions:
        def create(self, **kwargs):
            messages = kwargs.get('messages', [])
            user_message = next((m['content'] for m in messages if m['role'] == 'user'), '')
            
            # Extract the actual input from the prompt
            if "User input:" in user_message:
                user_input = user_message.split('User input: "')[1].split('"')[0]
            else:
                user_input = user_message
                
            for key, value in responses.items():
                if key.lower() in user_input.lower():
                    mock_choice = MagicMock()
                    mock_choice.message.content = json.dumps(value)
                    return MagicMock(choices=[mock_choice])
            # If no match found, raise exception to trigger rule-based parsing
            raise Exception("Unknown test case")
    
    class MockClient:
        def __init__(self, api_key=None):
            if not api_key:
                raise ValueError("API key is required")
            self.chat = MagicMock(completions=MockCompletions())
    
    return MockClient

@pytest.fixture
def mock_env_vars():
    """Mock environment variables."""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        yield

@pytest.fixture
def mock_openai(mock_openai_client):
    """Setup OpenAI API mock."""
    with patch('openai.OpenAI', mock_openai_client):
        with patch('openai.api_key', 'test-key'):
            yield

class TestAIParser:
    """Test suite for AI parser functionality."""
    
    def test_add_item_with_quantity(self, mock_openai, mock_env_vars):
        """Test parsing 'add' command with quantity."""
        result = parse_input_to_action("Add two tomatoes")
        assert result == {
            "action": "add",
            "item": "tomatoes",
            "quantity": 2,
            "list_name": None
        }

    def test_remove_item(self, mock_openai, mock_env_vars):
        """Test parsing 'remove' command."""
        result = parse_input_to_action("I've bought milk")
        assert result == {
            "action": "remove",
            "item": "milk",
            "quantity": None,
            "list_name": None
        }

    def test_switch_list(self, mock_openai, mock_env_vars):
        """Test parsing 'switch_list' command."""
        result = parse_input_to_action("Switch to party list")
        assert result == {
            "action": "switch_list",
            "item": None,
            "quantity": None,
            "list_name": "party"
        }

    def test_create_list(self, mock_openai, mock_env_vars):
        """Test parsing 'create_list' command."""
        result = parse_input_to_action("create birthday list")
        assert result == {
            "action": "create_list",
            "item": None,
            "quantity": None,
            "list_name": "birthday"
        }

    def test_delete_list(self, mock_openai, mock_env_vars):
        """Test parsing 'delete_list' command."""
        result = parse_input_to_action("delete work list")
        assert result == {
            "action": "delete_list",
            "item": None,
            "quantity": None,
            "list_name": "work"
        }

    def test_empty_input(self):
        """Test handling of empty input."""
        with pytest.raises(ParsingError) as exc_info:
            parse_input_to_action("")
        assert "Empty input" in str(exc_info.value)

    def test_fallback_to_rule_based(self, mock_env_vars):
        """Test fallback to rule-based parsing when OpenAI fails."""
        with patch('openai.OpenAI', side_effect=Exception("API Error")):
            with patch('openai.api_key', 'test-key'):
                result = parse_input_to_action("add 3 apples")
                assert result == {
                    "action": "add",
                    "item": "apples",
                    "quantity": 3,
                    "list_name": None
                }

    def test_rule_based_without_api_key(self):
        """Test rule-based parsing when no API key is available."""
        with patch('openai.api_key', None):
            result = parse_input_to_action("buy five bananas")
            assert result == {
                "action": "add",
                "item": "bananas",
                "quantity": 5,
                "list_name": None
            }

    @pytest.mark.parametrize("input_text,expected_error", [
        ("", "Empty input"),
        ("unknown command", "Could not determine action from input")
    ])
    def test_error_cases(self, mock_openai, mock_env_vars, input_text, expected_error):
        """Test various error cases."""
        with pytest.raises(ParsingError) as exc_info:
            if input_text == "unknown command":
                # Force rule-based parsing for unknown command
                with patch('openai.api_key', None):
                    parse_input_to_action(input_text)
            else:
                parse_input_to_action(input_text)
        assert expected_error in str(exc_info.value) 