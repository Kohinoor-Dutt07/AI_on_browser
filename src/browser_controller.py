"""
Browser Controller - Playwright-based browser automation
"""
import os
import asyncio
import random
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

try:
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext
except ImportError:
    print("Playwright not installed. Run: pip install playwright && playwright install")


class BrowserController:
    """Controls browser automation with Playwright"""

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

        # Config
        self.browser_type = os.getenv("BROWSER", "chrome").lower()
        self.viewport_width = int(os.getenv("VIEWPORT_WIDTH", 1280))
        self.viewport_height = int(os.getenv("VIEWPORT_HEIGHT", 720))
        self.user_agent = os.getenv("USER_AGENT", "")
        self.stealth = os.getenv("STEALTH_MODE", "true").lower() == "true"
        self.min_delay = float(os.getenv("MIN_DELAY", 1))
        self.max_delay = float(os.getenv("MAX_DELAY", 3))
        self.screenshot_dir = os.getenv("SCREENSHOT_DIR", "screenshots")

        # Ensure screenshot directory exists
        Path(self.screenshot_dir).mkdir(exist_ok=True)

    async def start(self):
        """Initialize the browser"""
        self.playwright = await async_playwright().start()

        if self.browser_type == "chrome":
            browser_launcher = self.playwright.chromium
        elif self.browser_type == "firefox":
            browser_launcher = self.playwright.firefox
        elif self.browser_type == "edge":
            browser_launcher = self.playwright.chromium  # Edge uses Chromium
        else:
            browser_launcher = self.playwright.chromium

        # Build launch args
        launch_args = []

        if self.stealth:
            # Anti-detection arguments
            launch_args.extend([
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ])

        self.browser = await browser_launcher.launch(
            headless=self.headless,
            args=launch_args,
            ignore_default_args=["--enable-automation"] if self.stealth else []
        )

        # Create context
        context_options = {
            "viewport": {"width": self.viewport_width, "height": self.viewport_height},
        }

        if self.user_agent:
            context_options["user_agent"] = self.user_agent

        self.context = await self.browser.new_context(**context_options)

        # Apply stealth if enabled
        if self.stealth:
            await self._apply_stealth()

        # Create page
        self.page = await self.context.new_page()

        # Set default timeout
        self.page.set_default_timeout(30000)

    async def _apply_stealth(self):
        """Apply stealth modifications to avoid detection"""
        # Remove webdriver property
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        # Add plugins
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
        """)

        # Add languages
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
        """)

    async def _random_delay(self):
        """Wait a random time between actions"""
        delay = random.uniform(self.min_delay, self.max_delay)
        await asyncio.sleep(delay)

    async def navigate(self, url: str) -> Dict[str, Any]:
        """Navigate to a URL"""
        await self._random_delay()
        try:
            response = await self.page.goto(url, wait_until="domcontentloaded")
            return {
                "success": True,
                "url": self.page.url,
                "status": response.status if response else None,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def click(self, selector: str) -> Dict[str, Any]:
        """Click on an element"""
        await self._random_delay()
        try:
            await self.page.click(selector)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def type_text(self, selector: str, text: str, clear_first: bool = True) -> Dict[str, Any]:
        """Type text into an input field"""
        await self._random_delay()
        try:
            if clear_first:
                await self.page.fill(selector, "")
            await self.page.type(selector, text, delay=random.randint(20, 50))
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_page_content(self, format: str = "text") -> Dict[str, Any]:
        """Get the page content"""
        try:
            if format == "html":
                content = await self.page.content()
            else:
                content = await self.page.evaluate("""
                    document.body.innerText
                """)
            return {"success": True, "content": content}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def screenshot(self, path: Optional[str] = None) -> Dict[str, Any]:
        """Take a screenshot"""
        try:
            if not path:
                filename = f"screenshot_{random.randint(1000, 9999)}.png"
                path = os.path.join(self.screenshot_dir, filename)

            await self.page.screenshot(path=path, full_page=True)
            return {"success": True, "path": path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def scroll(self, direction: str = "down", amount: int = 500) -> Dict[str, Any]:
        """Scroll the page"""
        await self._random_delay()
        try:
            if direction == "up":
                await self.page.evaluate(f"window.scrollBy(0, -{amount})")
            else:
                await self.page.evaluate(f"window.scrollBy(0, {amount})")
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def wait(self, seconds: float) -> Dict[str, Any]:
        """Wait for specified seconds"""
        await asyncio.sleep(seconds)
        return {"success": True}

    async def find_element(self, selector: str) -> Dict[str, Any]:
        """Find an element and get its details"""
        try:
            element = await self.page.query_selector(selector)
            if not element:
                return {"success": False, "error": "Element not found"}

            # Get various properties
            info = await element.evaluate("""
                el => ({
                    tagName: el.tagName,
                    text: el.innerText,
                    href: el.href,
                    src: el.src,
                    visible: el.offsetParent !== null,
                })
            """)
            return {"success": True, "element": info}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def search_google(self, query: str) -> Dict[str, Any]:
        """Search Google for a query"""
        encoded_query = query.replace(" ", "+")
        return await self.navigate(f"https://www.google.com/search?q={encoded_query}")

    async def execute_script(self, script: str) -> Dict[str, Any]:
        """Execute custom JavaScript"""
        try:
            result = await self.page.evaluate(script)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_page_title(self) -> str:
        """Get the page title"""
        return await self.page.title()

    async def get_current_url(self) -> str:
        """Get current URL"""
        return self.page.url

    async def close(self):
        """Close the browser"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def new_tab(self, url: str = "about:blank") -> Dict[str, Any]:
        """Open a new tab"""
        try:
            new_page = await self.context.new_page()
            await new_page.goto(url)
            return {"success": True, "page": new_page}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Credential management
    async def login(self, site: str, credentials: Dict[str, str]) -> Dict[str, Any]:
        """Attempt to login to a site (simplified - requires site-specific logic)"""
        # This would need to be customized per-site
        return {"success": False, "error": "Site-specific login not implemented"}


# Tool wrapper functions for LLM function calling
async def handle_tool_call(controller: BrowserController, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle tool calls from LLM"""

    if tool_name == "navigate":
        return await controller.navigate(args["url"])
    elif tool_name == "click":
        return await controller.click(args["selector"])
    elif tool_name == "type":
        return await controller.type_text(args["selector"], args["text"])
    elif tool_name == "get_page_content":
        return await controller.get_page_content(args.get("format", "text"))
    elif tool_name == "screenshot":
        return await controller.screenshot(args.get("path"))
    elif tool_name == "scroll":
        return await controller.scroll(args.get("direction", "down"), args.get("amount", 500))
    elif tool_name == "wait":
        return await controller.wait(args["seconds"])
    elif tool_name == "find_element":
        return await controller.find_element(args["selector"])
    elif tool_name == "search_google":
        return await controller.search_google(args["query"])
    else:
        return {"success": False, "error": f"Unknown tool: {tool_name}"}