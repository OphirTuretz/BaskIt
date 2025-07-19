import streamlit as st

def show(user):
    st.header("Purchase History")
    # Mock data for MVP
    history = [
        {"date": "2024-06-01", "list": "My Groceries", "total": 45.0, "chain": "Shufersal"},
        {"date": "2024-05-25", "list": "Fruits & Veg", "total": 32.5, "chain": "Victory"}
    ]
    st.table(history) 