"""Tool definitions for BaskIt's AI functionality."""
from typing import Optional, List, Dict, Any, TypeVar, Callable, Union
from pydantic import BaseModel, Field
from functools import wraps
from baskit.utils.logger import get_logger
from baskit.domain.types import HebrewText
from baskit.services.item_service import ItemService, ItemLocation
from baskit.services.list_service import ListService
from .tool_service import ToolService

logger = get_logger(__name__)

# Type variable for generic return type
T = TypeVar('T')

def tool(func: Callable[..., Dict[str, Any]]) -> Callable[..., Dict[str, Any]]:
    """Decorator to mark a function as an AI tool."""
    @wraps(func)
    def wrapper(*args, **kwargs) -> Dict[str, Any]:
        tool_name = func.__name__
        logger.info(
            f"Executing tool: {tool_name}",
            tool=tool_name,
            args=args[1:],  # Skip service arg
            kwargs=kwargs
        )
        try:
            result = func(*args, **kwargs)
            logger.info(
                f"Tool {tool_name} completed",
                tool=tool_name,
                status=result["status"],
                has_data=bool(result.get("data"))
            )
            return result
        except Exception as e:
            logger.exception(
                f"Tool {tool_name} failed",
                tool=tool_name,
                error=str(e)
            )
            return {
                "status": "error",
                "message": str(e),
                "data": None
            }
    return wrapper

def _validate_quantity(quantity: int) -> Optional[str]:
    """Validate item quantity."""
    if quantity <= 0:
        return "כמות חייבת להיות חיובית"
    if quantity > 99:
        return "כמות לא יכולה להיות גדולה מ-99"
    return None

def _validate_hebrew_text(text: str) -> Optional[str]:
    """Validate Hebrew text input."""
    try:
        HebrewText(text)
        return None
    except ValueError as e:
        return str(e)

# Tool Models
class AddItem(BaseModel):
    """Add a new item to a shopping list."""
    item_name: str = Field(..., description="Name of the item to add (in Hebrew)")
    quantity: int = Field(default=1, description="Quantity of the item")
    list_name: Optional[str] = Field(default=None, description="Name of the list to add to (uses default if not specified)")
    unit: str = Field(default="יחידה", description="Unit of measurement (e.g., יחידה, ליטר, etc.)")

class UpdateItem(BaseModel):
    """Update an existing item's quantity."""
    item_name: str = Field(..., description="Name of the item to update (in Hebrew)")
    quantity: int = Field(..., description="New quantity for the item")
    list_name: Optional[str] = Field(default=None, description="Name of the list containing the item (uses default if not specified)")

class IncrementQuantity(BaseModel):
    """Increment an item's quantity."""
    item_name: str = Field(..., description="Name of the item to increment (in Hebrew)")
    step: int = Field(default=1, description="Amount to increment by")
    list_name: Optional[str] = Field(default=None, description="Name of the list containing the item (uses default if not specified)")

class ReduceQuantity(BaseModel):
    """Reduce an item's quantity."""
    item_name: str = Field(..., description="Name of the item to reduce (in Hebrew)")
    step: int = Field(default=1, description="Amount to reduce by")
    list_name: Optional[str] = Field(default=None, description="Name of the list containing the item (uses default if not specified)")

class DeleteItem(BaseModel):
    """Delete an item from a list."""
    item_name: str = Field(..., description="Name of the item to delete (in Hebrew)")
    list_name: Optional[str] = Field(default=None, description="Name of the list containing the item (uses default if not specified)")

class MarkItemBought(BaseModel):
    """Mark an item as bought."""
    item_name: str = Field(..., description="Name of the item to mark as bought (in Hebrew)")
    list_name: Optional[str] = Field(default=None, description="Name of the list containing the item (uses default if not specified)")

class CreateList(BaseModel):
    """Create a new shopping list."""
    list_name: str = Field(..., description="Name for the new list (in Hebrew)")

class DeleteList(BaseModel):
    """Delete a shopping list."""
    list_name: str = Field(..., description="Name of the list to delete (in Hebrew)")
    hard_delete: bool = Field(default=False, description="Whether to permanently delete the list")

