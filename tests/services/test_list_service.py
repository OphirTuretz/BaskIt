"""Tests for the list management service."""
import pytest
from datetime import datetime, UTC

from baskit.services.list_service import ListService, ListContents, ListSummary
from baskit.models import GroceryList, GroceryItem


@pytest.fixture
def list_service(session, user):
    """Create a list service instance."""
    return ListService(session, user.id)


def test_create_list(list_service):
    """Test creating a new list."""
    # Create list
    result = list_service.create_list("רשימת קניות")
    assert result.success
    assert result.data.name == "רשימת קניות"
    assert result.data.owner_id == list_service.user_id
    assert not result.data.is_deleted
    
    # Should be default list (first list)
    default_result = list_service.get_default_list()
    assert default_result.success
    assert default_result.data.id == result.data.id


def test_create_list_invalid_name(list_service):
    """Test creating a list with invalid name."""
    # Empty name
    result = list_service.create_list("")
    assert not result.success
    assert "שם לא יכול להיות ריק" in result.error
    
    # Non-Hebrew name
    result = list_service.create_list("Shopping List")
    assert not result.success
    assert "טקסט חייב להיות בעיקר בעברית" in result.error


def test_create_duplicate_list(list_service):
    """Test creating a list with duplicate name."""
    # Create first list
    result1 = list_service.create_list("רשימת קניות")
    assert result1.success
    
    # Try to create second list with same name
    result2 = list_service.create_list("רשימת קניות")
    assert not result2.success
    assert "כבר קיים" in result2.error
    assert len(result2.suggestions) > 0


def test_delete_list(list_service):
    """Test deleting a list."""
    # Create list
    create_result = list_service.create_list("רשימת קניות")
    assert create_result.success
    list_id = create_result.data.id
    
    # Soft delete
    delete_result = list_service.delete_list(list_id)
    assert delete_result.success
    assert delete_result.data.is_deleted
    assert delete_result.data.deleted_at is not None
    assert delete_result.data.deleted_by == list_service.user_id
    
    # Should not be default list anymore
    default_result = list_service.get_default_list()
    assert default_result.success
    assert default_result.data is None


def test_restore_list(list_service):
    """Test restoring a deleted list."""
    # Create and delete list
    list_result = list_service.create_list("רשימת קניות")
    assert list_result.success
    list_id = list_result.data.id
    
    delete_result = list_service.delete_list(list_id)
    assert delete_result.success
    
    # Restore list
    restore_result = list_service.restore_list(list_id)
    assert restore_result.success
    assert not restore_result.data.is_deleted
    assert restore_result.data.deleted_at is None
    assert restore_result.data.deleted_by is None


def test_restore_list_with_conflict(list_service):
    """Test restoring a list when active list exists with same name."""
    # Create first list
    list1_result = list_service.create_list("רשימת קניות")
    assert list1_result.success
    list1_id = list1_result.data.id
    
    # Create second list with different name
    list2_result = list_service.create_list("רשימת סופר")
    assert list2_result.success
    
    # Delete first list
    delete_result = list_service.delete_list(list1_id)
    assert delete_result.success
    
    # Rename second list to first list's name
    rename_result = list_service.rename_list(list2_result.data.id, "רשימת קניות")
    assert rename_result.success
    
    # Try to restore first list
    restore_result = list_service.restore_list(list1_id)
    assert not restore_result.success
    assert "קיימת רשימה פעילה" in restore_result.error
    assert len(restore_result.suggestions) > 0


def test_rename_list(list_service):
    """Test renaming a list."""
    # Create list
    list_result = list_service.create_list("רשימת קניות")
    assert list_result.success
    list_id = list_result.data.id
    
    # Rename list
    rename_result = list_service.rename_list(list_id, "רשימת סופר")
    assert rename_result.success
    assert rename_result.data.name == "רשימת סופר"
    assert rename_result.data.updated_by == list_service.user_id


