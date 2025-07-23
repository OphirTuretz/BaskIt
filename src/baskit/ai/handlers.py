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
            'show_list': self._handle_show_list,
            'reduce_quantity': self._handle_reduce_quantity
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
        """Execute a tool call."""
        try:
            self.logger.info(
                "Starting tool execution",
                tool_call=tool_call,
                context=context
            )
            
            tool_name = tool_call['name']
            arguments = tool_call['arguments']
            
            self.logger.info(
                "Tool call parsed",
                tool_name=tool_name,
                arguments=arguments
            )
            
            # Get handler method from the handlers dictionary
            handler = self.handlers.get(tool_name)
            if not handler:
                self.logger.error(
                    "No handler found for tool",
                    tool_name=tool_name
                )
                return ToolExecutionResult.from_error(
                    ToolExecutionError(
                        f'כלי לא נתמך: {tool_name}',
                        suggestions=["השתמש בכלי מהרשימה המאושרת"]
                    )
                )
            
            # Execute handler
            return await handler(arguments, context)
        except Exception as e:
            self.logger.exception(
                "Tool execution failed",
                error=str(e)
            )
            return ToolExecutionResult.from_error(
                ToolExecutionError(str(e))
            )

    async def _handle_add_item(
        self,
        arguments: Dict[str, Any],
        context: GPTContext
    ) -> ToolExecutionResult:
        """Handle add_item tool."""
        try:
            # Parse item details
            name = HebrewText(arguments['item_name'])
            quantity = Quantity(
                value=arguments.get('quantity', 1),
                unit=arguments.get('unit', 'יחידה')
            )
            list_name = arguments.get('list_name')
            
            # Get list (default or specified)
            list_result = self.tool_service.resolve_list(list_name)
            if not list_result.success:
                return ToolExecutionResult.from_error(ToolExecutionError(
                    list_result.error,
                    suggestions=list_result.suggestions
                ))
            list_id = list_result.data
            
            # Check for duplicates if enabled
            if not self.allow_duplicates:
                item_result = self.tool_service.resolve_item(str(name), list_name)
                if item_result.success:
                    if self.auto_merge:
                        # Update existing item through the update handler
                        item_id, location = item_result.data
                        self.logger.info(
                            "Found duplicate item, preparing to update",
                            item_id=item_id,
                            location=location,
                            quantity=quantity.value,
                            unit=quantity.unit
                        )
                        # Create a proper tool call structure
                        update_tool_call = {
                            'name': 'update_quantity',
                            'arguments': {
                                'item_name': str(name),
                                'quantity': location.quantity + quantity.value,
                                'unit': quantity.unit,
                                'list_name': list_name
                            }
                        }
                        self.logger.info(
                            "Calling update_quantity with arguments",
                            tool_call=update_tool_call
                        )
                        return await self.execute(update_tool_call, context)
                    else:
                        return ToolExecutionResult.from_error(ToolExecutionError(
                            f"פריט בשם '{name}' כבר קיים",
                            suggestions=[
                                "השתמש בשם אחר",
                                "עדכן את הכמות של הפריט הקיים"
                            ]
                        ))
            
            # Add the item
            result = self.item_service.add_item(
                list_id=list_id,
                name=str(name),
                quantity=quantity.value,
                unit=quantity.unit
            )
            
            if not result.success:
                return ToolExecutionResult.from_error(ToolExecutionError(
                    result.error,
                    suggestions=result.suggestions
                ))
            
            return ToolExecutionResult(
                success=True,
                message=f"הוספתי {quantity} {name}",
                data={'item': result.data}
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
        self.logger.info(
            "Handling update_quantity",
            arguments=arguments
        )
        try:
            # Get list (default or specified)
            list_name = arguments.get('list_name')
            list_result = self.tool_service.resolve_list(list_name)
            if not list_result.success:
                self.logger.error(
                    "Failed to resolve list",
                    list_name=list_name,
                    error=list_result.error
                )
                return ToolExecutionResult.from_error(ToolExecutionError(
                    list_result.error,
                    suggestions=list_result.suggestions
                ))
            list_id = list_result.data
            
            # Parse item details
            name = HebrewText(arguments['item_name'])
            quantity = Quantity(
                value=arguments.get('quantity'),
                unit=arguments.get('unit')
            )
            
            # Resolve item name to ID
            item_result = self.tool_service.resolve_item(str(name), list_name)
            if not item_result.success:
                self.logger.error(
                    "Failed to resolve item",
                    item_name=str(name),
                    list_name=list_name,
                    error=item_result.error
                )
                return ToolExecutionResult.from_error(ToolExecutionError(
                    item_result.error,
                    suggestions=item_result.suggestions
                ))
            
            # Update the item
            item_id, location = item_result.data
            result = self.item_service.update_item(
                item_id=item_id,
                quantity=quantity.value,
                unit=quantity.unit
            )
            
            if not result.success:
                self.logger.error(
                    "Failed to update item quantity",
                    item_id=item_id,
                    error=result.error
                )
                return ToolExecutionResult.from_error(ToolExecutionError(
                    result.error or "שגיאה בעדכון כמות",
                    suggestions=result.suggestions
                ))
            
            self.logger.info(
                "Item quantity updated",
                item_id=item_id,
                new_quantity=quantity.value,
                new_unit=quantity.unit
            )
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

    async def _handle_reduce_quantity(
        self,
        arguments: Dict[str, Any],
        context: GPTContext
    ) -> ToolExecutionResult:
        """Handle reduce_quantity tool."""
        try:
            # Parse item details
            name = HebrewText(arguments['item_name'])
            step = arguments.get('step', 1)  # Default to 1 if not specified
            list_name = arguments.get('list_name')
            
            # Resolve item name to ID
            item_result = self.tool_service.resolve_item(str(name), list_name)
            if not item_result.success:
                return ToolExecutionResult.from_error(ToolExecutionError(
                    item_result.error,
                    suggestions=item_result.suggestions
                ))
            
            # Get item location
            item_id, location = item_result.data
            
            # Reduce the quantity
            result = self.item_service.reduce_quantity(item_id, step=step)
            
            if not result.success:
                return ToolExecutionResult.from_error(ToolExecutionError(
                    result.error,
                    suggestions=result.suggestions
                ))
            
            return ToolExecutionResult(
                success=True,
                message=f"הורדתי {step} {name}",
                data={'item': result.data}
            )
            
        except Exception as e:
            self.logger.exception("Failed to reduce item quantity")
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
            
            # Resolve item name to ID
            item_result = self.tool_service.resolve_item(str(name), list_name)
            if not item_result.success:
                return ToolExecutionResult.from_error(ToolExecutionError(
                    item_result.error,
                    suggestions=item_result.suggestions
                ))
            
            # Mark as bought
            item_id, location = item_result.data
            result = self.item_service.mark_bought(
                item_id=item_id,
                is_bought=True
            )
            
            if not result.success:
                return ToolExecutionResult.from_error(ToolExecutionError(
                    result.error,
                    suggestions=result.suggestions
                ))
            
            return ToolExecutionResult(
                success=True,
                message=f"סימנתי {name} כנקנה",
                data={'item': result.data}
            )
            
        except Exception as e:
            self.logger.exception("Failed to mark item as bought")
            return ToolExecutionResult.from_exception(e)

    async def _handle_create_list(
        self,
        arguments: Dict[str, Any],
        context: GPTContext
    ) -> ToolExecutionResult:
        """Handle create_list tool."""
        try:
            # Create the list
            name = arguments['list_name']
            result = self.list_service.create_list(name)
            
            if not result.success:
                return ToolExecutionResult.from_error(ToolExecutionError(
                    result.error,
                    suggestions=result.suggestions
                ))
            
            return ToolExecutionResult(
                success=True,
                message=f"יצרתי רשימה חדשה: {name}",
                data={'list': result.data}
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
            # Get list name (or use default)
            list_name = arguments.get('list_name')
            include_bought = arguments.get('include_bought', True)
            
            # Get list items
            result = self.list_service.get_list_items(
                list_name=list_name,
                include_bought=include_bought
            )
            
            if not result.success:
                return ToolExecutionResult.from_error(ToolExecutionError(
                    result.error,
                    suggestions=result.suggestions
                ))
            
            return ToolExecutionResult(
                success=True,
                message="הנה הרשימה שביקשת",
                data={'items': result.data}
            )
            
        except Exception as e:
            self.logger.exception("Failed to show list")
            return ToolExecutionResult.from_exception(e)

    def _handle_validation_error(self, e: PydanticValidationError) -> ToolExecutionResult:
        """Handle validation errors."""
        return ToolExecutionResult.from_error(ToolExecutionError(
            "נתונים לא תקינים",
            suggestions=["וודא שכל השדות הנדרשים מלאים"]
        ))

    def _handle_ambiguous_input(self, e: AmbiguousInputError) -> ToolExecutionResult:
        """Handle ambiguous input errors."""
        return ToolExecutionResult.from_error(ToolExecutionError(
            str(e),
            suggestions=e.suggestions
        )) 