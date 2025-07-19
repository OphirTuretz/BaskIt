from typing import Dict, Optional, Union, Any
import os
import json
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure OpenAI API
openai.api_key = os.getenv("OPENAI_API_KEY")

class ParsingError(Exception):
    """Custom exception for parsing errors"""
    pass

def create_prompt(user_input: str) -> str:
    """Create a structured prompt for the LLM."""
    return f"""Parse the following shopping list command into a structured format.
Expected format is a JSON with:
- action: str (add, remove, create_list, delete_list, switch_list)
- item: str or null
- quantity: int or null
- list_name: str or null

Examples:
"Add two tomatoes" → {{"action": "add", "item": "tomatoes", "quantity": 2, "list_name": null}}
"Remove milk" → {{"action": "remove", "item": "milk", "quantity": null, "list_name": null}}
"Switch to party list" → {{"action": "switch_list", "item": null, "quantity": null, "list_name": "party"}}

User input: "{user_input}"
JSON output:"""

def parse_with_openai(text: str) -> Dict[str, Any]:
    """Parse input using OpenAI's API."""
    if not openai.api_key:
        raise ParsingError("OpenAI API key not found")
        
    try:
        client = openai.OpenAI(api_key=openai.api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a shopping list command parser. Return only valid JSON."},
                {"role": "user", "content": create_prompt(text)}
            ],
            temperature=0,  # Use deterministic output
            max_tokens=100
        )
        
        content = response.choices[0].message.content
        if not content:
            raise ParsingError("Empty response from OpenAI")
            
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            # If JSON parsing fails, try eval as fallback
            result = eval(content)
            
        if not isinstance(result, dict) or 'action' not in result:
            raise ParsingError("Invalid response format from OpenAI")
            
        # Ensure all required fields are present
        result.setdefault('item', None)
        result.setdefault('quantity', None)
        result.setdefault('list_name', None)
        
        return result
    except Exception as e:
        raise ParsingError(f"OpenAI parsing failed: {str(e)}")

def rule_based_parse(text: str) -> Dict[str, Any]:
    """Fallback rule-based parsing when API is unavailable."""
    if not isinstance(text, str):
        raise ParsingError("Input must be a string")
        
    text = text.lower().strip()
    result: Dict[str, Optional[Union[str, int]]] = {
        "action": None,
        "item": None,
        "quantity": None,
        "list_name": None
    }
    
    # Basic action detection
    if "create" in text and "list" in text:
        result["action"] = "create_list"
    elif ("delete" in text or "remove" in text) and "list" in text:
        result["action"] = "delete_list"
    elif "switch" in text or "change" in text or "use" in text:
        result["action"] = "switch_list"
    elif "add" in text or "buy" in text or "get" in text:
        result["action"] = "add"
    elif "remove" in text or "bought" in text:
        result["action"] = "remove"
    else:
        raise ParsingError("Could not determine action from input")
    
    # Basic quantity detection (only for add/remove actions)
    if result["action"] in ["add", "remove"]:
        words = text.split()
        for i, word in enumerate(words):
            if word.isdigit():
                result["quantity"] = int(word)
                break
            elif word in ["one", "two", "three", "four", "five"]:
                numbers = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
                result["quantity"] = numbers[word]
                break
    
    # Extract item or list name
    if result["action"] in ["add", "remove"]:
        # Remove action words and quantities to isolate item
        for remove_word in ["add", "remove", "buy", "get", "delete", "bought"]:
            text = text.replace(remove_word, "")
        if result["quantity"]:
            text = text.replace(str(result["quantity"]), "")
            for word in ["one", "two", "three", "four", "five"]:
                text = text.replace(word, "")
        result["item"] = text.strip()
        if not result["item"]:
            raise ParsingError("Could not determine item from input")
    elif result["action"] in ["create_list", "delete_list", "switch_list"]:
        # Extract list name after "to" or "list"
        if "to" in text:
            result["list_name"] = text.split("to")[-1].strip()
        elif "list" in text:
            parts = text.split("list")
            if len(parts) > 1:
                result["list_name"] = parts[-1].strip()
            else:
                result["list_name"] = parts[0].replace("create", "").replace("delete", "").replace("switch", "").strip()
        
        if not result["list_name"]:
            raise ParsingError("Could not determine list name from input")
    
    return result

def parse_input_to_action(text: str) -> Dict[str, Any]:
    """
    Convert user input into structured shopping list actions.
    
    Args:
        text (str): Natural language input from user
        
    Returns:
        dict: Parsed action with keys:
            - action: str (add, remove, create_list, delete_list, switch_list)
            - item: str or None
            - quantity: int or None
            - list_name: str or None
            
    Raises:
        ParsingError: If parsing fails
    """
    if not text:
        raise ParsingError("Empty input")
        
    try:
        # Try OpenAI first if API key is available
        if openai.api_key:
            try:
                return parse_with_openai(text)
            except ParsingError:
                # If OpenAI parsing fails, try rule-based
                return rule_based_parse(text)
        # Fallback to rule-based parsing
        return rule_based_parse(text)
    except Exception as e:
        if isinstance(e, ParsingError):
            raise e
        raise ParsingError(f"All parsing methods failed. Error: {str(e)}") 