"""Feedback component for displaying user messages."""
from typing import Optional, List
import streamlit as st


def render_feedback(
    message: str,
    type_: str = "info",
    suggestions: Optional[List[str]] = None
) -> None:
    """
    Display a feedback message with optional suggestions.
    
    Args:
        message: The message to display
        type_: Type of message ('success', 'error', or 'info')
        suggestions: Optional list of suggestion buttons to display
    """
    # Add custom CSS for RTL text direction
    st.markdown("""
        <style>
        .stAlert {
            direction: rtl;
        }
        .stAlert > div {
            flex-direction: row-reverse;
        }
        .stAlert > div > div {
            text-align: right;
        }
        </style>
    """, unsafe_allow_html=True)
    
    if type_ == "success":
        st.success(message)
    elif type_ == "error":
        st.error(message)
    else:
        st.info(message)
        
    if suggestions:
        for suggestion in suggestions:
            st.button(suggestion)