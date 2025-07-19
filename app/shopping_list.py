import streamlit as st
import voice, image
import json, os, difflib

def suggest_category(item_name):
    name = item_name.lower()
    if any(word in name for word in ['milk', 'cheese', 'yogurt', 'butter']):
        return 'Dairy'
    if any(word in name for word in ['apple', 'banana', 'orange', 'grape']):
        return 'Fruit'
    if any(word in name for word in ['tomato', 'lettuce', 'carrot', 'onion']):
        return 'Vegetable'
    if any(word in name for word in ['chicken', 'beef', 'fish']):
        return 'Meat'
    if 'bread' in name:
        return 'Bread'
    return 'Other'

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
    default_index = list_names.index(st.session_state.get('current_list', list_names[0])) if 'current_list' in st.session_state else len(list_names) - 1
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
    # Show items
    st.subheader(f"Items in '{current_list}'")
    items = lists[current_list]['items']
    if not items:
        st.info("No items yet! Add your first item below.")
    # Inline edit state
    if 'edit_item_index' not in st.session_state:
        st.session_state['edit_item_index'] = None
    for i, item in enumerate(items):
        col1, col2, col3 = st.columns([4,1,1])
        if st.session_state['edit_item_index'] == i:
            # Show text input for editing
            with col1:
                new_name = st.text_input("Edit item", value=item['name'], key=f"edit_name_{i}")
            with col2:
                if st.button("💾", key=f"save_{i}"):
                    # Check for duplicates and similarity
                    if any(j != i and items[j]['name'].lower() == new_name.lower() for j in range(len(items))):
                        st.error(f"'{new_name}' is already in the list!")
                    elif is_similar(new_name, [itm for idx, itm in enumerate(items) if idx != i]):
                        st.warning(f"Did you mean '{is_similar(new_name, [itm for idx, itm in enumerate(items) if idx != i])}'? (already in list)")
                    else:
                        item['name'] = new_name
                        st.success(f"Item updated to: {new_name}")
                        st.session_state['edit_item_index'] = None
                        st.rerun()
            with col3:
                if st.button("❌", key=f"cancel_{i}"):
                    st.session_state['edit_item_index'] = None
                    st.rerun()
        else:
            col1.write(f"{item['name']} — Category: {suggest_category(item['name'])}")
            with col2:
                if st.button("✏️", key=f"edit_{i}"):
                    st.session_state['edit_item_index'] = i
                    st.rerun()
            with col3:
                if st.button("🗑️", key=f"delete_{i}"):
                    items.pop(i)
                    st.success("Item deleted.")
                    st.rerun()
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
                st.success(f"Added: {text_item.capitalize()} (Category: {suggest_category(text_item)})")
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
            st.success(f"Added by voice: {voice_result.capitalize()} (Category: {suggest_category(voice_result)})")
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
                st.success(f"Added by image: {image_result.capitalize()} (Category: {suggest_category(image_result)})")
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
        cheapest = min(totals, key=totals.get)
        st.info(f"Cheapest chain for your current list: {cheapest} (₪{totals[cheapest]:.2f})") 