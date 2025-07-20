"""Domain types for BaskIt."""
from typing import NewType, Optional, List, Any, Annotated
from datetime import datetime
from pydantic import BaseModel, constr, conint, Field, field_validator
from pydantic_core import CoreSchema, core_schema


# Strong types for IDs
UserId = NewType('UserId', int)
ListId = NewType('ListId', int)
ItemId = NewType('ItemId', int)


class HebrewText(str):
    """String subclass that validates text is primarily Hebrew."""
    
    def __new__(cls, value: str) -> 'HebrewText':
        """Create a new HebrewText instance with validation."""
        if not isinstance(value, str):
            raise TypeError('חייב להיות טקסט')
        if not value or not value.strip():
            raise ValueError('טקסט לא יכול להיות ריק')
        
        # Calculate ratio of Hebrew characters
        text = value.strip()
        
        # Count Hebrew characters and spaces
        hebrew_chars = sum(1 for c in text if '\u0590' <= c <= '\u05FF')
        spaces = sum(1 for c in text if c.isspace())
        
        # Calculate ratio excluding spaces
        text_length = len(text) - spaces
        if text_length == 0:
            raise ValueError('טקסט לא יכול להיות ריק')
        
        if hebrew_chars == 0 or hebrew_chars / text_length < 0.7:
            raise ValueError('טקסט חייב להיות בעיקר בעברית')
            
        return super().__new__(cls, text)
    
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: Any
    ) -> CoreSchema:
        """Get Pydantic core schema for validation."""
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.union_schema([
                core_schema.is_instance_schema(cls),
                core_schema.no_info_plain_validator_function(cls)
            ]),
            serialization=core_schema.plain_serializer_function_ser_schema(str)
        )


class Quantity(BaseModel):
    """Represents a quantity with an optional unit."""
    value: Annotated[int, Field(ge=0, le=99)]
    unit: Annotated[str, Field(min_length=1, max_length=20)] = "יחידה"

    @field_validator('value')
    @classmethod
    def value_must_be_positive(cls, v: int) -> int:
        """Validate that quantity is positive."""
        if v < 0:
            raise ValueError('כמות חייבת להיות חיובית')
        return v


class Item(BaseModel):
    """Represents a grocery item."""
    id: Optional[ItemId] = None
    name: HebrewText
    quantity: Quantity
    is_bought: bool = False
    bought_at: Optional[datetime] = None
    
    @field_validator('name')
    @classmethod
    def name_must_be_hebrew(cls, v: str) -> HebrewText:
        """Validate that name is Hebrew text."""
        return HebrewText(v)

class GroceryList(BaseModel):
    """Represents a grocery list."""
    id: Optional[ListId] = None
    name: HebrewText
    is_default: bool = False
    items: List[Item] = []

# Command Models
class AddItemCommand(BaseModel):
    """Command for adding an item to a list."""
    name: HebrewText
    quantity: Quantity = Field(default_factory=lambda: Quantity(value=1))
    list_name: Optional[HebrewText] = None

class UpdateQuantityCommand(BaseModel):
    """Command for updating an item's quantity."""
    item_id: ItemId
    new_quantity: Quantity
    list_id: Optional[ListId] = None

# Event Models
class ItemEvent(BaseModel):
    """Base class for item-related events."""
    item_id: ItemId
    list_id: ListId
    user_id: UserId
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ItemAddedEvent(ItemEvent):
    """Event emitted when an item is added."""
    name: HebrewText
    quantity: Quantity

class QuantityChangedEvent(ItemEvent):
    """Event emitted when an item's quantity changes."""
    old_quantity: Quantity
    new_quantity: Quantity 