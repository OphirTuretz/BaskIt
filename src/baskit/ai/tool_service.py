"""Service for handling AI tool operations."""
from typing import Optional, Dict, Any, List
from baskit.services.base_service import BaseService, Result
from baskit.services.item_service import ItemService, ItemLocation
from baskit.services.list_service import ListService
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