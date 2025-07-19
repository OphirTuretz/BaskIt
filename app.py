import streamlit as st
import speech_recognition as sr
from PIL import Image
import io
from typing import Callable, Optional, Union, Any
import base64
import json
from datetime import datetime
from ai_parser import parse_input_to_action, ParsingError

# Initialize session states
if 'active_list' not in st.session_state:
    st.session_state.active_list = 'default'
if 'shopping_lists' not in st.session_state:
    st.session_state.shopping_lists = {'default': []}
if 'clear_text' not in st.session_state:
    st.session_state.clear_text = False
if 'needs_rerun' not in st.session_state:
    st.session_state.needs_rerun = False

def get_current_cart():
    """Get the current active shopping cart."""
    return st.session_state.shopping_lists[st.session_state.active_list]

def set_current_cart(cart):
    """Set the current active shopping cart."""
    st.session_state.shopping_lists[st.session_state.active_list] = cart

def add_item(item_name: str, quantity: int = 1) -> bool:
    """Add an item to the shopping cart."""
    if not item_name:
        return False
        
    item_name = item_name.strip().lower()
    current_cart = get_current_cart()
    
    # Check if item already exists
    for item in current_cart:
        if item['item'].lower() == item_name:
            item['quantity'] += quantity
            set_current_cart(current_cart)
            return True
            
    current_cart.append({
        'item': item_name,
        'quantity': quantity
    })
    set_current_cart(current_cart)
    return True

def update_quantity(idx: int, delta: int) -> None:
    """Update item quantity in cart."""
    current_cart = get_current_cart()
    new_quantity = current_cart[idx]['quantity'] + delta
    
    if new_quantity <= 0:
        current_cart.pop(idx)
    else:
        current_cart[idx]['quantity'] = new_quantity
    
    set_current_cart(current_cart)
    st.session_state.needs_rerun = True

def set_quantity(idx: int, new_quantity: int) -> None:
    """Set exact quantity for item."""
    current_cart = get_current_cart()
    if new_quantity <= 0:
        current_cart.pop(idx)
    else:
        current_cart[idx]['quantity'] = new_quantity
    set_current_cart(current_cart)
    st.session_state.needs_rerun = True

def clear_cart() -> None:
    """Clear the entire current cart."""
    set_current_cart([])
    st.session_state.needs_rerun = True

def create_new_list(list_name: str) -> None:
    """Create a new shopping list."""
    if list_name and list_name not in st.session_state.shopping_lists:
        st.session_state.shopping_lists[list_name] = []
        st.session_state.active_list = list_name
        st.session_state.needs_rerun = True

def delete_list(list_name: str) -> None:
    """Delete a shopping list."""
    if list_name in st.session_state.shopping_lists and list_name != 'default':
        del st.session_state.shopping_lists[list_name]
        st.session_state.active_list = 'default'
        st.session_state.needs_rerun = True

def handle_parsed_action(action_dict: dict) -> None:
    """Handle parsed action from AI parser."""
    try:
        action = action_dict["action"]
        if action == "add":
            if add_item(action_dict["item"], action_dict.get("quantity", 1)):
                st.success(f"Added {action_dict.get('quantity', 1)} {action_dict['item']} to cart!")
                st.session_state.clear_text = True
        elif action == "remove":
            # Find and remove the item
            current_cart = get_current_cart()
            for idx, item in enumerate(current_cart):
                if item["item"].lower() == action_dict["item"].lower():
                    update_quantity(idx, -item["quantity"])
                    st.success(f"Removed {action_dict['item']} from cart!")
                    break
        elif action == "switch_list":
            if action_dict["list_name"] in st.session_state.shopping_lists:
                st.session_state.active_list = action_dict["list_name"]
                st.success(f"Switched to {action_dict['list_name']} list!")
            else:
                st.error(f"List '{action_dict['list_name']}' not found!")
        elif action == "create_list":
            create_new_list(action_dict["list_name"])
            st.success(f"Created new list: {action_dict['list_name']}")
        elif action == "delete_list":
            delete_list(action_dict["list_name"])
            st.success(f"Deleted list: {action_dict['list_name']}")
    except Exception as e:
        st.error(f"Error processing action: {str(e)}")

def on_text_change() -> None:
    """Handle text input changes"""
    if st.session_state.text_input:
        try:
            action_dict = parse_input_to_action(st.session_state.text_input)
            handle_parsed_action(action_dict)
        except ParsingError as e:
            st.error(f"Could not understand input: {str(e)}")

def handle_image_data(image_data: Union[str, bytes, io.BytesIO, None]) -> Optional[Image.Image]:
    """Handle both uploaded files and pasted image data."""
    try:
        if image_data is None:
            return None
        if isinstance(image_data, str) and image_data.startswith('data:image'):
            # Handle pasted image
            image_data = image_data.split(',')[1]
            image_bytes = base64.b64decode(image_data)
            return Image.open(io.BytesIO(image_bytes))
        elif hasattr(image_data, 'read'):
            # Handle uploaded file
            return Image.open(image_data)
        return None
    except Exception as e:
        st.error(f"Error processing image: {str(e)}")
        return None

def recognize_speech(recognizer: Any, audio: Any) -> Optional[str]:
    """Wrapper for speech recognition to handle type hints."""
    try:
        return recognizer.recognize_google(audio)
    except (AttributeError, sr.UnknownValueError, sr.RequestError) as e:
        st.error(f"Speech recognition error: {str(e)}")
        return None

# Page config
st.set_page_config(page_title="BaskIt", page_icon="🛒", layout="wide")
st.title("🛒 BaskIt")