class ShowList(BaseModel):
    """Show contents of a shopping list."""
    list_name: Optional[str] = Field(default=None, description="Name of the list to show (uses default if not specified)")

class SetDefaultList(BaseModel):
    """Set a list as the default list."""
    list_name: str = Field(..., description="Name of the list to set as default (in Hebrew)")

class ParseText(BaseModel):
    """Parse Hebrew text input into structured item data."""
    text: str = Field(..., description="Hebrew text input to parse")

@tool
def add_item(tool_service: ToolService, params: AddItem) -> Dict[str, Any]:
    """Add a new item to a list."""
    # Validate Hebrew text
    text_error = _validate_hebrew_text(params.item_name)
    if text_error:
        return {
            "status": "error",
            "message": text_error,
            "data": None
        }
    
    # Validate quantity
    quantity_error = _validate_quantity(params.quantity)
    if quantity_error:
        return {
            "status": "error",
            "message": quantity_error,
            "data": None
        }
    
    # Handle list resolution
    list_result = tool_service.resolve_list(params.list_name)
    if not list_result.success:
        return {
            "status": "error",
            "message": list_result.error,
            "data": None
        }
    
    if list_result.data is None:
        return {
            "status": "error",
            "message": "שגיאה פנימית: מזהה רשימה חסר",
            "data": None
        }
    
    # Add the item
    result = tool_service.item_service.add_item(
        list_id=list_result.data,
        name=params.item_name,
        quantity=params.quantity,
        unit=getattr(params, 'unit', 'יחידה')  # Use unit if provided
    )
    
    if not result.success:
        return {
            "status": "error",
            "message": result.error,
            "data": None
        }
    
    return {
        "status": "success",
        "message": f"הוספתי {params.quantity} {params.item_name} לרשימה",
        "data": {"item": result.data}
    }

@tool
def update_item(tool_service: ToolService, params: UpdateItem) -> Dict[str, Any]:
    """Update an item's quantity."""
    # Validate Hebrew text
    text_error = _validate_hebrew_text(params.item_name)
    if text_error:
        return {
            "status": "error",
            "message": text_error,
            "data": None
        }
    
    # Validate quantity
    quantity_error = _validate_quantity(params.quantity)
    if quantity_error:
        return {
            "status": "error",
            "message": quantity_error,
            "data": None
        }
    
    # Find the item
    locations = tool_service.item_service.get_item_locations(params.item_name)
    if not locations.success:
        # If item doesn't exist, add it
        return add_item(tool_service, AddItem(
            item_name=params.item_name,
            quantity=params.quantity,
            list_name=params.list_name
        ))
    
    if locations.data is None:
        return {
            "status": "error",
            "message": "שגיאה פנימית: לא נמצאו מיקומים",
            "data": None
        }
    
    # Handle multiple locations
    if len(locations.data) > 1 and params.list_name is None:
        result = tool_service.handle_multiple_locations(
            locations.data,
            params.item_name,
            "לעדכן"
        )
        return {
            "status": "error",
            "message": result.error,
            "suggestions": result.suggestions or []
        }
    
    # If list name specified, find matching location
    if params.list_name:
        location = next(
            (loc for loc in locations.data if loc.list_name == params.list_name),
            None
        )
        if not location:
            return {
                "status": "error",
                "message": f"לא מצאתי {params.item_name} ברשימה {params.list_name}",
                "data": None
            }
    else:
        location = locations.data[0]
    
    # Update the item
    result = tool_service.item_service.update_item(location.item_id, quantity=params.quantity)
    
    if not result.success:
        return {
            "status": "error",
            "message": result.error,
            "data": None
        }
    
    return {
        "status": "success",
        "message": f"עדכנתי את הכמות ל-{params.quantity} {params.item_name}",
        "data": {"item": result.data}
    }

