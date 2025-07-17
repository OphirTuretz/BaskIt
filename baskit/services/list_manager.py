"""In-memory grocery list management service."""
from typing import Dict, List, Any
from baskit.utils.logger import get_logger

logger = get_logger(__name__)

# In-memory storage
_grocery_list: List[Dict[str, Any]] = []

def add_item(item: Dict[str, Any]) -> bool:
    """
    Add an item to the grocery list.
    
    Args:
        item: Dictionary containing item details
        
    Returns:
        bool: True if successful
    """
    logger.info(f"Adding item to list: {item}")
    _grocery_list.append(item)
    return True

def remove_item(item_index: int) -> bool:
    """
    Remove an item from the grocery list by index.
    
    Args:
        item_index: Index of the item to remove
        
    Returns:
        bool: True if successful, False if index invalid
    """
    logger.info(f"Removing item at index: {item_index}")
    
    if 0 <= item_index < len(_grocery_list):
        del _grocery_list[item_index]
        return True
    
    logger.warning(f"Invalid index: {item_index}")
    return False

def get_list() -> List[Dict[str, Any]]:
    """
    Get the current grocery list.
    
    Returns:
        List of item dictionaries
    """
    logger.debug(f"Returning list with {len(_grocery_list)} items")
    return _grocery_list.copy()  # Return copy to prevent external modifications 