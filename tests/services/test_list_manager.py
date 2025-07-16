"""Tests for the list manager service."""
from services.list_manager import add_item, remove_item, get_list

def test_add_and_get_item():
    """Test adding an item and retrieving the list."""
    # Clear the list (since it's in-memory)
    while len(get_list()) > 0:
        remove_item(0)
    
    test_item = {
        "item": "test item",
        "quantity": 1,
        "unit": "unit",
        "confidence": 0.9,
        "original_text": "test"
    }
    
    # Add item
    assert add_item(test_item) is True
    
    # Get list and verify
    current_list = get_list()
    assert len(current_list) == 1
    assert current_list[0] == test_item

def test_remove_item():
    """Test removing items from the list."""
    # Clear the list
    while len(get_list()) > 0:
        remove_item(0)
    
    # Add two items
    item1 = {"item": "item1", "quantity": 1, "unit": "unit", "confidence": 0.9, "original_text": "test1"}
    item2 = {"item": "item2", "quantity": 1, "unit": "unit", "confidence": 0.9, "original_text": "test2"}
    
    add_item(item1)
    add_item(item2)
    
    # Remove first item
    assert remove_item(0) is True
    current_list = get_list()
    assert len(current_list) == 1
    assert current_list[0] == item2
    
    # Try to remove invalid index
    assert remove_item(99) is False 