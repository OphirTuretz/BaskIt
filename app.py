import streamlit as st
import speech_recognition as sr
from PIL import Image
import io
from typing import Callable

# Initialize session state for shopping cart if it doesn't exist
if 'shopping_cart' not in st.session_state:
    st.session_state.shopping_cart = []

def add_item(item_name: str, quantity: int = 1) -> bool:
    """Add an item to the shopping cart."""
    if not item_name:
        return False
        
    item_name = item_name.strip().lower()
    # Check if item already exists
    for item in st.session_state.shopping_cart:
        if item['item'].lower() == item_name:
            item['quantity'] += quantity
            return True
            
    st.session_state.shopping_cart.append({
        'item': item_name,
        'quantity': quantity
    })
    return True

def on_text_change() -> None:
    """Handle text input changes"""
    if st.session_state.text_input:
        add_item(st.session_state.text_input, int(st.session_state.text_quantity))

# Page config
st.set_page_config(page_title="Smart Grocery Cart", page_icon="🛒")
st.title("🛒 Smart Grocery Cart Manager")

# Sidebar for cart display
with st.sidebar:
    st.header("Your Shopping Cart")
    if not st.session_state.shopping_cart:
        st.info("Your cart is empty")
    else:
        for idx, item in enumerate(st.session_state.shopping_cart):
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(item['item'])
            with col2:
                st.write(f"Qty: {item['quantity']}")
            with col3:
                if st.button("🗑️", key=f"delete_{idx}"):
                    st.session_state.shopping_cart.pop(idx)
                    st.rerun()

# Input method tabs
tab1, tab2, tab3 = st.tabs(["📝 Text Input", "🎤 Voice Input", "📷 Image Input"])

# Text Input Tab
with tab1:
    st.header("Add Item by Text")
    col1, col2 = st.columns([3, 1])
    with col1:
        text_input = st.text_input("Enter item name (press Enter to add):", key="text_input", on_change=on_text_change)
    with col2:
        quantity = st.number_input("Quantity:", min_value=1, value=1, key="text_quantity", step=1)
    if st.button("Add to Cart", key="text_add"):
        if add_item(text_input, int(quantity)):
            st.success(f"Added {quantity} {text_input} to cart!")
            st.session_state.text_input = ""  # Clear input after adding
        else:
            st.error("Please enter an item name")

# Voice Input Tab
with tab2:
    st.header("Add Item by Voice")
    st.info("Please ensure your microphone is connected and you've granted browser permission.")
    
    if st.button("🎤 Start Recording", key="voice_record"):
        with st.spinner("Listening..."):
            try:
                recognizer = sr.Recognizer()
                with sr.Microphone() as source:
                    st.write("Adjusting for ambient noise... Speak now!")
                    recognizer.adjust_for_ambient_noise(source)
                    audio = recognizer.listen(source, timeout=5)
                try:
                    text = recognizer.recognize_google(audio)
                    st.write(f"Recognized: {text}")
                    if add_item(text):
                        st.success(f"Added {text} to cart!")
                except sr.UnknownValueError:
                    st.error("Could not understand audio")
                except sr.RequestError:
                    st.error("Could not request results")
            except Exception as e:
                st.error(f"Error accessing microphone: {str(e)}")

# Image Input Tab
with tab3:
    st.header("Add Item by Image")
    uploaded_file = st.file_uploader("Upload an image of your item", type=['png', 'jpg', 'jpeg'])
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image", use_column_width=True)
        st.info("Note: Image recognition feature will be implemented in future versions. For now, please provide the item name manually.")
        image_item_name = st.text_input("Confirm item name:", key="image_item_name")
        image_quantity = st.number_input("Quantity:", min_value=1, value=1, key="image_quantity", step=1)
        if st.button("Add to Cart", key="image_add"):
            if add_item(image_item_name, int(image_quantity)):
                st.success(f"Added {image_quantity} {image_item_name} to cart!")
                st.session_state.image_item_name = ""  # Clear input after adding
            else:
                st.error("Please enter an item name") 