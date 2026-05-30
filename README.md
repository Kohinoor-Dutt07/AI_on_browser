# AI Browser Agent

A Python-based AI agent that uses an LLM of your choice to control a browser and perform web tasks autonomously. Think of it as a digital assistant that can browse the web, analyze content, and execute tasks like a human would.

## Features

- **Multi-LLM Support**: Works with OpenAI (GPT), Anthropic (Claude), and Ollama (local LLMs)
- **Human-like Browsing**: Implements random delays, stealth modes, and adaptive decision-making
- **Task Automation**: Can perform complex web tasks like searching, form filling, data extraction, and more
- **Page Analysis**: Multiple analysis modes (general, products, people, trends, video)
- **Credential Management**: Secure handling of website logins (with encryption upgrade)
- **Cross-Platform**: Works on Windows, macOS, and Linux (including WSL)
- **Headless Operation**: Can run without a visible browser for server environments

## Architecture

```
AI Browser Agent
├── Config (.env)
├── Task Engine (task_engine.py) 
├── LLM Client (llm_client.py)
├── Browser Controller (browser_controller.py)
├── Credential Manager (src/credential_manager.py)
└── Main Entry Point (main.py)
```

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd AI-Browser-Agent
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install
   ```

3. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your preferred LLM provider and settings
   ```

## Usage

### Basic Tasks
```bash
# Search for information
python main.py "search for AI trends on Google"

# Find products
python main.py "find trending tech products on Amazon under $500"

# Analyze a video
python main.py "analyze this video: https://youtube.com/watch?v=..."
```

### Interactive Mode
```bash
python main.py --interactive
# Then type tasks manually, e.g.:
# "search for Python tutorials on YouTube"
```

### Headless Mode (for servers/WSL)
```bash
python main.py --headless "search for climate change news"
```

### Browser Test
```bash
python main.py --test-browser
```

## Configuration

All settings are in `.env`:

### LLM Settings
- `LLM_PROVIDER`: openai, anthropic, or ollama
- `OPENAI_API_KEY`: Your OpenAI API key
- `OPENAI_MODEL`: Model name (default: gpt-4o)
- `ANTHROPIC_API_KEY`: Your Anthropic API key
- `ANTHROPIC_MODEL`: Model name (default: claude-sonnet-4-20250514)
- `OLLAMA_BASE_URL`: Ollama server URL (default: http://localhost:11434)
- `OLLAMA_MODEL`: Model name (default: llama3)

### Browser Settings
- `BROWSER`: chrome, firefox, or edge (default: chrome)
- `HEADLESS`: true or false (default: false)
- `VIEWPORT_WIDTH`: Browser width (default: 1280)
- `VIEWPORT_HEIGHT`: Browser height (default: 720)
- `USER_AGENT`: Custom user agent string (optional)
- `STEALTH_MODE`: true or false (default: true)
- `MIN_DELAY`: Minimum delay between actions in seconds (default: 1)
- `MAX_DELAY`: Maximum delay between actions in seconds (default: 3)
- `SCREENSHOT_DIR`: Directory for screenshots (default: screenshots)

### Credential Settings
- Format: `CREDENTIALS_SITENAME=username|password`
- Example: `CREDENTIALS_LINKEDIN=john@example.com|mypassword123`
- Site name is converted to uppercase with dots and hyphens replaced by underscores

### Logging
- `LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR (default: INFO)

## Current Capabilities

The agent can currently:
- Navigate to websites and interact with elements (click, type, scroll)
- Perform Google searches
- Extract page content (text or HTML)
- Take screenshots
- Execute custom JavaScript
- Analyze pages in multiple modes:
  - General: Understand page purpose and main content
  - Products: Extract product details (name, price, description, ratings)
  - People: Identify profiles with name, title, company, bio
  - Trends: Detect popular topics and trending content
  - Video: Analyze video pages (title, thumbnail, engagement factors)
- Make human-like decisions using an LLM to plan and execute tasks
- Handle website credentials (with planned encryption upgrade)

## Planned Improvements

See [UPGRADES.md](UPGRADES.md) for detailed roadmap of planned enhancements including:
- Encrypted credential storage
- Comprehensive test suite
- Advanced stealth techniques
- Persistent memory system
- Video processing capabilities
- Rate limiting and quota management
- Structured logging and monitoring
- Configuration validation with Pydantic

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Playwright](https://playwright.dev/) for browser automation
- [python-dotenv](https://pypi.org/project/python-dotenv/) for environment management
- [colorlog](https://pypi.org/project/colorlog/) for colored logging
- The Anthropic, OpenAI, and Ollama teams for their LLM APIs