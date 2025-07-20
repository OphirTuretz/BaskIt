"""List display component for showing items and their actions."""
import streamlit as st
from typing import cast

from baskit.services.list_service import ListService, ListContents
from baskit.services.item_service import ItemService
from baskit.services.base_service import Result
from .feedback import render_feedback


def render_list_display(
    list_service: ListService,
    item_service: ItemService,
    list_id: int
) -> None:
    """
    Render a grocery list and its items.
    
    Args:
        list_service: Service for managing lists
        item_service: Service for managing items
        list_id: ID of the list to display
    """
    # Get list contents
    result = list_service.show_list(list_id)
    if not result.success or not result.data:
        render_feedback(result.error, type_="error")
        return
        
    list_contents = cast(ListContents, result.data)
    st.header(list_contents.name)
    
    if not list_contents.items:
        st.info("הרשימה ריקה")
        return
        
    # Group items by bought status
    unbought_items = [i for i in list_contents.items if not i.is_bought]
    bought_items = [i for i in list_contents.items if i.is_bought]
    
    # Display unbought items first
    if unbought_items:
        st.subheader("פריטים לקנייה")
        for item in unbought_items:
            with st.container():
                # Use a single row of columns for the item
                name_col, inc_col, buy_col, dec_col, del_col = st.columns([3, 1, 1, 1, 1])
                
                with name_col:
                    st.write(f"{item.name} ({item.quantity} {item.unit})")
                
                with inc_col:
                    if st.button(
                        "➕ הוסף כמות",
                        key=f"inc_{item.id}"
                    ):
                        result = item_service.increment_quantity(item.id)
                        if result.success:
                            st.rerun()
                        else:
                            render_feedback(result.error, type_="error")
                
                with buy_col:
                    if st.button(
                        "✅ סמן כנקנה",
                        key=f"buy_{item.id}"
                    ):
                        result = item_service.mark_bought(item.id)
                        if result.success:
                            st.rerun()
                        else:
                            render_feedback(result.error, type_="error")
                
                with dec_col:
                    if st.button(
                        "➖ הפחת כמות",
                        key=f"dec_{item.id}"
                    ):
                        result = item_service.increment_quantity(
                            item.id,
                            step=-1
                        )
                        if result.success:
                            if result.message:  # Item was removed
                                render_feedback(
                                    result.message,
                                    type_="info"
                                )
                            st.rerun()
                        else:
                            render_feedback(result.error, type_="error")
                
                with del_col:
                    if st.button(
                        "❌ מחק פריט",
                        key=f"del_{item.id}"
                    ):
                        result = item_service.remove_item(item.id)
                        if result.success:
                            st.rerun()
                        else:
                            render_feedback(result.error, type_="error")
    
    # Display bought items in a collapsible section
    if bought_items:
        with st.expander("פריטים שנקנו"):
            for item in bought_items:
                name_col, action_col = st.columns([4, 1])
                with name_col:
                    st.write(f"{item.name} ({item.quantity} {item.unit})")
                with action_col:
                    if st.button(
                        "⬜ סמן כלא נקנה",
                        key=f"unbuy_{item.id}"
                    ):
                        result = item_service.mark_bought(
                            item.id,
                            is_bought=False
                        )
                        if result.success:
                            st.rerun()
                        else:
                            render_feedback(result.error, type_="error") 