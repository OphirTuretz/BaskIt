"""Tests for AI tools implementation."""
import pytest
from typing import Dict, Any
from datetime import datetime, UTC

from baskit.ai.tools import (
    add_item,
    update_item,
    increment_quantity,
    reduce_quantity,
    delete_item,
    mark_item_bought,
    create_list,
    delete_list,
    show_list,
    set_default_list,
    AddItem,
    UpdateItem,
    IncrementQuantity,
    ReduceQuantity,
    DeleteItem,
    MarkItemBought,
    CreateList,
    DeleteList,
    ShowList,
    SetDefaultList
)


@pytest.fixture
def tools_setup(tool_service):
    """Setup common test data."""
    # Create a test list
    list_result = tool_service.list_service.create_list("רשימת בדיקה")
    assert list_result.success
    list_id = list_result.data.id
    
    # Add some items
    item1 = tool_service.item_service.add_item(list_id, "חלב", 1, "ליטר")
    assert item1.success
    
    item2 = tool_service.item_service.add_item(list_id, "לחם", 2, "יחידה")
    assert item2.success
    
    return {
        "list_id": list_id,
        "list_name": "רשימת בדיקה",
        "items": [item1.data, item2.data]
    }


def assert_tool_success(result: Dict[str, Any]):
    """Helper to assert tool success."""
    assert result["status"] == "success"
    assert result["message"]
    assert "data" in result


def assert_tool_error(result: Dict[str, Any]):
    """Helper to assert tool error."""
    assert result["status"] == "error"
    assert result["message"]
    assert result.get("data") is None


def test_add_item(tool_service, tools_setup):
    """Test adding items through tool."""
    # Add new item
    result = add_item(
        tool_service,
        AddItem(
            item_name="ביצים",
            quantity=12,
            list_name=tools_setup["list_name"]
        )
    )
    assert_tool_success(result)
    assert "ביצים" in result["message"]
    assert result["data"]["item"].name == "ביצים"
    assert result["data"]["item"].quantity == 12

    # Try adding with invalid quantity
    result = add_item(
        tool_service,
        AddItem(
            item_name="חלב",
            quantity=100,  # Too high
            list_name=tools_setup["list_name"]
        )
    )
    assert_tool_error(result)
    assert "99" in result["message"]


def test_update_item(tool_service, tools_setup):
    """Test updating items through tool."""
    # Update existing item
    result = update_item(
        tool_service,
        UpdateItem(
            item_name="חלב",
            quantity=2,
            list_name=tools_setup["list_name"]
        )
    )
    assert_tool_success(result)
    assert "חלב" in result["message"]
    assert result["data"]["item"].quantity == 2

    # Update non-existent item (should create it)
    result = update_item(
        tool_service,
        UpdateItem(
            item_name="ביצים",
            quantity=12,
            list_name=tools_setup["list_name"]
        )
    )
    assert_tool_success(result)
    assert "ביצים" in result["message"]


def test_increment_quantity(tool_service, tools_setup):
    """Test incrementing quantities through tool."""
    # Increment existing item
    result = increment_quantity(
        tool_service,
        IncrementQuantity(
            item_name="חלב",
            step=2,
            list_name=tools_setup["list_name"]
        )
    )
    assert_tool_success(result)
    assert "חלב" in result["message"]
    assert result["data"]["item"].quantity == 3

    # Increment non-existent item (should create it)
    result = increment_quantity(
        tool_service,
        IncrementQuantity(
            item_name="ביצים",
            step=12,
            list_name=tools_setup["list_name"]
        )
    )
    assert_tool_success(result)
    assert "ביצים" in result["message"]
    assert result["data"]["item"].quantity == 12


