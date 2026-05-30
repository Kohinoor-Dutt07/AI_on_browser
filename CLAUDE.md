# AI Browser Agent

A Python-based AI agent that uses an LLM of your choice to control a browser and perform web tasks autonomously. Think of it as a digital assistant that can browse the web, analyze content, and execute tasks like a human would.

## Project Overview

**Purpose**: Build an AI agent that can autonomously browse the web, analyze content, make human-like decisions, and perform tasks like:
- Signing up for websites and managing credentials
- Searching for trends and information
- Finding trending products on e-commerce sites
- Scraping and analyzing social media
- Extracting data from pages
- Analyzing videos and their success factors

**User**: This is your personal AI browser assistant - configurable for any LLM, any browser, with full control via .env

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     AI Browser Agent                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Config      │  │ Task        │  │ Browser Controller  │  │
│  │ (.env)      │  │ Engine      │  │ (Playwright)        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ LLM Client  │  │ Credential  │  │ Memory/History     │  │
│  │ (any model) │  │ Manager     │  │ (task context)      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Key Files

| File | Purpose |
|------|---------|
| `.env.example` | Configuration template - copy to `.env` |
| `requirements.txt` | Python dependencies |
| `src/llm_client.py` | LLM connection factory (OpenAI, Anthropic, Ollama) |
| `src/browser_controller.py` | Playwright browser automation |
| `src/task_engine.py` | Task planning & human-like decision making |
| `main.py` | CLI entry point |

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install
   ```

2. Configure `.env`:
   ```bash
   copy .env.example .env
   # Edit .env with your preferred LLM and settings
   ```

3. Run tasks:
   ```bash
   python main.py "search for AI trends on Google"
   python main.py "find trending products on Amazon"
   python main.py "analyze this video: https://youtube.com/..."
   ```

## Configuration

All settings in `.env`:

- **LLM**: Provider (openai/anthropic/ollama), API keys, model names
- **Browser**: Chrome/Edge/Firefox, headless mode, viewport
- **Stealth**: Detection avoidance settings
- **Credentials**: Site login info (CREDENTIALS_SITENAME=user|pass)
- **Behavior**: Delays, typing speed

## Current Status

- [x] Project structure created
- [x] LLM client factory
- [x] Browser controller
- [x] Task engine
- [x] Credential manager
- [x] Main entry point
- [ ] Testing

## Usage

```bash
# Test the browser works
python main.py --test-browser

# Run a simple task
python main.py "search for AI trends on Google"

# Interactive mode (type tasks manually)
python main.py --interactive

# Run in headless mode
python main.py --headless "find trending products on Amazon"
```

## Notes for Future Work

- Browser stealth settings in .env - configurable
- Credentials stored in .env (not encrypted - keep secure)
- Video analysis uses transcript/summary approach, not actual video processing
- Start with one LLM, switch via .env