@tool
def increment_quantity(tool_service: ToolService, params: IncrementQuantity) -> Dict[str, Any]:
    """Increment an item's quantity."""
    # Validate Hebrew text
    text_error = _validate_hebrew_text(params.item_name)
    if text_error:
        return {
            "status": "error",
            "message": text_error,
            "data": None
        }
    
    # Find the item
    locations = tool_service.item_service.get_item_locations(params.item_name)
    if not locations.success:
        # If item doesn't exist, add it
        return add_item(tool_service, AddItem(
            item_name=params.item_name,
            quantity=params.step,
            list_name=params.list_name
        ))
    
    if locations.data is None:
        return {
            "status": "error",
            "message": "שגיאה פנימית: לא נמצאו מיקומים",
            "data": None
        }
    
    # Handle multiple locations
    if len(locations.data) > 1 and params.list_name is None:
        result = tool_service.handle_multiple_locations(
            locations.data,
            params.item_name,
            "להוסיף"
        )
        return {
            "status": "error",
            "message": result.error,
            "suggestions": result.suggestions or []
        }
    
    # If list name specified, find matching location
    if params.list_name:
        location = next(
            (loc for loc in locations.data if loc.list_name == params.list_name),
            None
        )
        if not location:
            return {
                "status": "error",
                "message": f"לא מצאתי {params.item_name} ברשימה {params.list_name}",
                "data": None
            }
    else:
        location = locations.data[0]
    
    # Increment the item
    result = tool_service.item_service.increment_quantity(location.item_id, step=params.step)
    
    if not result.success:
        return {
            "status": "error",
            "message": result.error,
            "data": None
        }
    
    return {
        "status": "success",
        "message": f"הוספתי {params.step} {params.item_name}",
        "data": {"item": result.data}
    } 

@tool
def reduce_quantity(tool_service: ToolService, params: ReduceQuantity) -> Dict[str, Any]:
    """Reduce an item's quantity."""
    # Validate Hebrew text
    text_error = _validate_hebrew_text(params.item_name)
    if text_error:
        return {
            "status": "error",
            "message": text_error,
            "data": None
        }
    
    # Find the item
    locations = tool_service.item_service.get_item_locations(params.item_name)
    if not locations.success:
        return {
            "status": "error",
            "message": f"לא מצאתי {params.item_name} ברשימה",
            "data": None
        }
    
    if locations.data is None:
        return {
            "status": "error",
            "message": "שגיאה פנימית: לא נמצאו מיקומים",
            "data": None
        }
    
    # Handle multiple locations
    if len(locations.data) > 1 and params.list_name is None:
        result = tool_service.handle_multiple_locations(
            locations.data,
            params.item_name,
            "להוריד"
        )
        return {
            "status": "error",
            "message": result.error,
            "suggestions": result.suggestions or []
        }
    
    # If list name specified, find matching location
    if params.list_name:
        location = next(
            (loc for loc in locations.data if loc.list_name == params.list_name),
            None
        )
        if not location:
            return {
                "status": "error",
                "message": f"לא מצאתי {params.item_name} ברשימה {params.list_name}",
                "data": None
            }
    else:
        location = locations.data[0]
    
    # Reduce the item
    result = tool_service.item_service.reduce_quantity(location.item_id, step=params.step)
    
    if not result.success:
        return {
            "status": "error",
            "message": result.error,
            "data": None
        }
    
    return {
        "status": "success",
        "message": f"הורדתי {params.step} {params.item_name}",
        "data": {"item": result.data}
    }

@tool
def delete_item(tool_service: ToolService, params: DeleteItem) -> Dict[str, Any]:
    """Delete an item from a list."""
    # Validate Hebrew text
    text_error = _validate_hebrew_text(params.item_name)
    if text_error:
        return {
            "status": "error",
            "message": text_error,
            "data": None
        }
    
    # Find the item
    locations = tool_service.item_service.get_item_locations(params.item_name)
    if not locations.success:
        return {
            "status": "error",
            "message": f"לא מצאתי {params.item_name} ברשימה",
            "data": None
        }
    
    if locations.data is None:
        return {
            "status": "error",
            "message": "שגיאה פנימית: לא נמצאו מיקומים",
            "data": None
        }
    
    # Handle multiple locations
    if len(locations.data) > 1 and params.list_name is None:
        result = tool_service.handle_multiple_locations(
            locations.data,
            params.item_name,
            "למחוק"
        )
        return {
            "status": "error",
            "message": result.error,
            "suggestions": result.suggestions or []
        }
    
    # If list name specified, find matching location
    if params.list_name:
        location = next(
            (loc for loc in locations.data if loc.list_name == params.list_name),
            None
        )
        if not location:
            return {
                "status": "error",
                "message": f"לא מצאתי {params.item_name} ברשימה {params.list_name}",
                "data": None
            }
    else:
        location = locations.data[0]
    
    # Delete the item
    result = tool_service.item_service.remove_item(location.item_id)
    
    if not result.success:
        return {
            "status": "error",
            "message": result.error,
            "data": None
        }
    
    return {
        "status": "success",
        "message": f"מחקתי {params.item_name} מהרשימה",
        "data": None
    }

