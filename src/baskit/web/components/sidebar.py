"""Sidebar component for list navigation and management."""
import streamlit as st
from typing import cast, Optional

from baskit.services.list_service import ListService, ListSummary
from baskit.services.base_service import Result
from .feedback import render_feedback


def render_sidebar(list_service: ListService) -> Optional[int]:
    """
    Render the sidebar with list navigation and management.
    
    Args:
        list_service: Service for managing lists
        
    Returns:
        Selected list ID if a list is selected, None otherwise
    """
    with st.sidebar:
        st.title("🧺 BaskIt")
        
        # Create new list section
        with st.expander("צור רשימה חדשה", expanded=False):
            with st.form("create_list", clear_on_submit=True):
                name = st.text_input(
                    "שם הרשימה",
                    key="new_list_name"
                )
                submit = st.form_submit_button("צור")
                
                if submit and name:
                    result = list_service.create_list(name)
                    if result.success:
                        render_feedback(
                            f"רשימה '{name}' נוצרה בהצלחה",
                            type_="success"
                        )
                        st.rerun()  # Refresh to show new list
                    else:
                        render_feedback(
                            result.error,
                            type_="error",
                            suggestions=result.suggestions
                        )
        
        st.divider()
        
        # Get all lists
        result = list_service.list_all_user_lists()
        if not result.success or not result.data:
            render_feedback(
                result.error,
                type_="error",
                suggestions=result.suggestions
            )
            return None
            
        lists = cast(list[ListSummary], result.data)
        
        # Default list selection
        st.subheader("רשימת ברירת מחדל")
        default_list = next((l for l in lists if l.is_default), None)
        selected_default = st.selectbox(
            "בחר רשימת ברירת מחדל",
            options=lists,
            format_func=lambda x: x.name,
            index=lists.index(default_list) if default_list else 0,
            key="default_list"
        )
        
        if selected_default and selected_default.id != (default_list.id if default_list else None):
            result = list_service.set_default_list(selected_default.id)
            if result.success:
                render_feedback(
                    f"רשימת '{selected_default.name}' הוגדרה כברירת מחדל",
                    type_="success"
                )
                st.rerun()  # Refresh to update UI
            else:
                render_feedback(result.error, type_="error")
        
        st.divider()
        
        # List selection
        st.subheader("הרשימות שלי")
        selected_list_id = None
        
        for list_ in lists:
            col1, col2 = st.columns([4, 1])
            with col1:
                if st.button(
                    f"{'📌 ' if list_.is_default else ''}{list_.name}"
                    f" ({list_.total_items - list_.bought_items})",
                    key=f"list_{list_.id}"
                ):
                    selected_list_id = list_.id
            
            with col2:
                if st.button("🗑️", key=f"delete_{list_.id}"):
                    result = list_service.delete_list(list_.id)
                    if result.success:
                        render_feedback(
                            f"רשימה '{list_.name}' נמחקה",
                            type_="success"
                        )
                        st.rerun()
                    else:
                        render_feedback(result.error, type_="error")
        
        return selected_list_id 