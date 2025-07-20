import streamlit as st
from transformers import pipeline

@st.cache_resource(show_spinner=False)
def get_classifier():
    """Gets the HuggingFace zero-shot classifier, cached for performance."""
    return pipeline("zero-shot-classification", model="valhalla/distilbart-mnli-12-1")

def ai_suggest_category(item_name):
    """Suggests a category for an item using a zero-shot classifier."""
    classifier = get_classifier()
    candidate_labels = [
        "Dairy", "Fruit", "Vegetable", "Meat", "Bread",
        "Cleaning Products", "Essentials", "Snacks", "Personal Care", "Other"
    ]
    result = classifier(item_name, candidate_labels)
    return result['labels'][0] if result['labels'] else 'Other' 