def test_rename_list_invalid_name(list_service):
    """Test renaming a list with invalid name."""
    # Create list
    list_result = list_service.create_list("רשימת קניות")
    assert list_result.success
    list_id = list_result.data.id
    
    # Try to rename with empty name
    rename_result = list_service.rename_list(list_id, "")
    assert not rename_result.success
    assert "שם לא יכול להיות ריק" in rename_result.error
    
    # Try to rename with non-Hebrew name
    rename_result = list_service.rename_list(list_id, "Shopping List")
    assert not rename_result.success
    assert "טקסט חייב להיות בעיקר בעברית" in rename_result.error
    
    # Original name should not change
    list_result = list_service.get_lists()
    assert list_result.success
    assert list_result.data[0].name == "רשימת קניות"


def test_rename_list_to_existing_name(list_service):
    """Test renaming a list to an existing name."""
    # Create two lists
    list1_result = list_service.create_list("רשימת קניות")
    assert list1_result.success
    
    list2_result = list_service.create_list("רשימת סופר")
    assert list2_result.success
    
    # Try to rename second list to first list's name
    rename_result = list_service.rename_list(list2_result.data.id, "רשימת קניות")
    assert not rename_result.success
    assert "כבר קיים" in rename_result.error
    assert len(rename_result.suggestions) > 0


def test_set_default_list(list_service):
    """Test setting default list."""
    # Create two lists
    list1_result = list_service.create_list("רשימת קניות")
    assert list1_result.success
    list1_id = list1_result.data.id
    
    list2_result = list_service.create_list("רשימת סופר")
    assert list2_result.success
    list2_id = list2_result.data.id
    
    # First list should be default
    default_result = list_service.get_default_list()
    assert default_result.success
    assert default_result.data.id == list1_id
    
    # Set second list as default
    set_default_result = list_service.set_default_list(list2_id)
    assert set_default_result.success
    
    # Verify second list is now default
    default_result = list_service.get_default_list()
    assert default_result.success
    assert default_result.data.id == list2_id


def test_get_lists(list_service):
    """Test getting all lists."""
    # Create two lists
    list1_result = list_service.create_list("רשימת קניות")
    assert list1_result.success
    
    list2_result = list_service.create_list("רשימת סופר")
    assert list2_result.success
    
    # Delete second list
    delete_result = list_service.delete_list(list2_result.data.id)
    assert delete_result.success
    
    # Get active lists
    lists_result = list_service.get_lists()
    assert lists_result.success
    assert len(lists_result.data) == 1
    assert lists_result.data[0].id == list1_result.data.id
    
    # Get all lists including deleted
    all_lists_result = list_service.get_lists(include_deleted=True)
    assert all_lists_result.success
    assert len(all_lists_result.data) == 2 


def test_show_list(list_service, item_service):
    """Test showing list contents."""
    # Create list with items
    list_result = list_service.create_list("רשימת קניות")
    assert list_result.success
    list_id = list_result.data.id
    
    # Add items
    item1_result = item_service.add_item(list_id, "חלב", 1, "ליטר")
    assert item1_result.success
    
    item2_result = item_service.add_item(list_id, "לחם", 2, "יחידה")
    assert item2_result.success
    
    # Show list
    result = list_service.show_list(list_id)
    assert result.success
    assert isinstance(result.data, ListContents)
    assert result.data.id == list_id
    assert result.data.name == "רשימת קניות"
    assert len(result.data.items) == 2
    assert result.data.is_default  # First list is default


def test_show_list_with_bought_items(list_service, item_service):
    """Test showing list contents with bought items filter."""
    # Create list with items
    list_result = list_service.create_list("רשימת קניות")
    assert list_result.success
    list_id = list_result.data.id
    
    # Add items
    item1_result = item_service.add_item(list_id, "חלב", 1)
    assert item1_result.success
    item1_id = item1_result.data.id
    
    item2_result = item_service.add_item(list_id, "לחם", 2)
    assert item2_result.success
    
    # Mark first item as bought
    mark_result = item_service.mark_bought(item1_id)
    assert mark_result.success
    
    # Show list with bought items
    result = list_service.show_list(list_id, include_bought=True)
    assert result.success
    assert len(result.data.items) == 2
    
    # Show list without bought items
    result = list_service.show_list(list_id, include_bought=False)
    assert result.success
    assert len(result.data.items) == 1
    assert result.data.items[0].name == "לחם"


