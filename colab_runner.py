"""
AI Browser Agent - Single File Colab-Ready Version
Copy this entire file to Google Colab to test
"""
import os
import json
import asyncio
import time
from typing import List, Dict, Any, Optional

# =============================================================================
# CONFIGURATION - Edit these for Colab
# =============================================================================

# =============================================================================
# ⚠️ REQUIRED: Set your API key before running
# =============================================================================
# OPENAI_API_KEY = "sk-your-key-here"  # Replace with your actual key
# OR set in Colab: import os; os.environ["OPENAI_API_KEY"] = "sk-..."

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")  # Will use env var or empty

# Validate API key is set
if not OPENAI_API_KEY and LLM_PROVIDER in ["openai", "anthropic"]:
    print("⚠️ WARNING: No API key set! Set OPENAI_API_KEY or ANTHROPIC_API_KEY")

# Or use Anthropic
ANTHROPIC_API_KEY = ""
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"

# Choose provider: "openai", "anthropic", "ollama", or "openrouter"
LLM_PROVIDER = "openai"

# OpenRouter settings (if using openrouter)
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = "meta-llama/llama-3.1-8b-instruct"  # Or any model from OpenRouter

# Browser settings
HEADLESS = True  # Must be True for Colab
VIEWPORT_WIDTH = 1280
VIEWPORT_HEIGHT = 720

# =============================================================================
# LLM CLIENT
# =============================================================================

class LLMClient:
    """Base LLM client"""
    def chat(self, messages, tools=None):
        raise NotImplementedError