# List management in the main area
col1, col2 = st.columns([3, 1])
with col2:
    st.subheader("Manage Lists")
    new_list_name = st.text_input("New List Name", key="new_list_name")
    if st.button("Create New List"):
        create_new_list(new_list_name)
    
    st.selectbox(
        "Select Active List",
        options=list(st.session_state.shopping_lists.keys()),
        key="list_selector",
        on_change=lambda: setattr(st.session_state, 'active_list', st.session_state.list_selector)
    )
    
    if st.session_state.active_list != 'default':
        if st.button("Delete Current List"):
            delete_list(st.session_state.active_list)

# Sidebar for cart display
with st.sidebar:
    st.header(f"Shopping Cart: {st.session_state.active_list}")
    
    # Clear cart button
    if get_current_cart():
        if st.button("🗑️ Clear Cart"):
            clear_cart()
    
    if not get_current_cart():
        st.info("Your cart is empty")
    else:
        for idx, item in enumerate(get_current_cart()):
            st.write("---")
            st.write(item['item'])
            st.number_input(
                "Quantity",
                min_value=0,
                value=item['quantity'],
                key=f"qty_{idx}",
                on_change=lambda i=idx, q=f"qty_{idx}": set_quantity(i, st.session_state[q])
            )
            st.button("➕", key=f"plus_{idx}", on_click=lambda i=idx: update_quantity(i, 1))
            st.button("➖", key=f"minus_{idx}", on_click=lambda i=idx: update_quantity(i, -1))
            st.button("🗑️", key=f"delete_{idx}", on_click=lambda i=idx: update_quantity(i, -item['quantity']))

with col1:
    # Input method tabs
    tab1, tab2, tab3 = st.tabs(["📝 Text Input", "🎤 Voice Input", "📷 Image Input"])

    # Text Input Tab
    with tab1:
        st.header("Add Item by Text")
        text_col1, text_col2 = st.columns([3, 1])
        with text_col1:
            # Clear text input if needed
            if st.session_state.clear_text:
                st.session_state.text_input = ""
                st.session_state.clear_text = False
            text_input = st.text_input(
                "Enter command (e.g., 'add 2 tomatoes', 'switch to party list'):",
                key="text_input",
                on_change=on_text_change,
                help="You can use natural language commands like:\n- 'add two tomatoes'\n- 'remove milk'\n- 'switch to party list'"
            )
        with text_col2:
            quantity = st.number_input("Default Quantity:", min_value=1, value=1, key="text_quantity", step=1)
        if st.button("Process Command", key="text_add"):
            if text_input:
                try:
                    action_dict = parse_input_to_action(text_input)
                    handle_parsed_action(action_dict)
                except ParsingError as e:
                    st.error(f"Could not understand input: {str(e)}")
            else:
                st.error("Please enter a command")

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
                        text = recognize_speech(recognizer, audio)
                        if text:
                            st.write(f"Recognized: {text}")
                            if add_item(text):
                                st.success(f"Added {text} to cart!")
                    except Exception as e:
                        st.error(f"Error accessing microphone: {str(e)}")
                except Exception as e:
                    st.error(f"Error accessing microphone: {str(e)}")

    # Image Input Tab
    with tab3:
        st.header("Add Item by Image")
        
        # Add instructions for pasting images
        st.info("You can either upload an image file or paste an image directly (Ctrl+V)")
        
        # File uploader
        uploaded_file = st.file_uploader("Upload an image of your item", type=['png', 'jpg', 'jpeg'])
        
        # JavaScript for handling image paste
        st.markdown("""
        <script>
        const pasteArea = document.getElementById('paste_area');
        if (pasteArea) {
            document.addEventListener('paste', function(e) {
                const items = e.clipboardData.items;
                for (let i = 0; i < items.length; i++) {
                    if (items[i].type.indexOf('image') !== -1) {
                        const blob = items[i].getAsFile();
                        const reader = new FileReader();
                        reader.onload = function(e) {
                            pasteArea.value = e.target.result;
                            pasteArea.dispatchEvent(new Event('change'));
                        };
                        reader.readAsDataURL(blob);
                    }
                }
            });
        }
        </script>
        """, unsafe_allow_html=True)
        
        # Image paste area
        paste_placeholder = st.empty()
        paste_area = paste_placeholder.text_area(
            "Or paste image here (Ctrl+V)",
            key="paste_area",
            height=100,
            help="Press Ctrl+V to paste an image here"
        )
        
        # Handle both uploaded and pasted images
        image_data = uploaded_file if uploaded_file is not None else (paste_area if paste_area.startswith('data:image') else None)
        
        if image_data is not None:
            image = handle_image_data(image_data)
            if image:
                st.image(image, caption="Uploaded/Pasted Image", use_column_width=True)
                st.info("Note: Image recognition feature will be implemented in future versions. For now, please provide the item name manually.")
                image_item_name = st.text_input("Confirm item name:", key="image_item_name")
                image_quantity = st.number_input("Quantity:", min_value=1, value=1, key="image_quantity", step=1)
                if st.button("Add to Cart", key="image_add"):
                    if add_item(image_item_name, int(image_quantity)):
                        st.success(f"Added {image_quantity} {image_item_name} to cart!")
                        # Clear the image input field using session state
                        st.session_state.image_item_name = ""
                        # Clear the paste area
                        st.session_state.paste_area = ""
                        uploaded_file = None
                        st.session_state.needs_rerun = True

# Handle rerun if needed
if st.session_state.needs_rerun:
    st.session_state.needs_rerun = False
    st.rerun() 