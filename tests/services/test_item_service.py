"""Tests for the item management service."""
import pytest
from datetime import datetime, UTC

from baskit.services.item_service import ItemService, ItemLocation
from baskit.models import GroceryItem


@pytest.fixture
def item_service(session, user):
    """Create an item service instance."""
    return ItemService(session, user.id)


def test_add_item(list_service, item_service):
    """Test adding an item to a list."""
    # Create list
    list_result = list_service.create_list("רשימת קניות")
    assert list_result.success
    list_id = list_result.data.id
    
    # Add item
    result = item_service.add_item(list_id, "חלב", 2, "ליטר")
    assert result.success
    assert result.data.name == "חלב"
    assert result.data.quantity == 2
    assert result.data.unit == "ליטר"
    assert result.data.list_id == list_id
    assert result.data.created_by == item_service.user_id
    assert not result.data.is_bought


def test_add_item_invalid_name(list_service, item_service):
    """Test adding an item with invalid name."""
    # Create list
    list_result = list_service.create_list("רשימת קניות")
    assert list_result.success
    list_id = list_result.data.id
    
    # Empty name
    result = item_service.add_item(list_id, "")
    assert not result.success
    assert "טקסט לא יכול להיות ריק" in result.error
    
    # Non-Hebrew name
    result = item_service.add_item(list_id, "Milk")
    assert not result.success
    assert "טקסט חייב להיות בעיקר בעברית" in result.error


def test_add_item_invalid_quantity(list_service, item_service):
    """Test adding an item with invalid quantity."""
    # Create list
    list_result = list_service.create_list("רשימת קניות")
    assert list_result.success
    list_id = list_result.data.id
    
    # Negative quantity
    result = item_service.add_item(list_id, "חלב", -1)
    assert not result.success
    assert "חיובית" in result.error
    
    # Zero quantity
    result = item_service.add_item(list_id, "חלב", 0)
    assert not result.success
    assert "חיובית" in result.error
    
    # Too large quantity
    result = item_service.add_item(list_id, "חלב", 100)
    assert not result.success
    assert "99" in result.error


def test_add_item_to_nonexistent_list(item_service):
    """Test adding an item to a non-existent list."""
    result = item_service.add_item(999, "חלב")
    assert not result.success
    assert "רשימה לא נמצאה" in result.error


def test_add_item_to_deleted_list(list_service, item_service):
    """Test adding an item to a deleted list."""
    # Create and delete list
    list_result = list_service.create_list("רשימת קניות")
    assert list_result.success
    list_id = list_result.data.id
    
    delete_result = list_service.delete_list(list_id)
    assert delete_result.success
    
    # Try to add item
    result = item_service.add_item(list_id, "חלב")
    assert not result.success
    assert "לא ניתן להוסיף פריטים לרשימה מחוקה" in result.error


def test_mark_bought(list_service, item_service):
    """Test marking an item as bought."""
    # Create list and add item
    list_result = list_service.create_list("רשימת קניות")
    assert list_result.success
    list_id = list_result.data.id
    
    add_result = item_service.add_item(list_id, "חלב")
    assert add_result.success
    item_id = add_result.data.id
    
    # Mark as bought
    result = item_service.mark_bought(item_id)
    assert result.success
    assert result.data.is_bought
    assert result.data.bought_at is not None
    assert result.data.updated_by == item_service.user_id
    
    # Mark as unbought
    result = item_service.mark_bought(item_id, False)
    assert result.success
    assert not result.data.is_bought
    assert result.data.bought_at is None


def test_mark_bought_nonexistent_item(item_service):
    """Test marking a non-existent item as bought."""
    result = item_service.mark_bought(999)
    assert not result.success
    assert "פריט לא נמצא" in result.error


def test_mark_bought_in_deleted_list(list_service, item_service):
    """Test marking an item as bought in a deleted list."""
    # Create list and add item
    list_result = list_service.create_list("רשימת קניות")
    assert list_result.success
    list_id = list_result.data.id
    
    add_result = item_service.add_item(list_id, "חלב")
    assert add_result.success
    item_id = add_result.data.id
    
    # Delete list
    delete_result = list_service.delete_list(list_id)
    assert delete_result.success
    
    # Try to mark item as bought
    result = item_service.mark_bought(item_id)
    assert not result.success
    assert "לא ניתן לעדכן פריטים ברשימה מחוקה" in result.error


