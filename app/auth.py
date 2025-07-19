import streamlit as st

def login():
    if 'user' in st.session_state:
        return st.session_state['user']
    st.title("Login")
    username = st.text_input("Username")
    if st.button("Login") and username:
        st.session_state['user'] = {'username': username}
        return st.session_state['user']
    st.stop() 