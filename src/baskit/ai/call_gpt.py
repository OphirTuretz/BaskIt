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
from baskit.config.settings import get_openai_settings, get_settings
from .models import GPTConfig, GPTContext, GPTResponse, ToolCall
from .errors import APIError, ValidationError, ToolExecutionResult


class GPTHandler:
    """Handler for GPT API calls."""

    def __init__(self, config: Optional[GPTConfig] = None):
        """Initialize the handler."""
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
                'content': (
                    "אתה עוזר קניות בעברית. "
                    "תפקידך לעזור למשתמשים לנהל את רשימות הקניות שלהם. "
                    "השתמש בכלים שסופקו לך כדי לבצע פעולות."
                )
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
                    'description': 'הוסף פריט לרשימת קניות',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'name': {
                                'type': 'string',
                                'description': 'שם הפריט בעברית'
                            },
                            'quantity': {
                                'type': 'integer',
                                'description': 'כמות הפריט',
                                'default': 1
                            },
                            'unit': {
                                'type': 'string',
                                'description': 'יחידת המידה',
                                'default': 'יחידה'
                            },
                            'list_name': {
                                'type': 'string',
                                'description': 'שם הרשימה (אופציונלי)',
                                'optional': True
                            }
                        },
                        'required': ['name']
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
                    arguments = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError as e:
                    self.logger.error(
                        "Failed to parse tool arguments",
                        arguments=tool_call.function.arguments,
                        error=str(e)
                    )
                    continue
                
                tool_calls.append(ToolCall(
                    name=tool_call.function.name,
                    arguments=arguments
                ))
            
            # Calculate confidence based on temperature
            confidence = 1.0 - (self.config.temperature * 0.5)
            
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
                                    'name': item_name,
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