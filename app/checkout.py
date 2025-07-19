import streamlit as st

def show(user):
    st.header("Checkout")
    lists = st.session_state.get('lists', {})
    current_list_name = st.session_state.get('current_list', user['default_list'])
    current_list = lists.get(current_list_name, {'items': []})
    if not current_list['items']:
        st.info("Your shopping list is empty.")
        return
    st.subheader(f"Items in '{current_list_name}':")
    for item in current_list['items']:
        st.write(f"- {item['name']}")
    st.markdown("---")
    st.success("Ready to checkout! (MVP: This would redirect to the supermarket's site)")
    if st.button("Baskit (Go to Checkout)"):
        st.info("[MVP] Redirecting to supermarket checkout...") 