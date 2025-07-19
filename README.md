# Groceries App MVP

An AI-driven groceries shopping cart app that allows users to manage shopping lists, compare prices, and add items by text, voice, or image. Built with Streamlit.

## Features
- Social login authentication
- Multiple shopping lists (create, switch, edit, delete)
- Add items by text, voice, or image
- Price comparison between supermarket chains (mock data)
- Product dictionary with icons
- Purchase history
- Recurring deliveries
- Smart reminders (in-app)
- Dietary preferences/restrictions
- Accessibility (basic)

## Supermarket Chains
- Shufersal
- Rami Levi
- Victory
- Tiv-Ta'am

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the app:
   ```bash
   streamlit run app/main.py
   ```

## Notes
- Voice and image recognition are mocked for MVP.
- Product and price data are mock data for demonstration.
- For Google Vision API, see the utils/image.py file for integration instructions. 