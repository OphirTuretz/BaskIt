import streamlit as st

def show_onboarding(user):
    # Skip onboarding if user already exists in session_state['users']
    if 'users' in st.session_state and user['username'] in st.session_state['users']:
        st.session_state['user'] = st.session_state['users'][user['username']]
        st.session_state['onboarded'] = True
        return False
    if st.session_state.get('onboarded'):
        return False
    st.title("Welcome to Groceries App!")
    st.write("Let's set up your preferences.")
    chains = ["Shufersal", "Rami Levi", "Victory", "Tiv-Ta'am"]
    default_chain = st.selectbox("Default supermarket chain", chains)
    favorite_chains = st.multiselect("Other favorite chains", chains, default=[default_chain])
    delivery_day = st.selectbox("Default delivery day", ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
    delivery_time = st.selectbox("Default delivery time window", ["08:00-12:00", "12:00-16:00", "16:00-20:00"])
    payment_method = st.selectbox("Payment method", ["Credit Card", "PayPal", "Cash on Delivery"])
    address = st.text_input("Default delivery address")
    dietary = st.text_area("Dietary preferences/restrictions (e.g. allergies, vegan, keto)")
    default_list = st.text_input("Default shopping list name", value="My Groceries")
    if st.button("Save and Continue"):
        st.session_state['onboarded'] = True
        st.session_state['user'].update({
            'default_chain': default_chain,
            'favorite_chains': favorite_chains,
            'delivery_day': delivery_day,
            'delivery_time': delivery_time,
            'payment_method': payment_method,
            'address': address,
            'dietary': dietary,
            'default_list': default_list
        })
        # Always save user to users dict
        if 'users' not in st.session_state:
            st.session_state['users'] = {}
        st.session_state['users'][user['username']] = st.session_state['user']
        return False
    return True

def show_settings(user):
    st.title("Settings")
    st.write("Update your preferences below.")
    show_onboarding(user) 