def test_remove_item(list_service, item_service):
    """Test removing an item."""
    # Create list and add item
    list_result = list_service.create_list("רשימת קניות")
    assert list_result.success
    list_id = list_result.data.id
    
    add_result = item_service.add_item(list_id, "חלב")
    assert add_result.success
    item_id = add_result.data.id
    
    # Remove item
    result = item_service.remove_item(item_id)
    assert result.success
    
    # Verify item is gone
    with item_service.transaction.transaction() as session:
        item = session.get(GroceryItem, item_id)
        assert item is None


def test_remove_nonexistent_item(item_service):
    """Test removing a non-existent item."""
    result = item_service.remove_item(999)
    assert not result.success
    assert "פריט לא נמצא" in result.error


def test_remove_item_from_deleted_list(list_service, item_service):
    """Test removing an item from a deleted list."""
    # Create list and add item
    list_result = list_service.create_list("רשימת קניות")
    assert list_result.success
    list_id = list_result.data.id
    
    add_result = item_service.add_item(list_id, "חלב")
    assert add_result.success
    item_id = add_result.data.id
    
    # Delete list
    delete_result = list_service.delete_list(list_id)
    assert delete_result.success
    
    # Try to remove item
    result = item_service.remove_item(item_id)
    assert not result.success
    assert "לא ניתן למחוק פריטים מרשימה מחוקה" in result.error 


def test_update_item(list_service, item_service):
    """Test updating an item's quantity and unit."""
    # Create list and add item
    list_result = list_service.create_list("רשימת קניות")
    assert list_result.success
    list_id = list_result.data.id
    
    add_result = item_service.add_item(list_id, "חלב", 1, "ליטר")
    assert add_result.success
    item_id = add_result.data.id
    
    # Update quantity only
    result = item_service.update_item(item_id, quantity=2)
    assert result.success
    assert result.data.quantity == 2
    assert result.data.unit == "ליטר"
    
    # Update unit only
    result = item_service.update_item(item_id, unit="קרטון")
    assert result.success
    assert result.data.quantity == 2
    assert result.data.unit == "קרטון"
    
    # Update both
    result = item_service.update_item(item_id, quantity=3, unit="בקבוק")
    assert result.success
    assert result.data.quantity == 3
    assert result.data.unit == "בקבוק"


def test_update_item_invalid_quantity(list_service, item_service):
    """Test updating an item with invalid quantity."""
    # Create list and add item
    list_result = list_service.create_list("רשימת קניות")
    assert list_result.success
    list_id = list_result.data.id
    
    add_result = item_service.add_item(list_id, "חלב")
    assert add_result.success
    item_id = add_result.data.id
    
    # Negative quantity
    result = item_service.update_item(item_id, quantity=-1)
    assert not result.success
    assert "חיובית" in result.error
    
    # Zero quantity
    result = item_service.update_item(item_id, quantity=0)
    assert not result.success
    assert "חיובית" in result.error
    
    # Too large quantity
    result = item_service.update_item(item_id, quantity=100)
    assert not result.success
    assert "99" in result.error


def test_increment_quantity(list_service, item_service):
    """Test incrementing an item's quantity."""
    # Create list and add item
    list_result = list_service.create_list("רשימת קניות")
    assert list_result.success
    list_id = list_result.data.id
    
    add_result = item_service.add_item(list_id, "חלב", 1)
    assert add_result.success
    item_id = add_result.data.id
    
    # Increment by default (1)
    result = item_service.increment_quantity(item_id)
    assert result.success
    assert result.data.quantity == 2
    
    # Increment by specific amount
    result = item_service.increment_quantity(item_id, step=3)
    assert result.success
    assert result.data.quantity == 5


def test_increment_quantity_exceeds_max(list_service, item_service):
    """Test incrementing quantity beyond maximum."""
    # Create list and add item
    list_result = list_service.create_list("רשימת קניות")
    assert list_result.success
    list_id = list_result.data.id
    
    add_result = item_service.add_item(list_id, "חלב", 98)
    assert add_result.success
    item_id = add_result.data.id
    
    # Try to increment beyond max
    result = item_service.increment_quantity(item_id, step=2)
    assert not result.success
    assert "99" in result.error


