"""Base service class with common functionality."""
from typing import TypeVar, Generic, Optional, List, Any
from datetime import datetime, UTC
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from baskit.utils.logger import get_logger
from baskit.db.session import TransactionManager

# Generic type for service results
T = TypeVar('T')


class Result(BaseModel, Generic[T]):
    """Generic result type for service operations."""
    success: bool
    data: Optional[T] = None
    error: str = ""
    suggestions: List[str] = []
    metadata: dict = {}

    # Allow arbitrary types (like SQLAlchemy models)
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def ok(cls, data: T, **metadata) -> 'Result[T]':
        """Create a successful result."""
        return cls(success=True, data=data, metadata=metadata)

    @classmethod
    def fail(cls, error: str, suggestions: Optional[List[str]] = None) -> 'Result[T]':
        """Create a failed result."""
        return cls(success=False, error=error or "שגיאה לא ידועה", suggestions=suggestions or [])


class BaseService:
    """Base class for all services."""

    def __init__(self, session: Session, user_id: int):
        """
        Initialize the service.
        
        Args:
            session: Database session
            user_id: ID of the current user
        """
        self.session = session
        self.user_id = user_id
        self.logger = get_logger(self.__class__.__name__)
        self.transaction = TransactionManager(session)

    def _log_action(
        self, 
        action: str, 
        status: str = "success", 
        **kwargs
    ) -> None:
        """
        Log a service action.
        
        Args:
            action: Name of the action
            status: Status of the action
            **kwargs: Additional log data
        """
        self.logger.info(
            f"{action}: {status}",
            user_id=self.user_id,
            **kwargs
        )

    def _get_now(self) -> datetime:
        """Get current UTC datetime."""
        return datetime.now(UTC)

    def _validate_name(self, name: str, min_length: int = 1) -> Result[str]:
        """
        Validate a name string.
        
        Args:
            name: Name to validate
            min_length: Minimum length required
            
        Returns:
            Result indicating if name is valid
        """
        if not name or not name.strip():
            return Result.fail("שם לא יכול להיות ריק")
        
        name = name.strip()
        if len(name) < min_length:
            return Result.fail(
                f"שם חייב להכיל לפחות {min_length} תווים",
                suggestions=[
                    "נסה שם ארוך יותר",
                    "הוסף פרטים נוספים לשם"
                ]
            )
        
        return Result.ok(name)

    def _handle_duplicate_error(
        self, 
        name: str,
        suggestions: Optional[List[str]] = None
    ) -> Result[T]:
        """
        Handle duplicate name errors.
        
        Args:
            name: The duplicate name
            suggestions: Optional list of suggestions
            
        Returns:
            Result with error and suggestions
        """
        return Result.fail(
            f"השם '{name}' כבר קיים",
            suggestions=suggestions or [
                "נסה שם אחר",
                f"הוסף מספר או תיאור ל'{name}'"
            ]
        ) 