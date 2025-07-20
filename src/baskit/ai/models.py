"""Models for GPT integration."""
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, field_validator

from baskit.domain.types import HebrewText


class GPTConfig(BaseModel):
    """Configuration for GPT calls."""
    model: str = "gpt-4"
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    max_retries: int = Field(default=3, ge=1, le=5)
    timeout: int = Field(default=10, ge=5, le=30)
    
    @field_validator('model')
    @classmethod
    def validate_model(cls, v: str) -> str:
        allowed_models = ['gpt-4', 'gpt-3.5-turbo']
        if v not in allowed_models:
            raise ValueError(f"מודל חייב להיות אחד מ: {', '.join(allowed_models)}")
        return v


class GPTContext(BaseModel):
    """Conversation context."""
    messages: List[Dict[str, str]]
    current_list: Optional[HebrewText] = None
    last_item: Optional[HebrewText] = None
    
    @field_validator('messages')
    @classmethod
    def validate_messages(cls, v: List[Dict[str, str]]) -> List[Dict[str, str]]:
        if not v:
            raise ValueError("הקשר השיחה לא יכול להיות ריק")
        
        required_keys = {'role', 'content'}
        allowed_roles = {'user', 'assistant', 'system'}
        
        for msg in v:
            if not all(key in msg for key in required_keys):
                raise ValueError("כל הודעה חייבת להכיל role ו-content")
            if msg['role'] not in allowed_roles:
                raise ValueError(f"role חייב להיות אחד מ: {', '.join(allowed_roles)}")
            if not msg['content'].strip():
                raise ValueError("content לא יכול להיות ריק")
        
        return v


class ToolCall(BaseModel):
    """Represents a tool call from GPT."""
    name: str
    arguments: Dict[str, Any]
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        allowed_tools = {
            'add_item', 'remove_item', 'update_quantity',
            'mark_bought', 'create_list', 'show_list'
        }
        if v not in allowed_tools:
            raise ValueError(f"שם הכלי חייב להיות אחד מ: {', '.join(allowed_tools)}")
        return v


class GPTResponse(BaseModel):
    """Response from GPT including tool calls."""
    tool_calls: List[ToolCall]
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    
    @field_validator('tool_calls')
    @classmethod
    def validate_tool_calls(cls, v: List[ToolCall]) -> List[ToolCall]:
        if not v:
            raise ValueError("תשובת GPT חייבת לכלול לפחות קריאה אחת לכלי")
        return v 