"""Service for handling AI tool operations."""
from typing import Optional, Dict, Any, List, Tuple
from baskit.services.base_service import BaseService, Result
from baskit.services.item_service import ItemService, ItemLocation
from baskit.services.list_service import ListService
from baskit.domain.types import HebrewText
from baskit.utils.logger import get_logger

logger = get_logger(__name__)

class ToolService(BaseService):
    """Service for handling AI tool operations."""

    def __init__(self, session, user_id: int):
        """Initialize the service."""
        super().__init__(session, user_id)
        self.item_service = ItemService(session, user_id)
        self.list_service = ListService(session, user_id)

    def resolve_list(self, list_name: Optional[str] = None) -> Result[int]:
        """
        Resolve list ID from name or default.
        
        Args:
            list_name: Name of the list (optional)
            
        Returns:
            Result containing list ID or error
        """
        if list_name:
            # Find list by name
            lists = self.list_service.get_lists()
            if not lists.success:
                return Result.fail(lists.error)
            
            if not lists.data:
                return Result.fail(f"לא מצאתי רשימה בשם {list_name}")
            
            target_list = next(
                (l for l in lists.data if l.name == list_name),
                None
            )
            
            if not target_list:
                return Result.fail(f"לא מצאתי רשימה בשם {list_name}")
            
            return Result.ok(target_list.id)
        
        # Use default list
        default = self.list_service.get_default_list()
        if not default.success or not default.data:
            return Result.fail("לא נמצאה רשימת ברירת מחדל")
        
        return Result.ok(default.data.id)

    def resolve_item(
        self,
        item_name: str,
        list_name: Optional[str] = None,
        include_bought: bool = False
    ) -> Result[Tuple[int, ItemLocation]]:
        """
        Resolve item name to ID and location info.
        
        Args:
            item_name: Name of the item to resolve
            list_name: Optional list name for context
            include_bought: Whether to include bought items in search
            
        Returns:
            Result containing tuple of (item_id, location_info) or error
        """
        try:
            # Validate and normalize name
            name = HebrewText(item_name)
            
            # Find the item
            locations = self.item_service.get_item_locations(
                str(name),
                include_bought=include_bought
            )
            
            if not locations.success:
                return Result.fail(
                    f"לא מצאתי {name} ברשימה",
                    suggestions=["בדוק את שם הפריט"]
                )
            
            if not locations.data:
                return Result.fail(
                    "שגיאה פנימית: לא נמצאו מיקומים",
                    suggestions=["נסה שוב"]
                )
            
            # Handle multiple locations
            if len(locations.data) > 1 and not list_name:
                suggestions = [
                    f"בחר רשימה: {', '.join(loc.list_name for loc in locations.data)}"
                ]
                return Result.fail(
                    f"הפריט {name} נמצא במספר רשימות",
                    suggestions=suggestions
                )
            
            # If list name specified, find matching location
            if list_name:
                location = next(
                    (loc for loc in locations.data if loc.list_name == list_name),
                    None
                )
                if not location:
                    return Result.fail(
                        f"לא מצאתי {name} ברשימה {list_name}",
                        suggestions=["בדוק את שם הרשימה"]
                    )
            else:
                location = locations.data[0]
            
            return Result.ok((location.item_id, location))
            
        except Exception as e:
            self.logger.exception("Failed to resolve item")
            return Result.fail(
                "שגיאה בזיהוי הפריט",
                suggestions=["נסה שוב", "בדוק את שם הפריט"]
            )

    def handle_multiple_locations(
        self,
        locations: List[ItemLocation],
        item_name: str,
        action: str
    ) -> Result[Dict[str, Any]]:
        """
        Handle case where item exists in multiple lists.
        
        Args:
            locations: List of item locations
            item_name: Name of the item
            action: Action being performed (for error message)
            
        Returns:
            Result containing error with location data
        """
        return Result.fail(
            f"מצאתי {item_name} במספר רשימות. באיזו רשימה {action}?",
            suggestions=[loc.list_name for loc in locations]
        ) 