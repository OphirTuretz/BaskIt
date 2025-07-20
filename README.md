# 🛒 BaskIt

AI-powered grocery shopping assistant with Hebrew support - making your grocery list management smarter and more efficient.

## 🌟 Overview

BaskIt is a modern grocery list management application that leverages AI to understand natural language input in both English and Hebrew. It helps users maintain their shopping lists with intelligent item categorization and smart list management.

### Key Features

- 📝 Natural language input processing (Hebrew & English)
- 🤖 AI-powered item recognition and categorization
- 📋 Smart list management with categories
- 🔄 Full RTL (Right-to-Left) support for Hebrew
- 💾 Persistent storage with SQLAlchemy
- 📊 Comprehensive logging system

## 🚀 Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/OphirTuretz/BaskIt.git
   cd BaskIt
   ```

2. Create and activate Python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. Install the package in development mode:
   ```bash
   pip install -e .
   ```

6. Initialize the database:
   ```bash
   python -m baskit.db.init_db
   ```

7. Start the application:
   ```bash
   streamlit run src/baskit/web/app.py
   ```

## 🧪 Development

### Prerequisites

- Python 3.8 or higher
- SQLite (included in Python)
- Git

### Testing

Run the test suite:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=baskit tests/
```

### Project Structure

```
BaskIt/
├── src/baskit/
│   ├── ai/              # AI/NLP processing
│   ├── services/        # Business logic
│   ├── models/          # Database models
│   ├── web/            # Web interface
│   ├── db/             # Database management
│   └── utils/          # Shared utilities
├── tests/              # Test suite
├── requirements.txt    # Project dependencies
└── pyproject.toml     # Build configuration
```

## ⚙️ Configuration

Key environment variables:
- `USE_MOCK_AI`: Use mock AI responses (default: true)
- `LOG_LEVEL`: Logging level (default: INFO)
- `LOG_FILE`: Log file path (default: logs/baskit.log)
- `DATABASE_URL`: SQLite database path (default: baskit.db)

## 🤝 Contributing

1. Create a feature branch from `main`
2. Make your changes
3. Add or update tests as needed
4. Ensure all tests pass
5. Submit a pull request

### Pull Request Process

1. Update documentation as needed
2. Add your changes to CHANGELOG.md
3. Link any related issues
4. Request review from maintainers

## 📝 Versioning

We use [Semantic Versioning](https://semver.org/). See [CHANGELOG.md](CHANGELOG.md) for version history.

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.