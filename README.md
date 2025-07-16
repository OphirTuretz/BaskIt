# 🛒 BaskIt

AI-powered grocery shopping assistant with Hebrew support.

## Features (Phase 1)

- 📝 Hebrew text input for adding items to your list
- 🤖 Mock AI parser (simulates natural language understanding)
- 📋 In-memory list management
- 📊 Structured logging with rotation
- 🔄 RTL (Right-to-Left) UI support

## Setup

1. Create a Python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file:
   ```
   USE_MOCK_APIS=true
   LOG_LEVEL=DEBUG
   LOG_FILE=logs/baskit.log
   ```

4. Run the tests:
   ```bash
   pytest
   ```

5. Start the app:
   ```bash
   streamlit run app.py
   ```

## Project Structure

```
BaskIt/
├── ai/
│   └── text_to_item.py     # Mock text parser
├── services/
│   └── list_manager.py     # In-memory list management
├── utils/
│   └── logger.py           # Logging configuration
├── tests/                  # Test mirror structure
├── app.py                  # Streamlit UI
├── config.py              # Environment configuration
└── requirements.txt       # Python dependencies
```

## Development

- All code changes should have corresponding tests
- Run tests before committing: `pytest`
- Check logs in `logs/baskit.log`
- Use structured logging via `utils.logger.get_logger()`