def test_reduce_quantity(tool_service, tools_setup):
    """Test reducing quantities through tool."""
    # Reduce existing item
    result = reduce_quantity(
        tool_service,
        ReduceQuantity(
            item_name="לחם",
            step=1,
            list_name=tools_setup["list_name"]
        )
    )
    assert_tool_success(result)
    assert "לחם" in result["message"]
    assert result["data"]["item"].quantity == 1

    # Reduce non-existent item
    result = reduce_quantity(
        tool_service,
        ReduceQuantity(
            item_name="ביצים",
            step=1,
            list_name=tools_setup["list_name"]
        )
    )
    assert_tool_error(result)
    assert "לא מצאתי" in result["message"]


def test_delete_item(tool_service, tools_setup):
    """Test deleting items through tool."""
    # Delete existing item
    result = delete_item(
        tool_service,
        DeleteItem(
            item_name="חלב",
            list_name=tools_setup["list_name"]
        )
    )
    assert_tool_success(result)
    assert "חלב" in result["message"]

    # Try deleting again (should fail)
    result = delete_item(
        tool_service,
        DeleteItem(
            item_name="חלב",
            list_name=tools_setup["list_name"]
        )
    )
    assert_tool_error(result)
    assert "לא מצאתי" in result["message"]


def test_mark_item_bought(tool_service, tools_setup):
    """Test marking items as bought through tool."""
    # Mark item as bought
    result = mark_item_bought(
        tool_service,
        MarkItemBought(
            item_name="חלב",
            list_name=tools_setup["list_name"]
        )
    )
    assert_tool_success(result)
    assert "חלב" in result["message"]
    assert result["data"]["item"].is_bought

    # Try marking non-existent item
    result = mark_item_bought(
        tool_service,
        MarkItemBought(
            item_name="ביצים",
            list_name=tools_setup["list_name"]
        )
    )
    assert_tool_error(result)
    assert "לא מצאתי" in result["message"]


def test_create_list(tool_service):
    """Test creating lists through tool."""
    # Create new list
    result = create_list(
        tool_service,
        CreateList(list_name="רשימה חדשה")
    )
    assert_tool_success(result)
    assert "רשימה חדשה" in result["message"]

    # Try creating duplicate list
    result = create_list(
        tool_service,
        CreateList(list_name="רשימה חדשה")
    )
    assert_tool_error(result)
    assert "כבר קיימת" in result["message"]


def test_delete_list(tool_service, tools_setup):
    """Test deleting lists through tool."""
    # Delete existing list
    result = delete_list(
        tool_service,
        DeleteList(
            list_name=tools_setup["list_name"],
            hard_delete=False
        )
    )
    assert_tool_success(result)
    assert tools_setup["list_name"] in result["message"]

    # Try deleting non-existent list
    result = delete_list(
        tool_service,
        DeleteList(list_name="רשימה לא קיימת")
    )
    assert_tool_error(result)
    assert "לא מצאתי" in result["message"]


def test_show_list(tool_service, tools_setup):
    """Test showing lists through tool."""
    # Show existing list
    result = show_list(
        tool_service,
        ShowList(list_name=tools_setup["list_name"])
    )
    assert_tool_success(result)
    assert tools_setup["list_name"] in result["message"]
    assert len(result["data"]["contents"].items) == 2

    # Try showing non-existent list
    result = show_list(
        tool_service,
        ShowList(list_name="רשימה לא קיימת")
    )
    assert_tool_error(result)
    assert "לא מצאתי" in result["message"]


def test_set_default_list(tool_service, tools_setup):
    """Test setting default list through tool."""
    # Set list as default
    result = set_default_list(
        tool_service,
        SetDefaultList(list_name=tools_setup["list_name"])
    )
    assert_tool_success(result)
    assert tools_setup["list_name"] in result["message"]
    assert "ברירת מחדל" in result["message"]

    # Try setting non-existent list as default
    result = set_default_list(
        tool_service,
        SetDefaultList(list_name="רשימה לא קיימת")
    )
    assert_tool_error(result)
    assert "לא מצאתי" in result["message"] 