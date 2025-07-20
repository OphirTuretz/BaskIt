"""Add item component for adding new items to lists."""
import streamlit as st

from baskit.services.item_service import ItemService
from .feedback import render_feedback


def render_add_item(item_service: ItemService, list_id: int) -> None:
    """
    Render the add item form.
    
    Args:
        item_service: Service for managing items
        list_id: ID of the list to add items to
    """
    st.subheader("הוסף פריט")
    
    with st.form("add_item", clear_on_submit=True):
        name = st.text_input(
            "שם פריט",
            key="add_item_name"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            quantity = int(st.number_input(  # Cast to int
                "כמות",
                min_value=1,
                max_value=99,
                value=1,
                help="ברירת מחדל: 1",
                key="add_item_quantity"
            ))
        
        with col2:
            unit = str(st.selectbox(  # Cast to str
                "יחידה",
                options=["יחידה", "ק״ג", "גרם", "ליטר", "מ״ל"],
                index=0,
                key="add_item_unit"
            ))
        
        submit = st.form_submit_button("הוסף פריט")
        
        if submit and name:  # Only process if name is not empty
            result = item_service.add_item(
                list_id=list_id,
                name=name,
                quantity=quantity,
                unit=unit
            )
            
            if result.success:
                render_feedback(
                    f"הפריט {name} נוסף בהצלחה",
                    type_="success"
                )
            else:
                render_feedback(
                    result.error,
                    type_="error",
                    suggestions=result.suggestions
                ) 