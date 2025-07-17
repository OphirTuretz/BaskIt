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

3. Install the package in development mode:
   ```bash
   pip install -e .
   ```

4. Run the tests:
   ```bash
   pytest
   ```

5. Start the app:
   ```bash
   streamlit run src/baskit/web/app.py
   ```

## Project Structure

```
BaskIt/
├── src/
│   └── baskit/
│       ├── ai/              # AI/NLP components
│       │   └── text_to_item.py
│       ├── services/        # Business logic
│       │   └── list_manager.py
│       ├── utils/          # Shared utilities
│       │   └── logger.py
│       ├── web/           # Web application
│       │   ├── app.py
│       │   ├── pages/
│       │   └── assets/
│       ├── db/            # Database components
│       ├── __init__.py
│       └── config.py      # Environment configuration
├── tests/                 # Test mirror structure
│   ├── ai/
│   └── services/
├── logs/                  # Log files
├── pyproject.toml        # Build configuration
└── requirements.txt      # Python dependencies
```

## Development

- All code changes should have corresponding tests
- Run tests before committing: `pytest`
- Check logs in `logs/baskit.log`
- Use structured logging via `baskit.utils.logger.get_logger()`

## Environment Variables

The following environment variables can be configured:
- `USE_MOCK_APIS`: Set to "true" to use mock AI responses (default: true)
- `LOG_LEVEL`: Logging level (default: INFO)
- `LOG_FILE`: Log file path (default: logs/baskit.log)

## Contributing

1. Create a feature branch from `main`
2. Add tests for new functionality
3. Ensure all tests pass
4. Submit a pull request