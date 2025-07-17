"""BaskIt - AI-powered grocery shopping assistant."""
import streamlit as st
from baskit.ai.text_to_item import parse_text_to_item
from baskit.services.list_manager import add_item, get_list, remove_item
from baskit.utils.logger import get_logger

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
        /* RTL support for all text */
        .stTextInput input, .stMarkdown, div[data-testid="stText"] {
            direction: rtl;
            text-align: right;
        }
        
        /* RTL for success/info messages */
        .stSuccess, .stInfo {
            direction: rtl;
            text-align: right;
        }
        
        /* RTL for headers */
        h1, h2, h3 {
            direction: rtl;
            text-align: right !important;
        }
        
        /* Fix columns layout for RTL */
        [data-testid="column"] {
            direction: rtl;
            text-align: right;
            padding: 0 !important;
            display: flex !important;
            align-items: center !important;
        }

        /* Container for list items */
        div[data-testid="stHorizontalBlock"] {
            background: rgba(255, 255, 255, 0.05);
            padding: 0.5rem;
            border-radius: 4px;
            margin: 0.25rem 0;
            align-items: center !important;
        }
        
        /* Align buttons to the left in RTL context */
        button[kind="secondary"] {
            float: left;
            margin: 0 !important;
        }
        
        /* Fix input placeholder */
        .stTextInput input::placeholder {
            text-align: right;
        }
        
        /* Fix overall page layout */
        .main {
            direction: rtl;
        }

        /* Force text alignment in columns */
        [data-testid="column"] > div {
            text-align: right !important;
            width: 100%;
            margin: 0 !important;
            padding: 0 1rem !important;
        }

        /* Remove extra paragraph margins */
        [data-testid="column"] p {
            margin: 0 !important;
        }

        /* Ensure delete button aligns left */
        [data-testid="column"]:nth-child(3) {
            justify-content: center !important;
        }

        /* Ensure confidence aligns center */
        [data-testid="column"]:nth-child(2) {
            justify-content: center !important;
        }

        /* Ensure item text aligns right */
        [data-testid="column"]:nth-child(1) {
            justify-content: flex-end !important;
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
        # Create columns with proper spacing
        cols = st.columns([3, 1, 0.5])
        
        # Item name and quantity (right)
        cols[0].write(f"{item['item']} - {item['quantity']} {item['unit']}")
        
        # Confidence (center)
        cols[1].write(f"ביטחון: {item['confidence']:.0%}")
        
        # Delete button (left)
        if cols[2].button("❌", key=f"remove_{idx}"):
            remove_item(idx)
            st.rerun() 