@tool
def mark_item_bought(tool_service: ToolService, params: MarkItemBought) -> Dict[str, Any]:
    """Mark an item as bought."""
    # Validate Hebrew text
    text_error = _validate_hebrew_text(params.item_name)
    if text_error:
        return {
            "status": "error",
            "message": text_error,
            "data": None
        }
    
    # Find the item
    locations = tool_service.item_service.get_item_locations(params.item_name, include_bought=True)
    if not locations.success:
        return {
            "status": "error",
            "message": f"לא מצאתי {params.item_name} ברשימה",
            "data": None
        }
    
    if locations.data is None:
        return {
            "status": "error",
            "message": "שגיאה פנימית: לא נמצאו מיקומים",
            "data": None
        }
    
    # Handle multiple locations
    if len(locations.data) > 1 and params.list_name is None:
        result = tool_service.handle_multiple_locations(
            locations.data,
            params.item_name,
            "לסמן כנקנה"
        )
        return {
            "status": "error",
            "message": result.error,
            "suggestions": result.suggestions or []
        }
    
    # If list name specified, find matching location
    if params.list_name:
        location = next(
            (loc for loc in locations.data if loc.list_name == params.list_name),
            None
        )
        if not location:
            return {
                "status": "error",
                "message": f"לא מצאתי {params.item_name} ברשימה {params.list_name}",
                "data": None
            }
    else:
        location = locations.data[0]
    
    # Mark as bought
    result = tool_service.item_service.mark_bought(location.item_id)
    
    if not result.success:
        return {
            "status": "error",
            "message": result.error,
            "data": None
        }
    
    return {
        "status": "success",
        "message": f"סימנתי {params.item_name} כנקנה",
        "data": {"item": result.data}
    }

@tool
def create_list(tool_service: ToolService, params: CreateList) -> Dict[str, Any]:
    """Create a new shopping list."""
    # Validate Hebrew text
    text_error = _validate_hebrew_text(params.list_name)
    if text_error:
        return {
            "status": "error",
            "message": text_error,
            "data": None
        }
    
    # Create the list
    result = tool_service.list_service.create_list(params.list_name)
    
    if not result.success:
        if "כבר קיים" in result.error:
            return {
                "status": "error",
                "message": f"רשימה בשם '{params.list_name}' כבר קיימת",
                "data": None
            }
        return {
            "status": "error",
            "message": result.error,
            "data": None
        }
    
    # Check if this is the first list (will be default)
    lists = tool_service.list_service.get_lists()
    is_first = lists.success and len(lists.data or []) == 1
    
    return {
        "status": "success",
        "message": (
            f"יצרתי רשימה חדשה: {params.list_name}" +
            (" (רשימת ברירת מחדל)" if is_first else "")
        ),
        "data": {"list": result.data}
    }

