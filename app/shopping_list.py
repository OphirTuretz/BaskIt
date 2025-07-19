import streamlit as st
import voice, image
import json
import os

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
    list_names = list(lists.keys())
    current_list = st.sidebar.selectbox("Select shopping list", list_names, key="current_list")
    st.sidebar.write(f"Current chain: {lists[current_list]['chain']}")
    # List actions
    if st.sidebar.button("Create new list"):
        new_name = st.text_input("New list name", key="new_list_name")
        if new_name and new_name not in lists:
            lists[new_name] = {'name': new_name, 'chain': user['default_chain'], 'items': []}
            st.session_state['current_list'] = new_name
            st.rerun()
    if st.sidebar.button("Delete current list") and len(lists) > 1:
        del lists[current_list]
        st.session_state['current_list'] = list(lists.keys())[0]
        st.rerun()
    # Show items
    st.subheader(f"Items in '{current_list}'")
    items = lists[current_list]['items']
    for i, item in enumerate(items):
        col1, col2, col3 = st.columns([4,2,1])
        col1.write(item['name'])
        if col2.button("Edit", key=f"edit_{i}"):
            new_name = st.text_input("Edit item", value=item['name'], key=f"edit_name_{i}")
            if new_name:
                item['name'] = new_name
        if col3.button("Delete", key=f"delete_{i}"):
            items.pop(i)
            st.rerun()
    st.markdown("---")
    st.subheader("Add item to list")
    # Add by text
    text_item = st.text_input("Add by text", key="add_text")
    if st.button("Add by text") and text_item:
        items.append({'name': text_item})
        st.rerun()
    # Add by voice
    st.write("Or add by voice:")
    voice_result = voice.record_and_recognize()
    if voice_result:
        items.append({'name': voice_result})
        st.success(f"Added by voice: {voice_result}")
        st.rerun()
    # Add by image
    st.write("Or add by image:")
    uploaded = st.file_uploader("Upload product image", type=["jpg", "jpeg", "png"], key="add_image")
    if uploaded and uploaded.name != st.session_state.get("last_processed_image"):
        image_result = image.mock_recognize(uploaded)
        if image_result:
            items.append({'name': image_result})
            st.success(f"Added by image: {image_result}")
            st.session_state["last_processed_image"] = uploaded.name
            st.rerun() 