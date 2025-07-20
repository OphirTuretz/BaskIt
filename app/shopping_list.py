import streamlit as st
import voice, image
import json, os, difflib
from transformers import pipeline
from ai_utils import ai_suggest_category, get_classifier

@st.cache_resource(show_spinner=False)
def get_classifier():
    return pipeline("zero-shot-classification", model="valhalla/distilbart-mnli-12-1")

def ai_suggest_category(item_name):
    classifier = get_classifier()
    candidate_labels = [
        "Dairy", "Fruit", "Vegetable", "Meat", "Bread",
        "Cleaning Products", "Essentials", "Snacks", "Personal Care", "Other"
    ]
    result = classifier(item_name, candidate_labels)
    return result['labels'][0] if result['labels'] else 'Other'

def is_similar(new_item, items, threshold=0.7):
    for item in items:
        if new_item.lower() != item['name'].lower() and difflib.SequenceMatcher(None, new_item.lower(), item['name'].lower()).ratio() > threshold:
            return item['name']
    return None

def load_lists(user):
    if 'lists' not in st.session_state:
        # For MVP, store lists in session state
        st.session_state['lists'] = {
            user['default_list']: {
                'name': user['default_list'],
                'chain': user['default_chain'],
                'items': []
            }
        }
    return st.session_state['lists']

