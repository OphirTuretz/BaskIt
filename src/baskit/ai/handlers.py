"""Tool execution handler."""
import asyncio
from typing import Dict, Any, Optional, List, Callable, TypeVar
from pydantic import ValidationError as PydanticValidationError

from baskit.utils.logger import get_logger
from baskit.services.item_service import ItemService
from baskit.services.list_service import ListService
from baskit.domain.types import HebrewText, Quantity
from baskit.config.settings import get_settings
from .models import GPTContext
from .errors import (
    ToolExecutionError,
    AmbiguousInputError,
    ToolExecutionResult
)
from .tool_service import ToolService


T = TypeVar('T')


class ToolExecutor:
    """Executes tool calls with error handling."""

    def __init__(
        self,
        item_service: ItemService,
        list_service: ListService
    ):
        """Initialize the executor."""
        self.item_service = item_service
        self.list_service = list_service
        self.tool_service = ToolService(item_service.session, item_service.user_id)
        self.logger = get_logger(self.__class__.__name__)
        
        # Load settings
        settings = get_settings()
        self.tool_timeout = settings.TOOL_TIMEOUT
        self.max_retries = settings.MAX_RETRIES
        self.retry_delay = settings.RETRY_DELAY
        self.allow_duplicates = settings.ALLOW_DUPLICATE_ITEMS
        self.auto_merge = settings.AUTO_MERGE_SIMILAR
        self.soft_delete = settings.SOFT_DELETE
        
        # Map tool names to their handlers
        self.handlers: Dict[str, Callable] = {
            'add_item': self._handle_add_item,
            'remove_item': self._handle_remove_item,
            'update_quantity': self._handle_update_quantity,
            'mark_bought': self._handle_mark_bought,
            'create_list': self._handle_create_list,
            'show_list': self._handle_show_list
        }
        
        # Map error types to handlers
        self.error_handlers = {
            PydanticValidationError: self._handle_validation_error,
            AmbiguousInputError: self._handle_ambiguous_input,
            # Add more error handlers as needed
        }

    async def execute(
        self,
        tool_call: Dict[str, Any],
        context: GPTContext
    ) -> ToolExecutionResult:
        """
        Execute a tool call with error handling.
        
        Args:
            tool_call: Tool call details from GPT
            context: Current conversation context
            
        Returns:
            Result of tool execution
        """
        try:
            tool_name = tool_call['name']
            arguments = tool_call['arguments']
            
            handler = self.handlers.get(tool_name)
            if not handler:
                return ToolExecutionResult.from_error(ToolExecutionError(
                    f"כלי לא נתמך: {tool_name}",
                    suggestions=["נסה להשתמש בכלי אחר"]
                ))
            
            self.logger.info(
                "Executing tool",
                tool=tool_name,
                arguments=arguments
            )
            
            # Execute with timeout
            try:
                async with asyncio.timeout(self.tool_timeout):
                    result = await handler(arguments, context)
            except asyncio.TimeoutError:
                return ToolExecutionResult.from_error(ToolExecutionError(
                    "פעולה ארכה יותר מדי זמן",
                    suggestions=["נסה שוב", "פצל את הפעולה לחלקים קטנים יותר"]
                ))
            
            self.logger.info(
                "Tool execution completed",
                tool=tool_name,
                success=result.success
            )
            
            return result
            
        except Exception as e:
            # Try to handle known error types
            for error_type, handler in self.error_handlers.items():
                if isinstance(e, error_type):
                    return handler(e)
            
            # Fall back to generic error handling
            self.logger.exception("Tool execution failed")
            return ToolExecutionResult.from_exception(e)

    async def _handle_add_item(
        self,
        arguments: Dict[str, Any],
        context: GPTContext
    ) -> ToolExecutionResult:
        """Handle add_item tool."""
        try:
            # Get list (default or specified)
            list_name = arguments.get('list_name')
            list_result = self.tool_service.resolve_list(list_name)
            if not list_result.success:
                return ToolExecutionResult.from_error(ToolExecutionError(
                    list_result.error,
                    suggestions=list_result.suggestions
                ))
            list_id = list_result.data
            
            # Parse item details
            name = HebrewText(arguments['item_name'])
            quantity = Quantity(
                value=arguments.get('quantity', 1),
                unit=arguments.get('unit', 'יחידה')
            )
            
            # Check for duplicates if enabled
            if not self.allow_duplicates:
                item_result = self.tool_service.resolve_item(str(name), list_name)
                if item_result.success:
                    if self.auto_merge:
                        # Update existing item
                        item_id, location = item_result.data
                        result = self.item_service.update_item(
                            item_id=item_id,
                            quantity=location.quantity + quantity.value,
                            unit=quantity.unit
                        )
                        if not result.success:
                            return ToolExecutionResult.from_error(ToolExecutionError(
                                result.error or "שגיאה בעדכון פריט",
                                suggestions=result.suggestions
                            ))
                        return ToolExecutionResult(
                            success=True,
                            message=f"עדכנתי את הכמות של {name}",
                            data={
                                'item': {
                                    'id': result.data.id,
                                    'name': result.data.name,
                                    'quantity': result.data.quantity,
                                    'unit': result.data.unit
                                }
                            }
                        )
                    else:
                        return ToolExecutionResult.from_error(ToolExecutionError(
                            f"פריט בשם '{name}' כבר קיים",
                            suggestions=[
                                "השתמש בשם אחר",
                                "עדכן את הכמות של הפריט הקיים"
                            ]
                        ))
            
            # Add new item
            result = self.item_service.add_item(
                list_id=list_id,
                name=str(name),
                quantity=quantity.value,
                unit=quantity.unit
            )
            
            if not result.success:
                return ToolExecutionResult.from_error(ToolExecutionError(
                    result.error or "שגיאה בהוספת פריט",
                    suggestions=result.suggestions
                ))
            
            return ToolExecutionResult(
                success=True,
                message=f"הוספתי {quantity.value} {name} לרשימה",
                data={
                    'item': {
                        'id': result.data.id,
                        'name': result.data.name,
                        'quantity': result.data.quantity,
                        'unit': result.data.unit
                    }
                }
            )
            
        except Exception as e:
            self.logger.exception("Failed to add item")
            return ToolExecutionResult.from_exception(e)

    async def _handle_remove_item(
        self,
        arguments: Dict[str, Any],
        context: GPTContext
    ) -> ToolExecutionResult:
        """Handle remove_item tool."""
        try:
            # Parse item details
            name = HebrewText(arguments['item_name'])
            list_name = arguments.get('list_name')
            
            # Resolve item name to ID
            item_result = self.tool_service.resolve_item(str(name), list_name)
            if not item_result.success:
                return ToolExecutionResult.from_error(ToolExecutionError(
                    item_result.error,
                    suggestions=item_result.suggestions
                ))
            
            # Remove or mark as bought
            item_id, location = item_result.data
            if self.soft_delete:
                # Mark as bought instead of removing
                result = self.item_service.mark_bought(
                    item_id=item_id,
                    is_bought=True
                )
            else:
                result = self.item_service.remove_item(item_id)
            
            if not result.success:
                return ToolExecutionResult.from_error(ToolExecutionError(
                    result.error,
                    suggestions=result.suggestions
                ))
            
            action = "סימנתי כנקנה" if self.soft_delete else "מחקתי"
            return ToolExecutionResult(
                success=True,
                message=f"{action} את {name}",
                data={
                    'item': {
                        'id': item_id,
                        'name': str(name),
                        'is_bought': self.soft_delete
                    }
                }
            )
            
        except Exception as e:
            self.logger.exception("Failed to remove item")
            return ToolExecutionResult.from_exception(e)

    async def _handle_update_quantity(
        self,
        arguments: Dict[str, Any],
        context: GPTContext
    ) -> ToolExecutionResult:
        """Handle update_quantity tool."""
        try:
            # Parse item details
            name = HebrewText(arguments['item_name'])
            quantity = arguments.get('quantity')
            unit = arguments.get('unit')
            list_name = arguments.get('list_name')
            
            # Resolve item name to ID
            item_result = self.tool_service.resolve_item(str(name), list_name)
            if not item_result.success:
                return ToolExecutionResult.from_error(ToolExecutionError(
                    item_result.error,
                    suggestions=item_result.suggestions
                ))
            
            # Update the item
            item_id, location = item_result.data
            result = self.item_service.update_item(
                item_id=item_id,
                quantity=quantity,
                unit=unit
            )
            
            if not result.success:
                return ToolExecutionResult.from_error(ToolExecutionError(
                    result.error or "שגיאה בעדכון כמות",
                    suggestions=result.suggestions
                ))
            
            return ToolExecutionResult(
                success=True,
                message=f"עדכנתי את הכמות של {name} ל-{quantity}",
                data={
                    'item': {
                        'id': result.data.id,
                        'name': result.data.name,
                        'quantity': result.data.quantity,
                        'unit': result.data.unit
                    }
                }
            )
            
        except Exception as e:
            self.logger.exception("Failed to update quantity")
            return ToolExecutionResult.from_exception(e)

    async def _handle_mark_bought(
        self,
        arguments: Dict[str, Any],
        context: GPTContext
    ) -> ToolExecutionResult:
        """Handle mark_bought tool."""
        try:
            # Parse item details
            name = HebrewText(arguments['item_name'])
            list_name = arguments.get('list_name')
            is_bought = arguments.get('is_bought', True)
            
            # Resolve item name to ID
            item_result = self.tool_service.resolve_item(
                str(name),
                list_name,
                include_bought=True
            )
            if not item_result.success:
                return ToolExecutionResult.from_error(ToolExecutionError(
                    item_result.error,
                    suggestions=item_result.suggestions
                ))
            
            # Mark as bought
            item_id, location = item_result.data
            result = self.item_service.mark_bought(
                item_id=item_id,
                is_bought=is_bought
            )
            
            if not result.success:
                return ToolExecutionResult.from_error(ToolExecutionError(
                    result.error or "שגיאה בסימון פריט",
                    suggestions=result.suggestions
                ))
            
            status = "נקנה" if is_bought else "לא נקנה"
            return ToolExecutionResult(
                success=True,
                message=f"סימנתי את {name} כ{status}",
                data={
                    'item': {
                        'id': result.data.id,
                        'name': result.data.name,
                        'is_bought': result.data.is_bought
                    }
                }
            )
            
        except Exception as e:
            self.logger.exception("Failed to mark item")
            return ToolExecutionResult.from_exception(e)

    async def _handle_create_list(
        self,
        arguments: Dict[str, Any],
        context: GPTContext
    ) -> ToolExecutionResult:
        """Handle create_list tool."""
        try:
            name = HebrewText(arguments['name'])
            
            result = self.list_service.create_list(str(name))
            
            if not result.success or not result.data:
                return ToolExecutionResult.from_error(ToolExecutionError(
                    result.error or "שגיאה ביצירת רשימה",
                    suggestions=result.suggestions
                ))
            
            return ToolExecutionResult(
                success=True,
                data={
                    'list': {
                        'id': result.data.id,
                        'name': result.data.name
                    }
                }
            )
            
        except Exception as e:
            self.logger.exception("Failed to create list")
            return ToolExecutionResult.from_exception(e)

    async def _handle_show_list(
        self,
        arguments: Dict[str, Any],
        context: GPTContext
    ) -> ToolExecutionResult:
        """Handle show_list tool."""
        try:
            list_id = arguments.get('list_id')
            include_bought = arguments.get('include_bought', True)
            
            result = self.list_service.show_list(
                list_id=list_id,
                include_bought=include_bought
            )
            
            if not result.success or not result.data:
                return ToolExecutionResult.from_error(ToolExecutionError(
                    result.error or "שגיאה בהצגת רשימה",
                    suggestions=result.suggestions
                ))
            
            return ToolExecutionResult(
                success=True,
                data={
                    'list': {
                        'id': result.data.id,
                        'name': result.data.name,
                        'items': [
                            {
                                'id': item.id,
                                'name': item.name,
                                'quantity': item.quantity,
                                'unit': item.unit,
                                'is_bought': item.is_bought
                            }
                            for item in result.data.items
                        ]
                    }
                }
            )
            
        except Exception as e:
            self.logger.exception("Failed to show list")
            return ToolExecutionResult.from_exception(e)

    def _handle_validation_error(
        self,
        error: PydanticValidationError
    ) -> ToolExecutionResult:
        """Handle Pydantic validation errors."""
        self.logger.error(
            "Validation error",
            errors=error.errors()
        )
        return ToolExecutionResult.from_error(ToolExecutionError(
            "הערכים שסופקו אינם תקינים",
            suggestions=["בדוק את הערכים ונסה שוב"]
        ))

    def _handle_ambiguous_input(
        self,
        error: AmbiguousInputError
    ) -> ToolExecutionResult:
        """Handle ambiguous input errors."""
        return ToolExecutionResult.from_error(error) 