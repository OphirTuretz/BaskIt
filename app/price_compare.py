import streamlit as st
import json
import os

def show(user):
    st.header("Price Comparison")
    # Load products
    products_path = os.path.join(os.path.dirname(__file__), 'data/products.json')
    with open(products_path, encoding='utf-8') as f:
        products = json.load(f)
    # Get current list
    lists = st.session_state.get('lists', {})
    current_list_name = st.session_state.get('current_list', user['default_list'])
    current_list = lists.get(current_list_name, {'items': []})
    if not current_list['items']:
        st.info("Your shopping list is empty.")
        return
    # Calculate total per chain
    chains = ["Shufersal", "Rami Levi", "Victory", "Tiv-Ta'am"]
    totals = {chain: 0 for chain in chains}
    for item in current_list['items']:
        # Find product by name (Hebrew or English)
        prod = next((p for p in products if p['name_he'] == item['name'] or p['name_en'] == item['name']), None)
        if prod:
            for chain in chains:
                totals[chain] += prod['price_per_chain'][chain]
    # Display table
    st.subheader(f"Total price for '{current_list_name}' in each chain:")
    cheapest = min(totals, key=totals.get)
    st.table([{**{'Chain': chain, 'Total': totals[chain]}, **({'Cheapest': '✅'} if chain == cheapest else {})} for chain in chains])
    st.success(f"Cheapest chain: {cheapest} ({totals[cheapest]:.2f}₪)") 