def show(user):
    lists = load_lists(user)
    st.header("Shopping Lists")
    # List actions (in sidebar)
    with st.sidebar.form("create_list_form", clear_on_submit=True):
        new_name = st.text_input("New list name")
        create_submitted = st.form_submit_button("Create new list")
        if create_submitted:
            if not new_name:
                st.error("Please enter a name for the new list.")
            elif new_name in lists:
                st.error(f"List '{new_name}' already exists.")
            else:
                lists[new_name] = {'name': new_name, 'chain': user['default_chain'], 'items': []}
                st.success(f"Created new list: {new_name}")
                st.rerun()
    # Sidebar navigation for lists
    list_names = list(lists.keys())
    if 'current_list' in st.session_state:
        # Check if the current list name is still valid
        if st.session_state['current_list'] not in list_names:
            st.session_state['current_list'] = list_names[0] if list_names else None
        default_index = list_names.index(st.session_state.get('current_list', list_names[0])) if list_names else 0
    else:
        default_index = 0 if not list_names else len(list_names) - 1
    current_list = st.sidebar.selectbox("Select shopping list", list_names, index=default_index, key="current_list")
    st.sidebar.write(f"Current chain: {lists[current_list]['chain']}")
    # Option to select a chain for the current list
    chains = ["Shufersal", "Rami Levi", "Victory", "Tiv-Ta'am"]
    selected_chain = st.sidebar.selectbox("Select chain for this list", chains, index=chains.index(lists[current_list]['chain']), key=f"chain_{current_list}")
    if selected_chain != lists[current_list]['chain']:
        lists[current_list]['chain'] = selected_chain
        st.success(f"Chain for '{current_list}' updated to {selected_chain}.")
        st.rerun()
    if st.sidebar.button("Delete current list") and len(lists) > 1:
        del lists[current_list]
        st.success(f"Deleted list: {current_list}")
        st.rerun()
    # --- Price Display Logic ---
    # Load product data to get prices
    products_path = os.path.join(os.path.dirname(__file__), 'data/products.json')
    try:
        with open(products_path, encoding='utf-8') as f:
            products_data = json.load(f)
    except Exception:
        products_data = []
    # Get the chain for the current list
    current_chain = lists[current_list]['chain']
    total_cost = 0
    # Show items
    st.subheader(f"Items in '{current_list}'")
    items = lists[current_list]['items']
    if not items:
        st.info("No items yet! Add your first item below.")
    # Initialize edit_item_index if it doesn't exist
    if 'edit_item_index' not in st.session_state:
        st.session_state['edit_item_index'] = None
    for i, item in enumerate(items):
        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
        # --- Smarter Price Lookup Logic ---
        item_name_lower = item['name'].lower()
        best_match = None
        
        # 1. First, check for substring matches (catches generic names like "bread" in "Whole Wheat Bread")
        substring_matches = [
            p for p in products_data 
            if item_name_lower in p.get('name_en', '').lower() or item_name_lower in p.get('name_he', '').lower()
        ]
        if substring_matches:
            best_match = substring_matches[0] # Take the first substring match
        else:
            # 2. If no substring match, fall back to fuzzy matching for typos
            highest_ratio = 0.6  # Lower threshold for better matching
            for p in products_data:
                r_en = difflib.SequenceMatcher(None, item_name_lower, p.get('name_en', '').lower()).ratio()
                r_he = difflib.SequenceMatcher(None, item_name_lower, p.get('name_he', '').lower()).ratio()
                if r_en > highest_ratio:
                    highest_ratio = r_en
                    best_match = p
                if r_he > highest_ratio:
                    highest_ratio = r_he
                    best_match = p

        price = best_match['price_per_chain'][current_chain] if best_match else None
        if price:
            total_cost += price
        # Display item and price
        item_display = f"{item['name']}"
        price_display = f"₪{price:.2f}" if price is not None else "N/A"
        if st.session_state['edit_item_index'] == i:
            # Show text input for editing
            with col1:
                new_name = st.text_input("Edit item", value=item['name'], key=f"edit_name_{i}")
            with col3:
                if st.button("💾", key=f"save_{i}"):
                    if any(j != i and items[j]['name'].lower() == new_name.lower() for j in range(len(items))):
                        st.error(f"'{new_name}' is already in the list!")
                    elif is_similar(new_name, [itm for idx, itm in enumerate(items) if idx != i]):
                        st.warning(f"Did you mean '{is_similar(new_name, [itm for idx, itm in enumerate(items) if idx != i])}'? (already in list)")
                    else:
                        item['name'] = new_name
                        item.pop('category', None)
                        st.success(f"Item updated to: {new_name}")
                        st.session_state['edit_item_index'] = None
                        st.rerun()
            with col4:
                if st.button("❌", key=f"cancel_{i}"):
                    st.session_state['edit_item_index'] = None
                    st.rerun()
        else:
            category = item.get('category', 'Uncategorized')
            col1.write(f"{item_display} (Category: {category})")
            col2.write(f"**{price_display}**")
            with col3:
                if st.button("✏️", key=f"edit_{i}"):
                    st.session_state['edit_item_index'] = i
                    st.rerun()
            with col4:
                if st.button("🗑️", key=f"delete_{i}"):
                    items.pop(i)
                    st.success("Item deleted.")
                    st.rerun()
    # Display Total Cost
    st.markdown("---")
    st.subheader(f"Total Cost: ₪{total_cost:.2f}")
    st.markdown("---")
    # "Organize by Category" button
    if items:
        if st.button("✨ Organize by Category"):
            with st.spinner("Categorizing your list..."):
                item_names = [item['name'] for item in items if 'category' not in item]
                if item_names:
                    classifier = get_classifier()
                    candidate_labels = [
                        "Dairy", "Fruit", "Vegetable", "Meat", "Bread",
                        "Cleaning Products", "Essentials", "Snacks", "Personal Care", "Other"
                    ]
                    results = classifier(item_names, candidate_labels)
                    # Update only uncategorized items
                    uncategorized_items = [item for item in items if 'category' not in item]
                    for item, result in zip(uncategorized_items, results):
                        item['category'] = result['labels'][0]
                    st.success("Your list has been categorized!")
                    st.rerun()
                else:
                    st.info("All items are already categorized!")
    st.markdown("---")
    st.subheader("Add item to list")
    # Add by text using a form for robust clearing
    with st.form("add_item_form", clear_on_submit=True):
        text_item = st.text_input("Add by text")
        submitted = st.form_submit_button("Add by text")
        if submitted and text_item:
            similar = is_similar(text_item, items)
            if any(item['name'].lower() == text_item.lower() for item in items):
                st.error(f"'{text_item}' is already in the list!")
            elif similar:
                st.warning(f"Did you mean '{similar}'? (already in list)")
            else:
                items.append({'name': text_item.capitalize()})
                st.success(f"Added: {text_item.capitalize()}")
                st.rerun()
    # Add by voice
    st.write("Or add by voice:")
    voice_result = voice.record_and_recognize()
    if voice_result:
        similar = is_similar(voice_result, items)
        if any(item['name'].lower() == voice_result.lower() for item in items):
            st.error(f"'{voice_result}' is already in the list!")
        elif similar:
            st.warning(f"Did you mean '{similar}'? (already in list)")
        else:
            items.append({'name': voice_result.capitalize()})
            st.success(f"Added by voice: {voice_result.capitalize()}")
            st.rerun()
    # Add by image
    st.write("Or add by image:")
    uploaded = st.file_uploader("Upload product image", type=["jpg", "jpeg", "png"], key="add_image")
    if uploaded and uploaded.name != st.session_state.get("last_processed_image"):
        image_result = image.mock_recognize(uploaded)
        if image_result:
            similar = is_similar(image_result, items)
            if any(item['name'].lower() == image_result.lower() for item in items):
                st.error(f"'{image_result}' is already in the list!")
            elif similar:
                st.warning(f"Did you mean '{similar}'? (already in list)")
            else:
                items.append({'name': image_result.capitalize()})
                st.success(f"Added by image: {image_result.capitalize()}")
                st.session_state["last_processed_image"] = uploaded.name
                st.rerun()
    # --- Shopping List Optimizer: Suggest Cheapest Chain ---
    products_path = os.path.join(os.path.dirname(__file__), 'data/products.json')
    try:
        with open(products_path, encoding='utf-8') as f:
            products_data = json.load(f)
    except Exception:
        products_data = []
    chains = ["Shufersal", "Rami Levi", "Victory", "Tiv-Ta'am"]
    totals = {chain: 0 for chain in chains}
    for item in items:
        prod = next((p for p in products_data if p.get('name_he', '').lower() == item['name'].lower() or p.get('name_en', '').lower() == item['name'].lower()), None)
        if prod:
            for chain in chains:
                totals[chain] += prod['price_per_chain'][chain]
    if items:
        # Calculate overall cheapest chain
        overall_totals = {chain: 0 for chain in chains}
        for item in items:
            # Re-use the smart matching logic to find the best match for each item
            item_name_lower = item['name'].lower()
            best_match = None
            substring_matches = [p for p in products_data if item_name_lower in p.get('name_en', '').lower() or item_name_lower in p.get('name_he', '').lower()]
            if substring_matches:
                best_match = substring_matches[0]
            else:
                highest_ratio = 0.6
                for p in products_data:
                    r_en = difflib.SequenceMatcher(None, item_name_lower, p.get('name_en', '').lower()).ratio()
                    r_he = difflib.SequenceMatcher(None, item_name_lower, p.get('name_he', '').lower()).ratio()
                    if r_en > highest_ratio: highest_ratio = r_en; best_match = p
                    if r_he > highest_ratio: highest_ratio = r_he; best_match = p
            
            if best_match:
                for chain in chains:
                    overall_totals[chain] += best_match['price_per_chain'][chain]
        
        if sum(overall_totals.values()) > 0:
            cheapest_overall = min(overall_totals, key=overall_totals.get)
            st.info(f"Overall cheapest chain for this list: **{cheapest_overall}** (Total: ₪{overall_totals[cheapest_overall]:.2f})") 