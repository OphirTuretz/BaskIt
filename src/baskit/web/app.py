"""Main Streamlit application for BaskIt."""
import asyncio
import uuid
import streamlit as st
from typing import Optional, Dict, Any, cast

from baskit.services.list_service import ListService
from baskit.services.item_service import ItemService
from baskit.db.session import get_session
from baskit.web.components import (
    render_sidebar,
    render_list_display,
    render_add_item,
    render_feedback
)
from baskit.ai.call_gpt import GPTHandler
from baskit.ai.models import GPTContext
from baskit.utils.logger import get_logger
from baskit.domain.types import HebrewText
from baskit.ai.errors import ToolExecutionResult
from baskit.ai.handlers import ToolExecutor

# Initialize logger
logger = get_logger(__name__)

def init_session_state() -> None:
    """Initialize session state variables."""
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
        logger.info("New session started", extra={'session_id': st.session_state.session_id})
    
    if 'db_session' not in st.session_state:
        st.session_state.db_session = get_session()
    
    if 'ui_mode' not in st.session_state:
        st.session_state.ui_mode = 'smart'
    
    if 'smart_input' not in st.session_state:
        st.session_state.smart_input = ''

def render_mode_selector() -> str:
    """Render mode selection radio buttons."""
    selected_mode = st.radio(
        "בחר מצב שימוש:",
        options=['smart', 'manual'],
        format_func=lambda x: "🔮 מצב חכם (שפה חופשית)" if x == 'smart' else "🛠 מצב ידני",
        horizontal=True,
        key='ui_mode',
        index=0
    )
    
    # Log mode changes
    if selected_mode != st.session_state.get('previous_mode'):
        logger.info(
            "UI mode changed",
            extra={
                'session_id': st.session_state.session_id,
                'new_mode': selected_mode,
                'previous_mode': st.session_state.get('previous_mode')
            }
        )
        st.session_state.previous_mode = selected_mode
    
    # Cast to str since we know the radio options are strings
    return cast(str, selected_mode)

