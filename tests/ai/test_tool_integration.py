"""Integration tests for AI tools."""
import pytest
from typing import Dict, Any

from baskit.ai.tools import (
    add_item,
    update_item,
    show_list,
    create_list,
    delete_list,
    mark_item_bought,
    AddItem,
    UpdateItem,
    ShowList,
    CreateList,
    DeleteList,
    MarkItemBought
)


def test_add_and_update_flow(tool_service):
    """Test complete flow of adding and updating items."""
    # First create a list
    result = create_list(
        tool_service,
        CreateList(list_name="רשימת קניות")
    )
    assert result["status"] == "success"
    list_name = result["data"]["list"].name

    # Add some items
    items = [
        ("חלב", 1, "ליטר"),
        ("לחם", 2, "יחידה"),
        ("ביצים", 12, "יחידה")
    ]
    
    for item_name, quantity, unit in items:
        result = add_item(
            tool_service,
            AddItem(
                item_name=item_name,
                quantity=quantity,
                list_name=list_name,
                unit=unit
            )
        )
        assert result["status"] == "success"
        assert result["data"]["item"].name == item_name
        assert result["data"]["item"].quantity == quantity
        assert result["data"]["item"].unit == unit

    # Show list to verify
    result = show_list(
        tool_service,
        ShowList(list_name=list_name)
    )
    assert result["status"] == "success"
    assert len(result["data"]["contents"].items) == 3

    # Update quantities
    updates = [
        ("חלב", 2),
        ("לחם", 3),
        ("ביצים", 24)
    ]
    
    for item_name, new_quantity in updates:
        result = update_item(
            tool_service,
            UpdateItem(
                item_name=item_name,
                quantity=new_quantity,
                list_name=list_name
            )
        )
        assert result["status"] == "success"
        assert result["data"]["item"].quantity == new_quantity

    # Verify final state
    result = show_list(
        tool_service,
        ShowList(list_name=list_name)
    )
    assert result["status"] == "success"
    contents = result["data"]["contents"]
    
    for item in contents.items:
        expected_quantity = next(
            q for name, q in updates if name == item.name
        )
        assert item.quantity == expected_quantity


def test_error_handling_flow(tool_service):
    """Test error handling in a complete flow."""
    # Try operations on non-existent list
    result = add_item(
        tool_service,
        AddItem(
            item_name="חלב",
            quantity=1,
            list_name="רשימה לא קיימת"
        )
    )
    assert result["status"] == "error"
    assert "לא מצאתי" in result["message"]

    # Create list and try invalid operations
    result = create_list(
        tool_service,
        CreateList(list_name="רשימת קניות")
    )
    assert result["status"] == "success"
    list_name = result["data"]["list"].name

    # Try invalid quantity
    result = add_item(
        tool_service,
        AddItem(
            item_name="חלב",
            quantity=100,  # Too high
            list_name=list_name
        )
    )
    assert result["status"] == "error"
    assert "99" in result["message"]

    # Try invalid item name
    result = add_item(
        tool_service,
        AddItem(
            item_name="milk",  # Not Hebrew
            quantity=1,
            list_name=list_name
        )
    )
    assert result["status"] == "error"
    assert "עברית" in result["message"]

    # Add valid item then try invalid update
    result = add_item(
        tool_service,
        AddItem(
            item_name="חלב",
            quantity=1,
            list_name=list_name
        )
    )
    assert result["status"] == "success"

    result = update_item(
        tool_service,
        UpdateItem(
            item_name="חלב",
            quantity=0,  # Invalid
            list_name=list_name
        )
    )
    assert result["status"] == "error"
    assert "חיובית" in result["message"]


def test_list_management_flow(tool_service):
    """Test complete list management flow."""
    # Create multiple lists
    lists = ["רשימת שבת", "רשימת חול", "רשימת חגים"]
    for list_name in lists:
        result = create_list(
            tool_service,
            CreateList(list_name=list_name)
        )
        assert result["status"] == "success"
    
    # Add items to each list
    for list_name in lists:
        result = add_item(
            tool_service,
            AddItem(
                item_name="חלב",
                quantity=1,
                list_name=list_name
            )
        )
        assert result["status"] == "success"
    
    # Try to update without specifying list (should fail with multiple locations)
    result = update_item(
        tool_service,
        UpdateItem(
            item_name="חלב",
            quantity=2
        )
    )
    assert result["status"] == "error"
    assert "מספר רשימות" in result["message"]
    assert len(result.get("suggestions", [])) == len(lists)
    
    # Update with specific list
    result = update_item(
        tool_service,
        UpdateItem(
            item_name="חלב",
            quantity=2,
            list_name=lists[0]
        )
    )
    assert result["status"] == "success"
    
    # Mark item as bought in one list
    result = mark_item_bought(
        tool_service,
        MarkItemBought(
            item_name="חלב",
            list_name=lists[0]
        )
    )
    assert result["status"] == "success"
    
    # Delete a list
    result = delete_list(
        tool_service,
        DeleteList(list_name=lists[-1])
    )
    assert result["status"] == "success"
    
    # Verify final state
    for list_name in lists[:-1]:  # Skip deleted list
        result = show_list(
            tool_service,
            ShowList(list_name=list_name)
        )
        assert result["status"] == "success"
        contents = result["data"]["contents"]
        assert len(contents.items) == 1
        assert contents.items[0].name == "חלב"
        if list_name == lists[0]:
            assert contents.items[0].quantity == 2
            assert contents.items[0].is_bought
        else:
            assert contents.items[0].quantity == 1
            assert not contents.items[0].is_bought 