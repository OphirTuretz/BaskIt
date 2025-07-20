import streamlit as st
import json
import os
import pandas as pd
from ai_utils import ai_suggest_category, get_classifier
import difflib

def show(user):
    st.header("Price Comparison by Category")
    # Get current list
    lists = st.session_state.get('lists', {})
    current_list_name = st.session_state.get('current_list', user['default_list'])
    current_list = lists.get(current_list_name, {'items': []})
    if not current_list['items']:
        st.info("Your shopping list is empty.")
        return
    # Categorize uncategorized items
    uncategorized_items = [item for item in current_list['items'] if 'category' not in item]
    if uncategorized_items:
        with st.spinner("Categorizing items..."):
            item_names = [item['name'] for item in uncategorized_items]
            classifier = get_classifier()
            candidate_labels = [
                "Dairy", "Fruit", "Vegetable", "Meat", "Bread",
                "Cleaning Products", "Essentials", "Snacks", "Personal Care", "Other"
            ]
            results = classifier(item_names, candidate_labels)
            for item, result in zip(uncategorized_items, results):
                item['category'] = result['labels'][0]
            st.success("Items categorized!")
    # Load products data
    products_path = os.path.join(os.path.dirname(__file__), 'data/products.json')
    try:
        with open(products_path, encoding='utf-8') as f:
            products_data = json.load(f)
    except Exception:
        products_data = []
        st.error("Could not load product data.")
        return
    # Group items by category and calculate totals
    chains = ["Shufersal", "Rami Levi", "Victory", "Tiv-Ta'am"]
    category_totals = {cat: {chain: 0 for chain in chains} for cat in set(item.get('category', 'Other') for item in current_list['items'])}
    for item in current_list['items']:
        category = item.get('category', 'Other')
        # --- Smarter Price Lookup Logic ---
        item_name_lower = item['name'].lower()
        best_match = None
        # 1. First, check for substring matches
        substring_matches = [
            p for p in products_data 
            if item_name_lower in p.get('name_en', '').lower() or item_name_lower in p.get('name_he', '').lower()
        ]
        if substring_matches:
            best_match = substring_matches[0]
        else:
            # 2. If no substring match, fall back to fuzzy matching
            highest_ratio = 0.6
            for p in products_data:
                r_en = pd.Series(item_name_lower).apply(lambda x: difflib.SequenceMatcher(None, x, p.get('name_en', '').lower()).ratio()).iloc[0]
                r_he = pd.Series(item_name_lower).apply(lambda x: difflib.SequenceMatcher(None, x, p.get('name_he', '').lower()).ratio()).iloc[0]
                if r_en > highest_ratio:
                    highest_ratio = r_en
                    best_match = p
                if r_he > highest_ratio:
                    highest_ratio = r_he
                    best_match = p
        
        if best_match:
            for chain in chains:
                category_totals[category][chain] += best_match['price_per_chain'][chain]
    # Display comparison
    st.subheader("Total Price by Category")
    for category, totals in category_totals.items():
        st.markdown(f"**{category}**")
        df = pd.DataFrame([totals])
        st.dataframe(df)
        cheapest_chain = min(totals, key=totals.get)
        st.write(f"Cheapest for {category}: **{cheapest_chain}** (₪{totals[cheapest_chain]:.2f})")
        st.markdown("---")
    # Overall cheapest
    overall_totals = {chain: sum(category_totals[cat][chain] for cat in category_totals) for chain in chains}
    cheapest_overall = min(overall_totals, key=overall_totals.get)
    st.success(f"Overall cheapest chain: **{cheapest_overall}** (₪{overall_totals[cheapest_overall]:.2f})") 