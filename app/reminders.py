import streamlit as st

def show(user):
    st.header("Smart Reminders")
    # Mock reminders for MVP
    reminders = [
        {"product": "Milk 1L", "reminder": "You usually buy this every week."},
        {"product": "Bread Whole Wheat", "reminder": "On sale at Rami Levi!"}
    ]
    for r in reminders:
        st.info(f"{r['product']}: {r['reminder']}") 