import streamlit as st

def login():
    if 'user' in st.session_state:
        return st.session_state['user']
    st.title("Login")
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username")
        submitted = st.form_submit_button("Login")
        if submitted and username:
            # If user exists, restore their settings and skip onboarding
            if 'users' in st.session_state and username in st.session_state['users']:
                st.session_state['user'] = st.session_state['users'][username]
                st.session_state['onboarded'] = True
            else:
                st.session_state['user'] = {'username': username}
                st.session_state['onboarded'] = False
            return st.session_state['user']
    st.stop() 