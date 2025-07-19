# BaskIt - Smart Shopping List Manager

A modern, AI-powered shopping list manager that understands natural language commands and supports multiple input methods:
- Text input with natural language processing
- Voice input for hands-free operation
- Image input for visual item addition

## Features
- 🤖 Natural Language Commands: "Add two tomatoes", "Create party list", "Switch to groceries"
- 📝 Multiple List Management: Create and manage multiple shopping lists
- 🎤 Voice Recognition: Add items hands-free using voice commands
- 📷 Image Upload: Add items by uploading or pasting images
- 🛒 Smart Cart Management: Easily update quantities and remove items
- ⚡ Fallback Mode: Works even without internet (using rule-based parsing)

## Setup

### Prerequisites
- Python 3.8 or higher
- Git
- OpenAI API key (for AI features)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd BaskIt
```

2. Create and activate a virtual environment:
```bash
# Windows (Git Bash)
python -m venv venv
source venv/Scripts/activate

# Linux/macOS
python -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the project root with your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

### Running the Application

Start the Streamlit app:
```bash
streamlit run app.py
```

The app will be available at:
- Local: http://localhost:8501
- Network: Check terminal output for network URL

## Usage Guide

### Text Commands
The app understands natural language commands. Examples:

1. Adding Items:
   - "Add two tomatoes"
   - "Buy 5 apples"
   - "Get some milk"

2. List Management:
   - "Create party list"
   - "Switch to groceries list"
   - "Delete old list"

3. Removing Items:
   - "Remove milk"
   - "I bought the eggs"

### Voice Input
1. Click the "Voice Input" tab
2. Click "Start Recording"
3. Speak your command clearly
4. The app will process your voice command

### Image Input
1. Click the "Image Input" tab
2. Either:
   - Upload an image file, or
   - Paste an image (Ctrl+V)
3. Confirm the item name and quantity

### Cart Management
- Use + and - buttons to adjust quantities
- Click the trash icon to remove items
- Use "Clear Cart" to remove all items
- Switch between lists using the dropdown

## Development

### Running Tests
```bash
pytest test_ai_parser.py -v
```

### Project Structure
- `app.py`: Main Streamlit application
- `ai_parser.py`: Natural language processing module
- `test_ai_parser.py`: Test suite
- `requirements.txt`: Project dependencies

### AI Parser
The app uses OpenAI's GPT-3.5-turbo for natural language understanding, with a rule-based fallback:
- Primary: GPT-3.5-turbo for complex command parsing
- Fallback: Rule-based parser when offline or for simple commands

## Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License
[Add your license information here] 