def test_reduce_quantity(list_service, item_service):
    """Test reducing an item's quantity."""
    # Create list and add item
    list_result = list_service.create_list("רשימת קניות")
    assert list_result.success
    list_id = list_result.data.id
    
    add_result = item_service.add_item(list_id, "חלב", 5)
    assert add_result.success
    item_id = add_result.data.id
    
    # Reduce by default (1)
    result = item_service.reduce_quantity(item_id)
    assert result.success
    assert result.data.quantity == 4
    
    # Reduce by specific amount
    result = item_service.reduce_quantity(item_id, step=2)
    assert result.success
    assert result.data.quantity == 2


def test_reduce_quantity_to_zero(list_service, item_service):
    """Test reducing quantity to zero removes the item."""
    # Create list and add item
    list_result = list_service.create_list("רשימת קניות")
    assert list_result.success
    list_id = list_result.data.id
    
    add_result = item_service.add_item(list_id, "חלב", 2)
    assert add_result.success
    item_id = add_result.data.id
    
    # Reduce to zero
    result = item_service.reduce_quantity(item_id, step=2)
    assert result.success
    assert "הוסר" in result.message
    
    # Verify item is gone
    with item_service.transaction.transaction() as session:
        item = session.get(GroceryItem, item_id)
        assert item is None


def test_get_item_locations(list_service, item_service):
    """Test finding item locations across lists."""
    # Create two lists
    list1_result = list_service.create_list("רשימת קניות 1")
    assert list1_result.success
    list1_id = list1_result.data.id
    
    list2_result = list_service.create_list("רשימת קניות 2")
    assert list2_result.success
    list2_id = list2_result.data.id
    
    # Add same item to both lists
    item1_result = item_service.add_item(list1_id, "חלב", 1, "ליטר")
    assert item1_result.success
    
    item2_result = item_service.add_item(list2_id, "חלב", 2, "קרטון")
    assert item2_result.success
    
    # Find locations
    result = item_service.get_item_locations("חלב")
    assert result.success
    assert len(result.data) == 2
    
    # Verify locations
    locations = sorted(result.data, key=lambda x: x.list_id)
    assert locations[0].list_id == list1_id
    assert locations[0].quantity == 1
    assert locations[0].unit == "ליטר"
    
    assert locations[1].list_id == list2_id
    assert locations[1].quantity == 2
    assert locations[1].unit == "קרטון"


def test_get_item_locations_with_bought(list_service, item_service):
    """Test finding item locations including bought items."""
    # Create list and add items
    list_result = list_service.create_list("רשימת קניות")
    assert list_result.success
    list_id = list_result.data.id
    
    item1_result = item_service.add_item(list_id, "חלב", 1)
    assert item1_result.success
    item1_id = item1_result.data.id
    
    item2_result = item_service.add_item(list_id, "חלב", 2)
    assert item2_result.success
    item2_id = item2_result.data.id
    
    # Mark one as bought
    mark_result = item_service.mark_bought(item1_id)
    assert mark_result.success
    
    # Find locations (excluding bought)
    result = item_service.get_item_locations("חלב")
    assert result.success
    assert len(result.data) == 1
    assert result.data[0].item_id == item2_id
    
    # Find locations (including bought)
    result = item_service.get_item_locations("חלב", include_bought=True)
    assert result.success
    assert len(result.data) == 2


def test_validate_item_name(item_service):
    """Test item name validation."""
    # Valid names
    result = item_service.validate_item_name("חלב")
    assert result.success
    assert result.data == "חלב"
    
    result = item_service.validate_item_name("  חלב  ")
    assert result.success
    assert result.data == "חלב"
    
    # Invalid names
    result = item_service.validate_item_name("")
    assert not result.success
    assert "ריק" in result.error
    
    result = item_service.validate_item_name("א")
    assert not result.success
    assert "2 תווים" in result.error
    
    result = item_service.validate_item_name("milk")
    assert not result.success
    assert "עברית" in result.error
    
    result = item_service.validate_item_name("א" * 101)
    assert not result.success
    assert "100 תווים" in result.error 