class OpenAIClient(LLMClient):
    def __init__(self, api_key, model="gpt-4o"):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def chat(self, messages, tools=None):
        params = {"model": self.model, "messages": messages}
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"
        response = self.client.chat.completions.create(**params)

        choice = response.choices[0]
        result = {"content": choice.message.content or "", "finish_reason": choice.finish_reason}

        if choice.message.tool_calls:
            result["tool_calls"] = [
                {"id": tc.id, "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in choice.message.tool_calls
            ]
        return result

class AnthropicClient(LLMClient):
    def __init__(self, api_key, model="claude-sonnet-4-20250514"):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def chat(self, messages, tools=None):
        converted = [{"role": m["role"], "content": m["content"]} for m in messages if m["role"] != "system"]
        params = {"model": self.model, "messages": converted, "max_tokens": 4096}

        response = self.client.messages.create(**params)
        result = {"content": "", "finish_reason": "stop"}

        for block in response.content:
            if block.type == "text":
                result["content"] += block.text
            elif block.type == "tool_use":
                result["tool_calls"] = [{
                    "id": block.id,
                    "function": {"name": block.name, "arguments": json.dumps(block.input)}
                }]
        return result

class OllamaClient(LLMClient):
    def __init__(self, base_url="http://localhost:11434", model="llama3"):
        self.base_url = base_url
        self.model = model

    def chat(self, messages, tools=None):
        import requests
        response = requests.post(f"{self.base_url}/api/chat",
            json={"model": self.model, "messages": messages, "stream": False})
        data = response.json()
        return {"content": data.get("message", {}).get("content", ""), "finish_reason": "stop"}

class OpenRouterClient(LLMClient):
    """OpenRouter - unified API for many LLM providers"""
    def __init__(self, api_key, model="meta-llama/llama-3.1-8b-instruct"):
        from openai import OpenAI
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        self.model = model

    def chat(self, messages, tools=None):
        params = {"model": self.model, "messages": messages}
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"
        response = self.client.chat.completions.create(**params)

        choice = response.choices[0]
        result = {"content": choice.message.content or "", "finish_reason": choice.finish_reason}

        if choice.message.tool_calls:
            result["tool_calls"] = [
                {"id": tc.id, "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in choice.message.tool_calls
            ]
        return result

def create_llm_client():
    """Factory to create LLM client"""
    if LLM_PROVIDER == "openai":
        key = OPENAI_API_KEY or os.getenv("OPENAI_API_KEY", "")
        if not key:
            raise ValueError("OPENAI_API_KEY not set")
        return OpenAIClient(key, "gpt-4o")

    elif LLM_PROVIDER == "anthropic":
        key = ANTHROPIC_API_KEY or os.getenv("ANTHROPIC_API_KEY", "")
        if not key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        return AnthropicClient(key, ANTHROPIC_MODEL)

    elif LLM_PROVIDER == "openrouter":
        key = OPENROUTER_API_KEY or os.getenv("OPENROUTER_API_KEY", "")
        if not key:
            raise ValueError("OPENROUTER_API_KEY not set")
        return OpenRouterClient(key, OPENROUTER_MODEL)

    elif LLM_PROVIDER == "ollama":
        return OllamaClient()

    else:
        raise ValueError(f"Unknown provider: {LLM_PROVIDER}. Use: openai, anthropic, openrouter, ollama")

# =============================================================================
# BROWSER TOOLS DEFINITION
# =============================================================================

BROWSER_TOOLS = [
    {"type": "function", "function": {
        "name": "navigate", "description": "Navigate to a URL",
        "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}
    }},
    {"type": "function", "function": {
        "name": "click", "description": "Click an element",
        "parameters": {"type": "object", "properties": {"selector": {"type": "string"}}, "required": ["selector"]}
    }},
    {"type": "function", "function": {
        "name": "type_text", "description": "Type into an input",
        "parameters": {"type": "object", "properties": {"selector": {"type": "string"}, "text": {"type": "string"}}, "required": ["selector", "text"]}
    }},
    {"type": "function", "function": {
        "name": "get_page_content", "description": "Get page text",
        "parameters": {"type": "object", "properties": {}}
    }},
    {"type": "function", "function": {
        "name": "screenshot", "description": "Take screenshot",
        "parameters": {"type": "object", "properties": {}}
    }},
    {"type": "function", "function": {
        "name": "scroll", "description": "Scroll page",
        "parameters": {"type": "object", "properties": {"direction": {"type": "string", "enum": ["up", "down"]}}}
    }},
    {"type": "function", "function": {
        "name": "search_google", "description": "Search Google",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
    }},
]

# =============================================================================
# BROWSER CONTROLLER
# =============================================================================

class BrowserController:
    """Playwright-based browser automation"""

    def __init__(self, headless=True):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def start(self):
        from playwright.async_api import async_playwright
        self.playwright = await async_playwright().start()

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-setuid-sandbox",
        ]

        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=launch_args
        )

        self.context = await self.browser.new_context(
            viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT}
        )

        # Stealth
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US']});
        """)

        self.page = await self.context.new_page()
        self.page.set_default_timeout(30000)
        print("[Browser] Started")

    async def navigate(self, url):
        await asyncio.sleep(0.5)
        await self.page.goto(url, wait_until="domcontentloaded")
        return {"success": True, "url": self.page.url}

    async def click(self, selector):
        await asyncio.sleep(0.5)
        try:
            await self.page.click(selector)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def type_text(self, selector, text):
        await asyncio.sleep(0.5)
        try:
            await self.page.fill(selector, "")
            await self.page.type(selector, text, delay=30)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_page_content(self):
        try:
            content = await self.page.evaluate("document.body.innerText") or ""
            return {"success": True, "content": content[:3000] if content else ""}  # Limit length
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def screenshot(self):
        try:
            path = f"screenshot_{int(time.time())}.png"
            await self.page.screenshot(path=path, full_page=True)
            return {"success": True, "path": path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def scroll(self, direction="down"):
        await self.page.evaluate(f"window.scrollBy(0, {'500' if direction == 'down' else '-500'})")
        return {"success": True}

    async def search_google(self, query):
        return await self.navigate(f"https://www.google.com/search?q={query.replace(' ', '+')}")

    async def close(self):
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        print("[Browser] Closed")

# =============================================================================
# TOOL HANDLER
# =============================================================================

async def handle_tool(controller, tool_name, args):
    if tool_name == "navigate":
        return await controller.navigate(args["url"])
    elif tool_name == "click":
        return await controller.click(args["selector"])
    elif tool_name == "type_text":
        return await controller.type_text(args["selector"], args["text"])
    elif tool_name == "get_page_content":
        return await controller.get_page_content()
    elif tool_name == "screenshot":
        return await controller.screenshot()
    elif tool_name == "scroll":
        return await controller.scroll(args.get("direction", "down"))
    elif tool_name == "search_google":
        return await controller.search_google(args["query"])
    else:
        return {"success": False, "error": f"Unknown tool: {tool_name}"}

# =============================================================================
# TASK ENGINE
# =============================================================================

class TaskEngine:
    """AI task execution engine"""

    def __init__(self):
        self.llm = create_llm_client()
        self.conversation = []

    def get_system_prompt(self):
        return """You are an AI browser assistant. Plan steps to complete the user's task.
