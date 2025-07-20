"""Tests for the list management service."""
import pytest
from datetime import datetime, UTC

from baskit.services.list_service import ListService
from baskit.models import GroceryList


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