async def process_smart_input(
    user_input: str,
    current_list: Optional[str],
    gpt_handler: GPTHandler,
    item_service: ItemService,
    list_service: ListService,
    tool_executor: Optional[ToolExecutor] = None
) -> ToolExecutionResult:
    """Process smart mode input and handle results.
    
    Args:
        user_input: User's text input
        current_list: Current list name or None
        gpt_handler: GPT handler instance
        item_service: Service for managing items
        list_service: Service for managing lists
        tool_executor: Optional tool executor instance (for testing)
        
    Returns:
        ToolExecutionResult: The result of processing the input
    """
    # Add correlation ID for tracking this request
    correlation_id = str(uuid.uuid4())
    logger.info(
        "Processing smart input",
        extra={
            'correlation_id': correlation_id,
            'session_id': st.session_state.session_id,
            'list_name': current_list,
            'input_length': len(user_input),
            'input': user_input  # Log the actual input for debugging
        }
    )
    
    try:
        # Convert current_list to HebrewText if not None
        hebrew_list = HebrewText(current_list) if current_list else None
        
        # Create context with required messages
        messages = [
            {
                'role': 'system',
                'content': (
                    "אתה עוזר קניות בעברית. "
                    "תפקידך לעזור למשתמשים לנהל את רשימות הקניות שלהם. "
                    "השתמש בכלים שסופקו לך כדי לבצע פעולות."
                )
            }
        ]
        
        # Add list context if available
        if hebrew_list:
            messages.append({
                'role': 'system',
                'content': f"הרשימה הנוכחית היא: {hebrew_list}"
            })
        
        # Add user message
        messages.append({
            'role': 'user',
            'content': user_input
        })
        
        context = GPTContext(
            current_list=hebrew_list,
            messages=messages,
            last_item=None
        )
        
        # Get tool calls from GPT
        gpt_result = await gpt_handler.call_with_tools(user_input, context)
        
        logger.info(
            "GPT response received",
            extra={
                'correlation_id': correlation_id,
                'session_id': st.session_state.session_id,
                'success': gpt_result.success,
                'has_tool_calls': bool(gpt_result.data and gpt_result.data.get('tool_calls')),
                'tool_calls_count': len(gpt_result.data.get('tool_calls', [])) if gpt_result.data else 0
            }
        )
        
        if not gpt_result.success:
            logger.warning(
                "GPT call failed",
                extra={
                    'correlation_id': correlation_id,
                    'error': gpt_result.error,
                    'has_suggestions': bool(gpt_result.suggestions)
                }
            )
            st.error(gpt_result.error)
            if gpt_result.suggestions:
                with st.expander("הצעות לתיקון"):
                    for suggestion in gpt_result.suggestions:
                        st.write(f"• {suggestion}")
            return gpt_result
            
        # Create tool executor if not provided
        if tool_executor is None:
            tool_executor = ToolExecutor(
                item_service=item_service,
                list_service=list_service
            )
        
        # Execute each tool call
        results = []
        for tool_call in gpt_result.data['tool_calls']:
            logger.info(
                "Executing tool call",
                extra={
                    'correlation_id': correlation_id,
                    'tool': tool_call['name'],
                    'arguments': tool_call['arguments']
                }
            )
            
            result = await tool_executor.execute(tool_call, context)
            results.append(result)
            
            # Log result
            logger.info(
                "Tool execution completed",
                extra={
                    'correlation_id': correlation_id,
                    'tool': tool_call['name'],
                    'success': result.success,
                    'has_error': bool(result.error),
                    'has_suggestions': bool(result.suggestions),
                    'data': result.data
                }
            )
            
            # Show feedback
            if result.success:
                success_msg = result.message or "הפעולה הושלמה בהצלחה"
                st.success(success_msg)
                logger.info(
                    "Tool execution success",
                    extra={
                        'correlation_id': correlation_id,
                        'message': success_msg
                    }
                )
            else:
                st.error(result.error)
                if result.suggestions:
                    with st.expander("הצעות לתיקון"):
                        for suggestion in result.suggestions:
                            st.write(f"• {suggestion}")
                logger.warning(
                    "Tool execution failed",
                    extra={
                        'correlation_id': correlation_id,
                        'error': result.error,
                        'suggestions': result.suggestions
                    }
                )
            
            # Stop on first error
            if not result.success:
                return result
        
        # Return success if all tools executed successfully
        final_result = ToolExecutionResult(
            success=True,
            message=gpt_result.message,  # Use GPT's message instead of generic one
            data={'results': results}
        )
        
        logger.info(
            "Smart input processing completed",
            extra={
                'correlation_id': correlation_id,
                'success': True,
                'results_count': len(results)
            }
        )
        
        return final_result
                
    except Exception as e:
        logger.exception(
            "Smart input processing failed",
            extra={
                'correlation_id': correlation_id,
                'session_id': st.session_state.session_id,
                'error_type': type(e).__name__,
                'error': str(e)
            }
        )
        error_result = ToolExecutionResult(
            success=False,
            message=f"שגיאה בעיבוד הבקשה: {str(e)}",
            suggestions=["נסה שוב או עבור למצב ידני"]
        )
        st.error(error_result.message)
        st.info(error_result.suggestions[0])
        return error_result

async def render_smart_input(
    list_service: ListService,
    item_service: ItemService,
    selected_list_id: int
) -> None:
    """Render smart mode input interface."""
    logger.debug(
        "Rendering smart input interface",
        extra={'session_id': st.session_state.session_id}
    )
    
    # Get current list context
    current_list = None
    list_result = list_service.show_list(selected_list_id)
    if list_result.success and list_result.data:
        current_list = list_result.data.name
    
    st.write("---")
    st.markdown("### הוסף פריטים בטקסט חופשי")
    
    # Handle form submission from previous interaction
    if 'smart_input_submitted' in st.session_state and st.session_state.smart_input_submitted:
        st.session_state.smart_input = ""  # Clear input before rendering
        st.session_state.smart_input_submitted = False
    
    with st.form("smart_input_form", clear_on_submit=False):
        col1, col2, col3 = st.columns([6, 2, 0.5])
        
        with col1:
            user_input = st.text_input(
                "",
                placeholder="הקלד טקסט חופשי בעברית (למשל: 'טופו', 'קניתי עגבניות', 'תמחק עגבניות')",
                key="smart_input"
            )
        
        with col2:
            submit = st.form_submit_button(
                "✨ עבד טקסט",
                use_container_width=True,
                type="primary"
            )

    if submit and user_input:
        logger.info(
            "Smart input submitted",
            extra={
                'session_id': st.session_state.session_id,
                'input_length': len(user_input),
                'input': user_input
            }
        )
        with st.spinner("מעבד את הבקשה..."):
            gpt_handler = GPTHandler()
            result = await process_smart_input(
                user_input, 
                current_list, 
                gpt_handler,
                item_service,
                list_service
            )
            if result.success:
                logger.info(
                    "Smart input processing succeeded, triggering UI refresh",
                    extra={
                        'session_id': st.session_state.session_id,
                        'input': user_input
                    }
                )
                st.session_state.smart_input_submitted = True  # Mark for clearing on next render
                st.experimental_rerun()  # Rerun to refresh the list display
            else:
                logger.warning(
                    "Smart input processing failed",
                    extra={
                        'session_id': st.session_state.session_id,
                        'input': user_input,
                        'error': result.error
                    }
                )

