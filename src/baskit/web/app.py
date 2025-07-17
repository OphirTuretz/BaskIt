"""BaskIt - AI-powered grocery shopping assistant."""
import streamlit as st
from ai.text_to_item import parse_text_to_item
from services.list_manager import add_item, get_list, remove_item
from utils.logger import get_logger

logger = get_logger(__name__)

# Configure the page
st.set_page_config(
    page_title="BaskIt - רשימת קניות חכמה",
    page_icon="🛒",
    layout="wide",
)

# Add custom CSS for RTL support
st.markdown("""
    <style>
        .stTextInput input {
            direction: rtl;
            text-align: right;
        }
        .st-emotion-cache-1y4p8pa {
            direction: rtl;
            text-align: right;
        }
    </style>
""", unsafe_allow_html=True)

# App title
st.title("🛒 BaskIt - רשימת קניות חכמה")

# Text input for new items
text_input = st.text_input(
    "הוסף מוצר לרשימה",
    key="item_input",
    placeholder="לדוגמה: קניתי מלפפונים"
)

# Process input
if text_input:
    logger.info(f"Processing new input: {text_input}")
    parsed_item = parse_text_to_item(text_input)
    if add_item(parsed_item):
        st.success(f"הוספתי {parsed_item['item']} לרשימה")

# Display current list
st.subheader("📝 הרשימה שלך")
current_list = get_list()

if not current_list:
    st.info("הרשימה ריקה - התחל להוסיף פריטים!")
else:
    for idx, item in enumerate(current_list):
        col1, col2, col3 = st.columns([3, 1, 0.5])
        with col1:
            st.write(f"{item['item']} - {item['quantity']} {item['unit']}")
        with col2:
            st.write(f"ביטחון: {item['confidence']:.0%}")
        with col3:
            if st.button("❌", key=f"remove_{idx}"):
                remove_item(idx)
                st.rerun() 