def test_show_default_list(list_service):
    """Test showing default list when no list_id provided."""
    # Create list
    list_result = list_service.create_list("רשימת קניות")
    assert list_result.success
    
    # Show default list
    result = list_service.show_list()
    assert result.success
    assert result.data.id == list_result.data.id
    assert result.data.is_default


def test_show_list_errors(list_service):
    """Test error cases for show_list."""
    # No default list
    result = list_service.show_list()
    assert not result.success
    assert "לא נמצאה רשימה ברירת מחדל" in result.error
    assert "צור רשימה חדשה" in result.suggestions
    
    # Non-existent list
    result = list_service.show_list(999)
    assert not result.success
    assert "רשימה לא נמצאה" in result.error
    
    # Deleted list
    list_result = list_service.create_list("רשימת קניות")
    assert list_result.success
    list_id = list_result.data.id
    
    delete_result = list_service.delete_list(list_id)
    assert delete_result.success
    
    result = list_service.show_list(list_id)
    assert not result.success
    assert "נמחקה" in result.error
    assert len(result.suggestions) > 0


def test_list_all_user_lists(list_service, item_service):
    """Test listing all user lists with summaries."""
    # Create lists with items
    list1_result = list_service.create_list("רשימת קניות")
    assert list1_result.success
    list1_id = list1_result.data.id
    
    list2_result = list_service.create_list("רשימת סופר")
    assert list2_result.success
    list2_id = list2_result.data.id
    
    # Add items to first list
    item1_result = item_service.add_item(list1_id, "חלב")
    assert item1_result.success
    item1_id = item1_result.data.id
    
    item2_result = item_service.add_item(list1_id, "לחם")
    assert item2_result.success
    
    # Mark one item as bought
    mark_result = item_service.mark_bought(item1_id)
    assert mark_result.success
    
    # Add item to second list
    item3_result = item_service.add_item(list2_id, "ביצים")
    assert item3_result.success
    
    # List all lists
    result = list_service.list_all_user_lists()
    assert result.success
    assert len(result.data) == 2
    
    # Verify first list summary
    list1 = next(l for l in result.data if l.id == list1_id)
    assert isinstance(list1, ListSummary)
    assert list1.name == "רשימת קניות"
    assert list1.total_items == 1  # One unbought item
    assert list1.bought_items == 1  # One bought item
    assert list1.is_default  # First list is default
    
    # Verify second list summary
    list2 = next(l for l in result.data if l.id == list2_id)
    assert list2.name == "רשימת סופר"
    assert list2.total_items == 1
    assert list2.bought_items == 0
    assert not list2.is_default


def test_list_all_user_lists_with_deleted(list_service):
    """Test listing all user lists including deleted ones."""
    # Create two lists
    list1_result = list_service.create_list("רשימת קניות")
    assert list1_result.success
    
    list2_result = list_service.create_list("רשימת סופר")
    assert list2_result.success
    list2_id = list2_result.data.id
    
    # Delete second list
    delete_result = list_service.delete_list(list2_id)
    assert delete_result.success
    
    # List active lists only
    result = list_service.list_all_user_lists()
    assert result.success
    assert len(result.data) == 1
    
    # List all lists including deleted
    result = list_service.list_all_user_lists(include_deleted=True)
    assert result.success
    assert len(result.data) == 2


def test_list_all_user_lists_empty(list_service):
    """Test listing lists when user has none."""
    result = list_service.list_all_user_lists()
    assert not result.success
    assert "לא נמצאו רשימות" in result.error
    assert "צור רשימה חדשה" in result.suggestions


def test_is_list_soft_deleted(list_service):
    """Test checking if a list is soft-deleted."""
    # Create list
    list_result = list_service.create_list("רשימת קניות")
    assert list_result.success
    list_id = list_result.data.id
    
    # Check active list
    result = list_service.is_list_soft_deleted(list_id)
    assert result.success
    assert not result.data
    
    # Delete list
    delete_result = list_service.delete_list(list_id)
    assert delete_result.success
    
    # Check deleted list
    result = list_service.is_list_soft_deleted(list_id)
    assert result.success
    assert result.data


def test_is_list_soft_deleted_errors(list_service):
    """Test error cases for is_list_soft_deleted."""
    # Non-existent list
    result = list_service.is_list_soft_deleted(999)
    assert not result.success
    assert "רשימה לא נמצאה" in result.error 