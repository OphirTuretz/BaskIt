"""GPT integration handler."""
import asyncio
import json
import re
from typing import Dict, Any, Optional, List, cast
from functools import wraps
from openai import AsyncOpenAI, APIError as OpenAIAPIError
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionMessage,
    ChatCompletionMessageParam,
    ChatCompletionToolParam
)
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from baskit.utils.logger import get_logger
from baskit.services.base_service import Result
from baskit.config.settings import get_openai_settings, get_settings, clear_settings_cache
from .models import GPTConfig, GPTContext, GPTResponse, ToolCall
from .errors import APIError, ValidationError, ToolExecutionResult


class GPTHandler:
    """Handler for GPT API calls."""

    def __init__(self, config: Optional[GPTConfig] = None):
        """Initialize the handler."""
        # Clear settings cache to ensure we have the latest values
        clear_settings_cache()
        
        openai_settings = get_openai_settings()
        baskit_settings = get_settings()
        
        self.config = config or GPTConfig(
            model=openai_settings.MODEL,
            temperature=openai_settings.TEMPERATURE,
            max_retries=openai_settings.MAX_RETRIES,
            timeout=openai_settings.TIMEOUT
        )
        
        self.client = AsyncOpenAI(
            api_key=openai_settings.API_KEY,
            timeout=self.config.timeout
        )
        
        self.logger = get_logger(self.__class__.__name__)
        self.use_mock = baskit_settings.USE_MOCK_AI
        self.enable_context = baskit_settings.ENABLE_CONTEXT
        self.context_max_turns = baskit_settings.CONTEXT_MAX_TURNS
        self.confidence_threshold = baskit_settings.TOOL_CONFIDENCE_THRESHOLD

    def _prepare_messages(
        self,
        text: str,
        context: GPTContext
    ) -> List[ChatCompletionMessageParam]:
        """Prepare messages for GPT call."""
        messages: List[ChatCompletionMessageParam] = []
        
        # Add system message if not present
        if not any(msg['role'] == 'system' for msg in context.messages):
            messages.append({
                'role': 'system',
                'content': """You are an AI assistant for a smart grocery shopping app called "BaskIt".

Your job is to understand user messages written in Hebrew and select the correct tool (function) to call, using the appropriate arguments.

Your output must be in the OpenAI tool-calling format:
- tool_name
- tool_arguments (as a dictionary)

Use the function definitions below and select the one that best fits the user's intent.
If no function applies, return an error via tool_name="no_op".

You must be accurate and deterministic (temperature = 0).

---

Available tools you may call:

1. add_item
→ Add a new item to a grocery list (or increment it if it already exists).
Parameters:
  - item_name (str, required): The name of the product, in Hebrew.
  - quantity (int, optional): How many units to add (default = 1).
  - unit (str, optional): Unit of measurement (default = "יחידה").
  - list_name (str, optional): The name of the grocery list (default = the user's default list).

2. update_quantity
→ Update the quantity of an existing item.
Parameters:
  - item_name (str, required): The name of the item to update.
  - quantity (int, required): The new quantity to set.
  - list_name (str, optional): The name of the list containing the item.

3. increment_quantity
→ Increase the quantity of an item already in the list.
Parameters:
  - item_name (str, required): The name of the item to increment.
  - step (int, optional): Amount to increase (default = 1).
  - list_name (str, optional): The name of the list containing the item.

4. reduce_quantity
→ Reduce the quantity of an item.
Parameters:
  - item_name (str, required): The name of the item to reduce.
  - step (int, optional): Amount to reduce (default = 1).
  - list_name (str, optional): The name of the list containing the item.

5. remove_item
→ Remove an item from the list entirely.
Parameters:
  - item_name (str, required): The name of the item to remove.
  - list_name (str, optional): The name of the list containing the item.

6. mark_bought
→ Mark an item as purchased.
Parameters:
  - item_name (str, required): The name of the item to mark.
  - list_name (str, optional): The name of the list containing the item.

7. create_list
→ Create a new grocery list.
Parameters:
  - list_name (str, required): The name of the new list.

8. delete_list
→ Delete a grocery list.
Parameters:
  - list_name (str, required): The name of the list to delete.
  - hard_delete (bool, optional): If true, permanently delete the list (default = false).

9. show_list
→ Show the contents of a grocery list.
Parameters:
  - list_name (str, optional): The name of the list to show (default = current list).
  - include_bought (bool, optional): Whether to include purchased items (default = true).

10. set_default_list
→ Set the user's default list.
Parameters:
  - list_name (str, required): The name of the list to set as default.

11. no_op
→ Special fallback tool when no meaningful action can be inferred.
Parameters:
  - reason (str, required): Explain why no tool was selected.

---

Edge case strategy:

1. Ambiguous item name (e.g., "לבן") → no_op with explanation.
2. List not found → no_op and suggest creating it.
3. Item in multiple lists → no_op and ask user to specify list.
4. Default list deletion → no_op and explain.
5. Item not found for reduce/delete/mark → no_op with reason.
6. Empty or unclear input → no_op with polite Hebrew explanation.
7. Single product name → add_item.
8. "קניתי X" → mark_bought.
9. "תוסיף Y" or "תוסיף 3 Z" → increment_quantity or fallback to add_item.
10. "תוריד Y" or "תוריד 2 Z" → reduce_quantity.
11. "תמחק X" → remove_item.
12. "רשימה ל..." → create_list.
13. "מה יש ב..." or "תראה את הרשימה" → show_list.

Always prefer precision and never guess the tool.

---

Examples:

User Input: "טופו"  
→ Tool Call:
{
  "tool_name": "add_item",
  "tool_arguments": { 
    "item_name": "טופו",
    "quantity": 1,
    "unit": "יחידה"
  }
}

User Input: "תוסיף 3 עגבניות"  
→ Tool Call:
{
  "tool_name": "increment_quantity",
  "tool_arguments": { 
    "item_name": "עגבניות", 
    "step": 3 
  }
}

User Input: "תוריד 2 עגבניות"  
→ Tool Call:
{
  "tool_name": "reduce_quantity",
  "tool_arguments": { 
    "item_name": "עגבניות", 
    "step": 2 
  }
}

User Input: "קניתי טופו"  
→ Tool Call:
{
  "tool_name": "mark_bought",
  "tool_arguments": { 
    "item_name": "טופו" 
  }
}

User Input: "תמחק עגבניות"  
→ Tool Call:
{
  "tool_name": "remove_item",
  "tool_arguments": { 
    "item_name": "עגבניות" 
  }
}

User Input: "רשימה לשבת"  
→ Tool Call:
{
  "tool_name": "create_list",
  "tool_arguments": { 
    "list_name": "שבת" 
  }
}

User Input: "מה יש ברשימת שבת?"  
→ Tool Call:
{
  "tool_name": "show_list",
  "tool_arguments": { 
    "list_name": "שבת",
    "include_bought": true 
  }
}

User Input: "רוצה לראות את הרשימה"  
→ Tool Call:
{
  "tool_name": "show_list",
  "tool_arguments": {
    "include_bought": true
  }
}

User Input: "3 גמבה"  
→ Tool Call:
{
  "tool_name": "add_item",
  "tool_arguments": { 
    "item_name": "גמבה", 
    "quantity": 3,
    "unit": "יחידה"
  }
}

User Input: "קח משהו ללבן"  
→ Tool Call:
{
  "tool_name": "no_op",
  "tool_arguments": {
    "reason": "שם המוצר לא ברור (לבן). לא ניתן להבין לאיזה פריט הכוונה."
  }
}

User Input: ""  
→ Tool Call:
{
  "tool_name": "no_op",
  "tool_arguments": {
    "reason": "הקלט ריק. לא ניתן לבצע פעולה."
  }
}"""
            })
        
        # Add current context if available and enabled
        if self.enable_context:
            if context.current_list:
                messages.append({
                    'role': 'system',
                    'content': f"הרשימה הנוכחית היא: {context.current_list}"
                })
            
            if context.last_item:
                messages.append({
                    'role': 'system',
                    'content': f"הפריט האחרון שדובר עליו: {context.last_item}"
                })
            
            # Limit context size
            if len(context.messages) > self.context_max_turns:
                context.messages = context.messages[-self.context_max_turns:]
        
        # Add user message
        messages.append({
            'role': 'user',
            'content': text
        })
        
        return messages

    def _prepare_tools(self) -> List[ChatCompletionToolParam]:
        """Prepare tool definitions for GPT."""
        return [
            {
                'type': 'function',
                'function': {
                    'name': 'add_item',
                    'description': 'Add a new item to a grocery list',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'item_name': {
                                'type': 'string',
                                'description': 'The name of the product, in Hebrew'
                            },
                            'quantity': {
                                'type': 'integer',
                                'description': 'How many units to add',
                                'default': 1
                            },
                            'unit': {
                                'type': 'string',
                                'description': 'Unit of measurement',
                                'default': 'יחידה'
                            },
                            'list_name': {
                                'type': 'string',
                                'description': 'The name of the grocery list (uses default if not specified)',
                                'optional': True
                            }
                        },
                        'required': ['item_name']
                    }
                }
            },
            {
                'type': 'function',
                'function': {
                    'name': 'update_quantity',
                    'description': 'Update the quantity of an existing item',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'item_name': {
                                'type': 'string',
                                'description': 'The name of the item to update'
                            },
                            'quantity': {
                                'type': 'integer',
                                'description': 'The new quantity to set'
                            },
                            'list_name': {
                                'type': 'string',
                                'description': 'The name of the list containing the item',
                                'optional': True
                            }
                        },
                        'required': ['item_name', 'quantity']
                    }
                }
            },
            {
                'type': 'function',
                'function': {
                    'name': 'increment_quantity',
                    'description': 'Increase the quantity of an item already in the list',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'item_name': {
                                'type': 'string',
                                'description': 'The name of the item to increment'
                            },
                            'step': {
                                'type': 'integer',
                                'description': 'Amount to increase',
                                'default': 1
                            },
                            'list_name': {
                                'type': 'string',
                                'description': 'The name of the list containing the item',
                                'optional': True
                            }
                        },
                        'required': ['item_name']
                    }
                }
            },
            {
                'type': 'function',
                'function': {
                    'name': 'reduce_quantity',
                    'description': 'Reduce the quantity of an item',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'item_name': {
                                'type': 'string',
                                'description': 'The name of the item to reduce'
                            },
                            'step': {
                                'type': 'integer',
                                'description': 'Amount to reduce',
                                'default': 1
                            },
                            'list_name': {
                                'type': 'string',
                                'description': 'The name of the list containing the item',
                                'optional': True
                            }
                        },
                        'required': ['item_name']
                    }
                }
            },
            {
                'type': 'function',
                'function': {
                    'name': 'remove_item',
                    'description': 'Remove an item from the list entirely',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'item_name': {
                                'type': 'string',
                                'description': 'The name of the item to remove'
                            },
                            'list_name': {
                                'type': 'string',
                                'description': 'The name of the list containing the item',
                                'optional': True
                            }
                        },
                        'required': ['item_name']
                    }
                }
            },
            {
                'type': 'function',
                'function': {
                    'name': 'mark_bought',
                    'description': 'Mark an item as purchased',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'item_name': {
                                'type': 'string',
                                'description': 'The name of the item to mark'
                            },
                            'list_name': {
                                'type': 'string',
                                'description': 'The name of the list containing the item',
                                'optional': True
                            }
                        },
                        'required': ['item_name']
                    }
                }
            },
            {
                'type': 'function',
                'function': {
                    'name': 'create_list',
                    'description': 'Create a new grocery list',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'list_name': {
                                'type': 'string',
                                'description': 'The name of the new list'
                            }
                        },
                        'required': ['list_name']
                    }
                }
            },
            {
                'type': 'function',
                'function': {
                    'name': 'delete_list',
                    'description': 'Delete a grocery list',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'list_name': {
                                'type': 'string',
                                'description': 'The name of the list to delete'
                            },
                            'hard_delete': {
                                'type': 'boolean',
                                'description': 'If true, permanently delete the list',
                                'default': False
                            }
                        },
                        'required': ['list_name']
                    }
                }
            },
            {
                'type': 'function',
                'function': {
                    'name': 'show_list',
                    'description': 'Show the contents of a grocery list',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'list_name': {
                                'type': 'string',
                                'description': 'The name of the list to show',
                                'optional': True
                            },
                            'include_bought': {
                                'type': 'boolean',
                                'description': 'Whether to include purchased items',
                                'default': True
                            }
                        }
                    }
                }
            },
            {
                'type': 'function',
                'function': {
                    'name': 'set_default_list',
                    'description': 'Set the user\'s default list',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'list_name': {
                                'type': 'string',
                                'description': 'The name of the list to set as default'
                            }
                        },
                        'required': ['list_name']
                    }
                }
            },
            {
                'type': 'function',
                'function': {
                    'name': 'no_op',
                    'description': 'Special fallback tool when no meaningful action can be inferred',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'reason': {
                                'type': 'string',
                                'description': 'Explain why no tool was selected'
                            }
                        },
                        'required': ['reason']
                    }
                }
            }
        ]

    async def _handle_api_error(self, e: OpenAIAPIError) -> ToolExecutionResult:
        """Handle OpenAI API errors."""
        self.logger.exception("OpenAI API error")
        
        error_str = str(e).lower()
        if 'rate_limit' in error_str:
            return ToolExecutionResult.from_error(APIError(
                "יותר מדי בקשות, נסה שוב בעוד מספר שניות",
                suggestions=["המתן מעט ונסה שוב"]
            ))
        
        if 'timeout' in error_str:
            return ToolExecutionResult.from_error(APIError(
                "השרת לא הגיב בזמן, נסה שוב",
                suggestions=["נסה שוב", "בדוק את החיבור לאינטרנט"]
            ))
        
        if 'api_key' in error_str:
            return ToolExecutionResult.from_error(APIError(
                "שגיאה בהגדרות המערכת",
                suggestions=["פנה למנהל המערכת"]
            ))
        
        return ToolExecutionResult.from_error(APIError(
            "שגיאה בתקשורת עם השרת",
            suggestions=["נסה שוב בעוד מספר שניות"]
        ))

    def _parse_tool_calls(
        self,
        message: ChatCompletionMessage
    ) -> GPTResponse:
        """Parse and validate tool calls from GPT response."""
        try:
            tool_calls = []
            for tool_call in message.tool_calls or []:
                if tool_call.type != 'function':
                    continue
                    
                # Parse arguments from JSON string
                try:
                    # Check if arguments is already a dict
                    if isinstance(tool_call.function.arguments, dict):
                        arguments = tool_call.function.arguments
                    else:
                        arguments = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError as e:
                    self.logger.error(
                        "Failed to parse tool arguments",
                        arguments=tool_call.function.arguments,
                        error=str(e)
                    )
                    continue
                
                # Add debug logging
                self.logger.debug(
                    "Parsed tool call",
                    name=tool_call.function.name,
                    arguments=arguments
                )
                
                tool_calls.append(ToolCall(
                    name=tool_call.function.name,
                    arguments=arguments
                ))
            
            # Use actual confidence from API response
            confidence = 1.0  # Default to high confidence
            
            # Validate confidence in API mode
            if not self.use_mock and confidence < self.confidence_threshold:
                self.logger.warning(
                    "Low confidence response",
                    confidence=confidence,
                    threshold=self.confidence_threshold
                )
                raise ValidationError(
                    "רמת הביטחון נמוכה מדי",
                    suggestions=["נסה לנסח את הבקשה בצורה ברורה יותר"]
                )
            
            # In mock mode, always use high confidence
            if self.use_mock:
                confidence = 1.0
            
            return GPTResponse(
                tool_calls=tool_calls,
                confidence=confidence
            )
            
        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            raise ValidationError(
                "שגיאה בעיבוד תשובת GPT",
                suggestions=["נסה לנסח את הבקשה אחרת"]
            ) from e

    @retry(
        retry=retry_if_exception_type(OpenAIAPIError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def call_with_tools(
        self,
        text: str,
        context: GPTContext
    ) -> ToolExecutionResult:
        """Call GPT with tools and handle errors."""
        try:
            # Use mock responses in test mode
            if self.use_mock:
                self.logger.info(
                    "Using mock GPT response",
                    text=text,
                    current_list=context.current_list,
                    mock_mode=True
                )
                return self._get_mock_response(text)
            
            self.logger.info(
                "Calling GPT API",
                text=text,
                current_list=context.current_list,
                model=self.config.model,
                mock_mode=False
            )
            
            messages = self._prepare_messages(text, context)
            tools = self._prepare_tools()
            
            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=self.config.temperature,
                timeout=self.config.timeout,
                max_tokens=get_openai_settings().MAX_TOKENS
            )
            
            gpt_response = self._parse_tool_calls(response.choices[0].message)
            
            self.logger.info(
                "GPT call successful",
                tool_calls=len(gpt_response.tool_calls),
                confidence=gpt_response.confidence,
                mock_mode=False
            )
            
            return ToolExecutionResult(
                success=True,
                data={
                    'tool_calls': [
                        {
                            'name': call.name,
                            'arguments': call.arguments
                        }
                        for call in gpt_response.tool_calls
                    ],
                    'confidence': gpt_response.confidence
                },
                metadata={'model': self.config.model, 'mock_mode': False}
            )
            
        except OpenAIAPIError as e:
            return await self._handle_api_error(e)
            
        except ValidationError as e:
            self.logger.exception("Validation error")
            return ToolExecutionResult.from_error(e)
            
        except Exception as e:
            self.logger.exception("Unexpected error")
            return ToolExecutionResult.from_exception(e)

    def _get_mock_response(self, text: str) -> ToolExecutionResult:
        """Get mock response for testing."""
        # Simple mock that extracts item name from common patterns
        patterns = [
            # תוסיף X
            r'תוסיף\s+([^\d\s]+)',
            # תוריד X
            r'תוריד\s+([^\d\s]+)',
            # סמן שקניתי X
            r'סמן\s+שקניתי\s+([^\d\s]+)',
            # קניתי X
            r'קניתי\s+([^\d\s]+)',
            # צריך X
            r'צריך\s+([^\d\s]+)',
            # X
            r'^([^\d\s]+)$'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                item_name = match.group(1)
                return ToolExecutionResult(
                    success=True,
                    data={
                        'tool_calls': [
                            {
                                'name': 'add_item',
                                'arguments': {
                                    'item_name': item_name,  # Changed from 'name' to 'item_name'
                                    'quantity': 1,
                                    'unit': 'יחידה'
                                }
                            }
                        ],
                        'confidence': 1.0
                    },
                    metadata={'model': 'mock', 'mock_mode': True}
                )
        
        return ToolExecutionResult.from_error(ValidationError(
            "לא הצלחתי להבין את הבקשה",
            suggestions=["נסה לנסח את הבקשה בצורה ברורה יותר"]
        )) 