@tool
def delete_list(tool_service: ToolService, params: DeleteList) -> Dict[str, Any]:
    """Delete a shopping list."""
    # Validate Hebrew text
    text_error = _validate_hebrew_text(params.list_name)
    if text_error:
        return {
            "status": "error",
            "message": text_error,
            "data": None
        }
    
    # Find the list
    lists = tool_service.list_service.get_lists()
    if not lists.success:
        return {
            "status": "error",
            "message": lists.error,
            "data": None
        }
    
    if not lists.data:
        return {
            "status": "error",
            "message": f"לא מצאתי רשימה בשם {params.list_name}",
            "data": None
        }
    
    target_list = next(
        (l for l in lists.data if l.name == params.list_name),
        None
    )
    
    if not target_list:
        return {
            "status": "error",
            "message": f"לא מצאתי רשימה בשם {params.list_name}",
            "data": None
        }
    
    # Delete the list
    result = tool_service.list_service.delete_list(target_list.id, soft=not params.hard_delete)
    
    if not result.success:
        return {
            "status": "error",
            "message": result.error,
            "data": None
        }
    
    return {
        "status": "success",
        "message": (
            f"מחקתי את הרשימה {params.list_name}" +
            (" לצמיתות" if params.hard_delete else "")
        ),
        "data": None
    }

@tool
def show_list(tool_service: ToolService, params: ShowList) -> Dict[str, Any]:
    """Show contents of a shopping list."""
    # If list name provided, validate Hebrew text
    if params.list_name:
        text_error = _validate_hebrew_text(params.list_name)
        if text_error:
            return {
                "status": "error",
                "message": text_error,
                "data": None
            }
    
    # Get list summary first
    summaries = tool_service.list_service.list_all_user_lists()
    if not summaries.success:
        return {
            "status": "error",
            "message": summaries.error,
            "data": None
        }
    
    if not summaries.data:
        return {
            "status": "error",
            "message": "לא נמצאו רשימות",
            "suggestions": ["צור רשימה חדשה"],
            "data": None
        }
    
    target_summary = None
    if params.list_name:
        target_summary = next(
            (s for s in summaries.data if s.name == params.list_name),
            None
        )
        if not target_summary:
            return {
                "status": "error",
                "message": f"לא מצאתי רשימה בשם {params.list_name}",
                "data": None
            }
    
    # Show list contents
    result = tool_service.list_service.show_list(
        target_summary.id if target_summary else None
    )
    
    if not result.success:
        return {
            "status": "error",
            "message": result.error,
            "data": None
        }
    
    contents = result.data
    if not contents:
        return {
            "status": "error",
            "message": "שגיאה פנימית: תוכן רשימה חסר",
            "data": None
        }
    
    summary = target_summary or next(
        (s for s in summaries.data if s.id == contents.id),
        None
    )
    
    if not summary:
        return {
            "status": "error",
            "message": "שגיאה פנימית: סיכום רשימה חסר",
            "data": None
        }
    
    return {
        "status": "success",
        "message": (
            f"רשימת {contents.name}"
            f" ({summary.total_items} פריטים,"
            f" {summary.bought_items} נקנו)"
            f"{' (ברירת מחדל)' if contents.is_default else ''}"
        ),
        "data": {"contents": contents, "summary": summary}
    }

@tool
def set_default_list(tool_service: ToolService, params: SetDefaultList) -> Dict[str, Any]:
    """Set a list as the default list."""
    # Validate Hebrew text
    text_error = _validate_hebrew_text(params.list_name)
    if text_error:
        return {
            "status": "error",
            "message": text_error,
            "data": None
        }
    
    # Find the list
    lists = tool_service.list_service.get_lists()
    if not lists.success:
        return {
            "status": "error",
            "message": lists.error,
            "data": None
        }
    
    if not lists.data:
        return {
            "status": "error",
            "message": f"לא מצאתי רשימה בשם {params.list_name}",
            "data": None
        }
    
    target_list = next(
        (l for l in lists.data if l.name == params.list_name),
        None
    )
    
    if not target_list:
        return {
            "status": "error",
            "message": f"לא מצאתי רשימה בשם {params.list_name}",
            "data": None
        }
    
    # Set as default
    result = tool_service.list_service.set_default_list(target_list.id)
    
    if not result.success:
        return {
            "status": "error",
            "message": result.error,
            "data": None
        }
    
    return {
        "status": "success",
        "message": f"הגדרתי את {params.list_name} כברירת מחדל",
        "data": {"list": result.data}
    }

# List of available tools
tools = [
    add_item,
    update_item,
    increment_quantity,
    reduce_quantity,
    delete_item,
    mark_item_bought,
    create_list,
    delete_list,
    show_list,
    set_default_list
] 