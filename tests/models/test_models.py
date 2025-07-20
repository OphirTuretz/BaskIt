"""Tests for BaskIt database models."""
import pytest
from datetime import datetime, UTC

from baskit.models import User, GroceryList, GroceryItem


def test_user_creation(user):
    """Test that a user can be created."""
    assert user.id is not None
    assert user.created_at is not None
    assert user.updated_at is not None
    assert user.default_list_id is None
    # Verify timestamps are timezone-aware
    assert user.created_at.tzinfo is not None
    assert user.updated_at.tzinfo is not None


def test_list_creation(grocery_list, user):
    """Test that a grocery list can be created and linked to a user."""
    assert grocery_list.id is not None
    assert grocery_list.name == "רשימת קניות"
    assert grocery_list.owner_id == user.id
    assert grocery_list.created_by == user.id
    assert not grocery_list.is_deleted
    assert grocery_list.owner == user
    assert grocery_list in user.lists
    # Verify timestamps are timezone-aware
    assert grocery_list.created_at.tzinfo is not None
    assert grocery_list.updated_at.tzinfo is not None


def test_item_creation(grocery_item, grocery_list):
    """Test that a grocery item can be created and linked to a list."""
    assert grocery_item.id is not None
    assert grocery_item.name == "טופו"
    assert grocery_item.normalized_name == "טופו"
    assert grocery_item.quantity == 1
    assert grocery_item.unit == "חבילה"
    assert not grocery_item.is_bought
    assert grocery_item.bought_at is None
    assert grocery_item.list_id == grocery_list.id
    assert grocery_item.list == grocery_list
    assert grocery_item in grocery_list.items
    # Verify timestamps are timezone-aware
    assert grocery_item.created_at.tzinfo is not None
    assert grocery_item.updated_at.tzinfo is not None


def test_list_soft_delete(session, grocery_list, user):
    """Test that a list can be soft-deleted."""
    # Soft delete the list
    grocery_list.is_deleted = True
    grocery_list.deleted_at = datetime.now(UTC)
    grocery_list.deleted_by = user.id
    session.commit()
    
    # Verify the list is soft-deleted but still exists
    assert grocery_list.is_deleted
    assert grocery_list.deleted_at is not None
    assert grocery_list.deleted_by == user.id
    # Verify timestamp is timezone-aware
    assert grocery_list.deleted_at.tzinfo is not None
    
    # Verify we can still access the list and its items
    list_from_db = session.get(GroceryList, grocery_list.id)
    assert list_from_db is not None
    assert list_from_db.is_deleted


def test_cascade_delete(session, grocery_list, grocery_item):
    """Test that deleting a list cascades to its items."""
    list_id = grocery_list.id
    item_id = grocery_item.id
    
    # Delete the list
    session.delete(grocery_list)
    session.commit()
    
    # Verify both list and item are deleted
    assert session.get(GroceryList, list_id) is None
    assert session.get(GroceryItem, item_id) is None


def test_unique_list_name_per_user(session, user):
    """Test that list names must be unique per user."""
    # Create first list
    list1 = GroceryList(
        name="רשימת קניות",
        owner_id=user.id,
        created_by=user.id
    )
    session.add(list1)
    session.commit()
    
    # Try to create second list with same name
    list2 = GroceryList(
        name="רשימת קניות",
        owner_id=user.id,
        created_by=user.id
    )
    session.add(list2)
    
    # Should raise integrity error
    with pytest.raises(Exception):
        session.commit()
    session.rollback()


def test_timezone_awareness(user, grocery_list, grocery_item):
    """Test that all datetime fields are timezone-aware."""
    # User timestamps
    assert user.created_at.tzinfo is not None
    assert user.updated_at.tzinfo is not None
    
    # List timestamps
    assert grocery_list.created_at.tzinfo is not None
    assert grocery_list.updated_at.tzinfo is not None
    
    # Item timestamps
    assert grocery_item.created_at.tzinfo is not None
    assert grocery_item.updated_at.tzinfo is not None 