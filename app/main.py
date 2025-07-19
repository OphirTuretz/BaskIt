import streamlit as st
import auth, onboarding, shopping_list, price_compare, checkout, history, reminders

st.set_page_config(page_title="Groceries App", layout="wide")

# Session state for navigation
if 'page' not in st.session_state:
    st.session_state.page = 'Shopping List'

# Sidebar navigation
st.sidebar.title("Groceries App")
pages = [
    "Shopping List",
    "Price Comparison",
    "Checkout",
    "Purchase History",
    "Reminders",
    "Settings"
]
selected = st.sidebar.radio("Navigate", pages, index=pages.index(st.session_state.page))
st.session_state.page = selected

# Authentication (placeholder for MVP)
user = auth.login()
if not user:
    st.stop()

# Onboarding/settings (first time)
if not st.session_state.get('onboarded', False):
    if onboarding.show_onboarding(user):
        st.stop()

# Main page routing
if selected == "Shopping List":
    shopping_list.show(user)
elif selected == "Price Comparison":
    price_compare.show(user)
elif selected == "Checkout":
    checkout.show(user)
elif selected == "Purchase History":
    history.show(user)
elif selected == "Reminders":
    reminders.show(user)
elif selected == "Settings":
    onboarding.show_settings(user) 