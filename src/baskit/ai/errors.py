"""Error handling for GPT integration."""
from typing import Optional, List, Dict, Any, TypeVar
from pydantic import BaseModel

from baskit.services.base_service import Result


T = TypeVar('T')


class GPTError(Exception):
    """Base class for GPT-related errors."""
    def __init__(
        self,
        message: str,
        suggestions: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.suggestions = suggestions or []
        self.metadata = metadata or {}
        super().__init__(message)


class APIError(GPTError):
    """Error from OpenAI API."""
    pass


class ValidationError(GPTError):
    """Error validating GPT response."""
    pass


class AmbiguousInputError(GPTError):
    """Error for ambiguous user inputs."""
    pass


class ToolExecutionError(GPTError):
    """Error executing a tool."""
    pass


class ToolExecutionResult(Result[Dict[str, Any]]):
    """Result type for tool execution."""
    
    @classmethod
    def from_error(cls, error: GPTError) -> 'ToolExecutionResult':
        """Create result from GPTError."""
        return cls(
            success=False,
            error=error.message,
            suggestions=error.suggestions,
            metadata=error.metadata
        )
    
    @classmethod
    def from_exception(cls, e: Exception) -> 'ToolExecutionResult':
        """Create result from generic exception."""
        return cls(
            success=False,
            error=str(e) or "שגיאה לא ידועה",
            suggestions=["נסה שוב", "נסה לנסח את הבקשה אחרת"]
        ) 