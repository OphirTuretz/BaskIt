"""Item management service."""
from typing import Optional, List, TypeVar, cast, Dict
from datetime import datetime, UTC
from dataclasses import dataclass
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from baskit.models import GroceryItem, GroceryList
from baskit.domain.types import HebrewText, Quantity
from .base_service import BaseService, Result


# Generic type for service results
T = TypeVar('T')


@dataclass
class ItemLocation:
    """Represents an item's location in a list."""
    list_id: int
    list_name: str
    item_id: int
    quantity: int
    unit: str
    is_bought: bool


class ItemService(BaseService):
    """Service for managing grocery items."""

    def add_item(
        self,
        list_id: int,
        name: str,
        quantity: int = 1,
        unit: str = "יחידה"
    ) -> Result[GroceryItem]:
        """
        Add an item to a grocery list.
        
        Args:
            list_id: ID of the list to add to
            name: Name of the item
            quantity: Item quantity (default: 1)
            unit: Unit of measurement (default: יחידה)
            
        Returns:
            Result containing the created item or error
        """
        # Validate name
        self.logger.debug("Validating item name", name=name)
        try:
            hebrew_name = HebrewText(name)
            self.logger.debug("Hebrew text validation passed", name=hebrew_name)
        except (ValueError, TypeError) as e:
            self.logger.debug("Hebrew text validation failed", error=str(e))
            return Result.fail(str(e) if e.args else "שם לא תקין")
            
        # Validate quantity
        self.logger.debug("Validating quantity", quantity=quantity, unit=unit)
        try:
            item_quantity = Quantity(value=quantity, unit=unit)
            self.logger.debug("Quantity validation passed", quantity=item_quantity)
        except ValueError as e:
            self.logger.debug("Quantity validation failed", error=str(e))
            error_msg = str(e)
            if quantity <= 0:
                error_msg = "כמות חייבת להיות חיובית"
            elif quantity > 99:
                error_msg = "כמות לא יכולה להיות גדולה מ-99"
            return Result.fail(error_msg)
            
        try:
            with self.transaction.transaction() as session:
                # Check list exists and user owns it
                list_ = session.get(GroceryList, list_id)
                if not list_:
                    return Result.fail("רשימה לא נמצאה")
                
                if list_.owner_id != self.user_id:
                    return Result.fail("אין הרשאה להוסיף פריטים לרשימה זו")
                
                if list_.is_deleted:
                    return Result.fail("לא ניתן להוסיף פריטים לרשימה מחוקה")
                
                # Create normalized name for searching
                normalized = hebrew_name.strip().lower()
                
                # Create new item
                item = GroceryItem(
                    name=hebrew_name,
                    normalized_name=normalized,
                    quantity=item_quantity.value,
                    unit=item_quantity.unit,
                    list_id=list_id,
                    created_by=self.user_id
                )
                session.add(item)
                session.flush()  # Get ID before commit
                
                session.commit()
                session.refresh(item)  # Refresh to ensure all attributes loaded
                
                self._log_action(
                    "add_item",
                    item_id=item.id,
                    list_id=list_id,
                    name=hebrew_name
                )
                return Result.ok(item)
                
        except IntegrityError:
            self.logger.exception("Failed to add item")
            return Result.fail("שגיאה בהוספת הפריט")
        except Exception as e:
            self.logger.exception("Failed to add item")
            return Result.fail("שגיאה בהוספת הפריט")

    def mark_bought(
        self,
        item_id: int,
        is_bought: bool = True
    ) -> Result[GroceryItem]:
        """
        Mark an item as bought or unbought.
        
        Args:
            item_id: ID of the item to mark
            is_bought: Whether to mark as bought (default: True)
            
        Returns:
            Result containing the updated item or error
        """
        try:
            with self.transaction.transaction() as session:
                # Get item and validate ownership
                item = session.get(GroceryItem, item_id)
                if not item:
                    return Result.fail("פריט לא נמצא")
                
                # Get list to check ownership
                list_ = session.get(GroceryList, item.list_id)
                if not list_ or list_.owner_id != self.user_id:
                    return Result.fail("אין הרשאה לעדכן פריט זה")
                
                if list_.is_deleted:
                    return Result.fail("לא ניתן לעדכן פריטים ברשימה מחוקה")
                
                # Update bought status
                item.is_bought = is_bought
                item.bought_at = self._get_now() if is_bought else None
                item.updated_by = self.user_id
                
                session.commit()
                session.refresh(item)
                
                self._log_action(
                    "mark_item",
                    item_id=item_id,
                    is_bought=is_bought
                )
                return Result.ok(item)
                
        except Exception as e:
            self.logger.exception("Failed to mark item")
            return Result.fail("שגיאה בעדכון הפריט")

    def remove_item(
        self,
        item_id: int
    ) -> Result[GroceryItem]:
        """
        Remove an item from a list.
        
        Args:
            item_id: ID of the item to remove
            
        Returns:
            Result containing the removed item or error
        """
        try:
            with self.transaction.transaction() as session:
                # Get item and validate ownership
                item = session.get(GroceryItem, item_id)
                if not item:
                    return Result.fail("פריט לא נמצא")
                
                # Get list to check ownership
                list_ = session.get(GroceryList, item.list_id)
                if not list_ or list_.owner_id != self.user_id:
                    return Result.fail("אין הרשאה למחוק פריט זה")
                
                if list_.is_deleted:
                    return Result.fail("לא ניתן למחוק פריטים מרשימה מחוקה")
                
                # Remove item
                session.delete(item)
                session.commit()
                
                self._log_action(
                    "remove_item",
                    item_id=item_id,
                    list_id=list_.id
                )
                return Result.ok(item)
                
        except Exception as e:
            self.logger.exception("Failed to remove item")
            return Result.fail("שגיאה במחיקת הפריט") 

    def update_item(
        self,
        item_id: int,
        quantity: Optional[int] = None,
        unit: Optional[str] = None
    ) -> Result[GroceryItem]:
        """
        Update an item's quantity and/or unit.
        
        Args:
            item_id: ID of the item to update
            quantity: New quantity (optional)
            unit: New unit of measurement (optional)
            
        Returns:
            Result containing the updated item or error
        """
        try:
            with self.transaction.transaction() as session:
                # Get item and validate ownership
                item = session.get(GroceryItem, item_id)
                if not item:
                    return Result.fail("פריט לא נמצא")
                
                # Get list to check ownership
                list_ = session.get(GroceryList, item.list_id)
                if not list_ or list_.owner_id != self.user_id:
                    return Result.fail("אין הרשאה לעדכן פריט זה")
                
                if list_.is_deleted:
                    return Result.fail("לא ניתן לעדכן פריטים ברשימה מחוקה")

                # Update quantity if provided
                if quantity is not None:
                    try:
                        item_quantity = Quantity(value=quantity, unit=unit or item.unit)
                        item.quantity = item_quantity.value
                        if unit:
                            item.unit = item_quantity.unit
                    except ValueError as e:
                        error_msg = str(e)
                        if quantity <= 0:
                            error_msg = "כמות חייבת להיות חיובית"
                        elif quantity > 99:
                            error_msg = "כמות לא יכולה להיות גדולה מ-99"
                        return Result.fail(error_msg)
                
                # Update unit if provided
                elif unit:
                    try:
                        item_quantity = Quantity(value=item.quantity, unit=unit)
                        item.unit = item_quantity.unit
                    except ValueError as e:
                        return Result.fail(str(e))

                item.updated_by = self.user_id
                session.commit()
                session.refresh(item)
                
                self._log_action(
                    "update_item",
                    item_id=item_id,
                    quantity=quantity,
                    unit=unit
                )
                return Result.ok(item)
                
        except Exception as e:
            self.logger.exception("Failed to update item")
            return Result.fail("שגיאה בעדכון הפריט")

    def increment_quantity(
        self,
        item_id: int,
        step: int = 1
    ) -> Result[GroceryItem]:
        """
        Increment an item's quantity.
        
        Args:
            item_id: ID of the item to increment
            step: Amount to increment by (default: 1)
            
        Returns:
            Result containing the updated item or error
        """
        try:
            with self.transaction.transaction() as session:
                # Get item and validate ownership
                item = session.get(GroceryItem, item_id)
                if not item:
                    return Result.fail("פריט לא נמצא")
                
                # Get list to check ownership
                list_ = session.get(GroceryList, item.list_id)
                if not list_ or list_.owner_id != self.user_id:
                    return Result.fail("אין הרשאה לעדכן פריט זה")
                
                if list_.is_deleted:
                    return Result.fail("לא ניתן לעדכן פריטים ברשימה מחוקה")

                # Calculate new quantity
                new_quantity = item.quantity + step
                
                # Validate new quantity
                try:
                    item_quantity = Quantity(value=new_quantity, unit=item.unit)
                    item.quantity = item_quantity.value
                except ValueError as e:
                    error_msg = str(e)
                    if new_quantity <= 0:
                        error_msg = "כמות חייבת להיות חיובית"
                    elif new_quantity > 99:
                        error_msg = "כמות לא יכולה להיות גדולה מ-99"
                    return Result.fail(error_msg)

                item.updated_by = self.user_id
                session.commit()
                session.refresh(item)
                
                self._log_action(
                    "increment_item",
                    item_id=item_id,
                    step=step
                )
                return Result.ok(item)
                
        except Exception as e:
            self.logger.exception("Failed to increment item quantity")
            return Result.fail("שגיאה בעדכון כמות הפריט")

    def reduce_quantity(
        self,
        item_id: int,
        step: int = 1
    ) -> Result[GroceryItem]:
        """
        Reduce an item's quantity. If quantity becomes 0, the item is removed.
        
        Args:
            item_id: ID of the item to reduce
            step: Amount to reduce by (default: 1)
            
        Returns:
            Result containing the updated item or error
        """
        try:
            with self.transaction.transaction() as session:
                # Get item and validate ownership
                item = session.get(GroceryItem, item_id)
                if not item:
                    return Result.fail("פריט לא נמצא")
                
                # Get list to check ownership
                list_ = session.get(GroceryList, item.list_id)
                if not list_ or list_.owner_id != self.user_id:
                    return Result.fail("אין הרשאה לעדכן פריט זה")
                
                if list_.is_deleted:
                    return Result.fail("לא ניתן לעדכן פריטים ברשימה מחוקה")

                # Calculate new quantity
                new_quantity = item.quantity - step
                
                # If quantity would be 0 or less, remove the item
                if new_quantity <= 0:
                    session.delete(item)
                    session.commit()
                    
                    self._log_action(
                        "remove_item",
                        item_id=item_id,
                        reason="quantity_zero"
                    )
                    return Result.ok(
                        item,
                        message="הפריט הוסר מהרשימה כי הכמות ירדה ל-0"
                    )
                
                # Otherwise update quantity
                try:
                    item_quantity = Quantity(value=new_quantity, unit=item.unit)
                    item.quantity = item_quantity.value
                except ValueError as e:
                    return Result.fail(str(e))

                item.updated_by = self.user_id
                session.commit()
                session.refresh(item)
                
                self._log_action(
                    "reduce_item",
                    item_id=item_id,
                    step=step
                )
                return Result.ok(item)
                
        except Exception as e:
            self.logger.exception("Failed to reduce item quantity")
            return Result.fail("שגיאה בעדכון כמות הפריט") 

    def get_item_locations(
        self,
        name: str,
        include_bought: bool = False
    ) -> Result[List[ItemLocation]]:
        """
        Find all locations of an item across user's lists.
        
        Args:
            name: Name of the item to find
            include_bought: Whether to include bought items (default: False)
            
        Returns:
            Result containing list of item locations or error
        """
        try:
            # Validate and normalize name
            try:
                hebrew_name = HebrewText(name)
                normalized = hebrew_name.strip().lower()
            except (ValueError, TypeError) as e:
                return Result.fail(str(e) if e.args else "שם לא תקין")

            with self.transaction.transaction() as session:
                # Query for items with matching normalized name
                query = (
                    select(GroceryItem, GroceryList)
                    .join(GroceryList)
                    .where(
                        GroceryItem.normalized_name == normalized,
                        GroceryList.owner_id == self.user_id,
                        GroceryList.is_deleted == False
                    )
                )
                
                if not include_bought:
                    query = query.where(GroceryItem.is_bought == False)
                
                results = session.execute(query).all()
                
                # Convert to ItemLocation objects
                locations = [
                    ItemLocation(
                        list_id=list_.id,
                        list_name=list_.name,
                        item_id=item.id,
                        quantity=item.quantity,
                        unit=item.unit,
                        is_bought=item.is_bought
                    )
                    for item, list_ in results
                ]
                
                if not locations:
                    return Result.fail(
                        "פריט לא נמצא באף רשימה",
                        suggestions=["נסה לחפש בשם אחר", "כולל פריטים שנקנו"] if not include_bought else None
                    )
                
                self._log_action(
                    "search_items",
                    name=hebrew_name,
                    found_count=len(locations)
                )
                return Result.ok(locations)
                
        except Exception as e:
            self.logger.exception("Failed to search for item")
            return Result.fail("שגיאה בחיפוש הפריט")

    def validate_item_name(self, name: str) -> Result[str]:
        """
        Validate an item name.
        
        Args:
            name: Name to validate
            
        Returns:
            Result containing normalized name or error
        """
        try:
            # Basic validation
            if not name or not name.strip():
                return Result.fail("שם הפריט לא יכול להיות ריק")
            
            # Validate Hebrew text
            try:
                hebrew_name = HebrewText(name)
            except (ValueError, TypeError) as e:
                return Result.fail(str(e) if e.args else "שם לא תקין")
            
            # Create normalized version
            normalized = hebrew_name.strip().lower()
            
            # Check length
            if len(normalized) < 2:
                return Result.fail("שם הפריט חייב להכיל לפחות 2 תווים")
            
            if len(normalized) > 100:
                return Result.fail("שם הפריט לא יכול להכיל יותר מ-100 תווים")
            
            return Result.ok(normalized)
            
        except Exception as e:
            self.logger.exception("Failed to validate item name")
            return Result.fail("שגיאה באימות שם הפריט") 