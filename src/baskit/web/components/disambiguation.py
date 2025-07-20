"""Disambiguation component for handling multiple item locations."""
from typing import List, Optional
import streamlit as st

from baskit.services.item_service import ItemLocation


def render_disambiguation(
    locations: List[ItemLocation],
    item_name: str
) -> Optional[int]:
    """
    Display disambiguation options when an item exists in multiple lists.
    
    Args:
        locations: List of locations where the item exists
        item_name: Name of the item
        
    Returns:
        Selected list ID if a choice was made, None otherwise
    """
    st.info(
        f"הפריט '{item_name}' קיים במספר רשימות. "
        "באיזו מהן לבצע את הפעולה?"
    )
    
    selected_list_id = None
    
    # Create columns for better button layout
    cols = st.columns(min(3, len(locations)))
    for idx, location in enumerate(locations):
        col = cols[idx % len(cols)]
        with col:
            if st.button(
                f"[{location.list_name}]",
                key=f"disambig_{location.list_id}"
            ):
                selected_list_id = location.list_id
    
    return selected_list_id 