Execute one action at a time using the available tools.
After each action, explain what happened and decide next step.
When task is complete, summarize what was done."""

    async def execute(self, controller, task):
        self.conversation = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": f"Task: {task}\n\nPlan and execute this task step by step."}
        ]

        for i in range(10):  # Max 10 iterations
            response = self.llm.chat(self.conversation, BROWSER_TOOLS)

            if response.get("tool_calls"):
                for tc in response["tool_calls"]:
                    tool_name = tc["function"]["name"]
                    args = json.loads(tc["function"]["arguments"])

                    result = await handle_tool(controller, tool_name, args)
                    self.conversation.append({
                        "role": "assistant",
                        "content": f"Action: {tool_name}({json.dumps(args)})\nResult: {json.dumps(result)}"
                    })
                    self.conversation.append({
                        "role": "user",
                        "content": "Continue or finish?"
                    })

                    print(f"  [{tool_name}] {result.get('success', False)}")
            else:
                print("\n" + "="*50)
                print("RESULT:")
                print("="*50)
                print(response.get("content", "Done"))
                print("="*50)
                break

        return {"success": True, "iterations": i + 1}

# =============================================================================
# MAIN FUNCTION - Run this in Colab
# =============================================================================

async def run_task(task: str):
    """Run an AI browser task"""
    print(f"\n{'='*50}")
    print(f"Starting: {task}")
    print(f"{'='*50}\n")

    controller = BrowserController(headless=HEADLESS)
    engine = TaskEngine()

    try:
        await controller.start()
        result = await engine.execute(controller, task)
        print(f"\n✓ Task completed in {result.get('iterations', '?')} steps")
        return result
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return {"success": False, "error": str(e)}
    finally:
        await controller.close()

# =============================================================================
# COLAB SETUP & RUN
# =============================================================================

def setup_colab():
    """Install dependencies for Colab"""
    print("Installing dependencies...")
    import subprocess
    subprocess.run(["pip", "install", "playwright", "openai", "anthropic", "requests"], check=True)
    subprocess.run(["playwright", "install", "chromium"], check=True)
    subprocess.run(["apt-get", "install", "-y", "libglib2.0-0", "libnss3", "libnspr4", "libdbus-1-3"], check=True)
    print("✓ Dependencies installed")

# =============================================================================
# EXAMPLE USAGE - For Google Colab / Jupyter
# =============================================================================

# ⚠️ IMPORTANT: In Colab/Jupyter, use this instead of asyncio.run()

def run_in_colab(task: str):
    """Run task in Jupyter/Colab - handles event loop automatically"""
    try:
        # Try to get existing loop
        loop = asyncio.get_running_loop()
        # If we're in a loop, create a task
        import nest_asyncio
        nest_asyncio.apply()
        return asyncio.run(run_task(task))
    except RuntimeError:
        # No running loop - safe to use asyncio.run
        return asyncio.run(run_task(task))

# Example usage in Colab - choose ONE:
# ----------------------------------------------------------
# Option 1: Just call the function directly (recommended)
# result = run_in_colab("search for AI trends on Google")

# Option 2: Use await if already in async context
# await run_task("search for AI trends on Google")

# Option 3: Run inline in cell (for quick testing)
# ----------------------------------------------------------
# Copy paste these lines in separate Colab cells:

# Cell 1: Setup
# import sys; sys.path.insert(0, '.')
# from colab_runner import *

# Cell 2: Run (pick one)
# run_in_colab("search for AI trends on Google")
# run_in_colab("find trending products on Amazon")
# run_in_colab("go to youtube and search for python tutorials")

# NOTE: If you get error about event loop, install nest_asyncio:
# !pip install nest_asyncio
# And add: import nest_asyncio; nest_asyncio.apply()

if __name__ == "__main__":
    # For local testing (not in Jupyter)
    asyncio.run(run_task("search for AI trends on Google"))