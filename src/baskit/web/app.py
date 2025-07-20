"""Main Streamlit application for BaskIt."""
import streamlit as st

from baskit.services.list_service import ListService
from baskit.services.item_service import ItemService
from baskit.db.session import get_session
from baskit.web.components import (
    render_sidebar,
    render_list_display,
    render_add_item,
    render_feedback
)


def main():
    """Main application entry point."""
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
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # Initialize session state
    if 'db_session' not in st.session_state:
        st.session_state.db_session = get_session()
    
    # TODO: Replace with actual user ID from auth
    USER_ID = 1
    
    # Initialize services
    list_service = ListService(st.session_state.db_session, USER_ID)
    item_service = ItemService(st.session_state.db_session, USER_ID)
    
    # Initialize selected list
    if 'selected_list_id' not in st.session_state:
        default_list = list_service.get_default_list()
        st.session_state.selected_list_id = (
            default_list.data.id if default_list.success and default_list.data
            else None
        )
    
    # Render sidebar and get selected list
    selected_list_id = render_sidebar(list_service)
    if selected_list_id is not None:
        st.session_state.selected_list_id = selected_list_id
    
    # Render main content if list is selected
    if st.session_state.selected_list_id:
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
        st.info("בחר רשימה מהתפריט או צור רשימה חדשה")


if __name__ == "__main__":
    main() 