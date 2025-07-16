"""Mock implementation of text-to-item parsing."""
from typing import Dict, Any
from utils.logger import get_logger

logger = get_logger(__name__)

def parse_text_to_item(text: str) -> Dict[str, Any]:
    """
    Mock function that simulates parsing Hebrew text into a grocery item.
    
    Args:
        text: Hebrew text input from the user
        
    Returns:
        Dictionary containing parsed item details
    """
    logger.info(f"Parsing text: {text}")
    
    # Mock response - in reality this would use NLP/LLM to parse the text
    mock_item = {
        "item": "מלפפונים",  # Default to cucumbers for demo
        "quantity": 1,
        "unit": "יחידה",
        "confidence": 0.95,
        "original_text": text
    }
    
    logger.debug(f"Parsed result: {mock_item}")
    return mock_item 