async def main() -> None:
    """Main application entry point."""
    logger.info(
        "Starting BaskIt application",
        extra={'session_id': st.session_state.get('session_id', 'init')}
    )
    
    try:
        # Configure page
        st.set_page_config(
            layout="wide",
            page_title="BaskIt",
            page_icon="🧺",
            initial_sidebar_state="expanded"
        )
        
        # Set RTL and Hebrew font CSS
        st.markdown(
            """
            <style>
            .stApp {
                direction: rtl;
                font-family: 'Heebo', sans-serif;
            }
            .stButton button {
                width: 100%;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            .stRadio > label {
                font-size: 1.2em;
                margin-bottom: 1em;
            }
            .stTextInput {
                margin-bottom: 1em;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        
        # Initialize session state
        init_session_state()
        
        # TODO: Replace with actual user ID from auth
        USER_ID = 1
        
        # Initialize services
        list_service = ListService(st.session_state.db_session, USER_ID)
        item_service = ItemService(st.session_state.db_session, USER_ID)
        
        # Initialize selected list
        if 'selected_list_id' not in st.session_state:
            logger.info(
                "Initializing default list",
                extra={'session_id': st.session_state.session_id}
            )
            default_list = list_service.get_default_list()
            st.session_state.selected_list_id = (
                default_list.data.id if default_list.success and default_list.data
                else None
            )
        
        # Render sidebar and get selected list
        selected_list_id = render_sidebar(list_service)
        if selected_list_id is not None:
            if selected_list_id != st.session_state.selected_list_id:
                logger.info(
                    "Selected list changed",
                    extra={
                        'session_id': st.session_state.session_id,
                        'new_list_id': selected_list_id
                    }
                )
            st.session_state.selected_list_id = selected_list_id
        
        # Render mode selector
        st.markdown("## בחר מצב שימוש")
        selected_mode = render_mode_selector()
        
        # Render main content if list is selected
        if st.session_state.selected_list_id:
            if selected_mode == 'smart':
                logger.debug(
                    "Rendering smart mode interface",
                    extra={'session_id': st.session_state.session_id}
                )
                st.markdown("## הרשימה שלי")
                render_list_display(
                    list_service,
                    item_service,
                    st.session_state.selected_list_id
                )
                
                await render_smart_input(
                    list_service,
                    item_service,
                    st.session_state.selected_list_id
                )
            else:
                logger.debug(
                    "Rendering manual mode interface",
                    extra={'session_id': st.session_state.session_id}
                )
                st.markdown("## הרשימה שלי")
                col1, col2 = st.columns([2, 1])
                with col1:
                    render_list_display(
                        list_service,
                        item_service,
                        st.session_state.selected_list_id
                    )
                with col2:
                    render_add_item(
                        item_service,
                        st.session_state.selected_list_id
                    )
        else:
            logger.info(
                "No list selected",
                extra={'session_id': st.session_state.session_id}
            )
            st.info("בחר רשימה מהתפריט או צור רשימה חדשה")
            
    except Exception as e:
        logger.exception(
            "Unhandled error in main application",
            extra={'session_id': st.session_state.get('session_id', 'error')}
        )
        st.error("שגיאה במערכת. אנא נסה שוב מאוחר יותר.")

if __name__ == "__main__":
    asyncio.run(main()) 