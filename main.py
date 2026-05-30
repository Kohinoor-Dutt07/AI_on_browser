"""
AI Browser Agent - Main Entry Point

A Python-based AI agent that uses an LLM to control a browser and perform web tasks autonomously.
"""
import os
import sys
import asyncio
import argparse
from dotenv import load_dotenv
import logging
import colorlog

# Load environment variables
load_dotenv()

# GitHub Codespaces Sandbox Safeguard: Force headless mode if running in a cloud container
if os.getenv("CODESPACES") == "true":
    os.environ["HEADLESS"] = "true"

# Setup logging
logging_config = {
    "format": "%(asctime)s - %(levelname)s - %(message)s",
    "datefmt": "%H:%M:%S",
}

log_level = os.getenv("LOG_LEVEL", "INFO").upper()
if log_level == "DEBUG":
    logging_config["level"] = logging.DEBUG
else:
    logging_config["level"] = logging.INFO

colorlog.basicConfig(**logging_config)
logger = colorlog.getLogger(__name__)


async def test_browser(headless: bool):
    """Quick test to verify browser works"""
    from src.browser_controller import BrowserController

    logger.info("Testing browser controller...")
    controller = BrowserController(headless=headless)

    try:
        await controller.start()
        logger.info("Browser started successfully")

        # Test navigation
        result = await controller.navigate("https://example.com")
        logger.info(f"Navigation result: {result}")

        # Test screenshot
        ss = await controller.screenshot("test.png")
        logger.info(f"Screenshot: {ss}")

        # Test search
        search = await controller.search_google("Python programming")
        logger.info(f"Search result: {search}")

        await controller.wait(2)

        logger.info("Browser test completed successfully!")
        return True

    except Exception as e:
        logger.error(f"Browser test failed: {e}")
        return False

    finally:
        await controller.close()


async def run_task(task: str, headless: bool):
    """Run a task with the AI browser agent"""
    from src.browser_controller import BrowserController
    from src.task_engine import TaskEngine

    logger.info(f"Starting task: {task}")

    # Initialize
    controller = BrowserController(headless=headless)
    engine = TaskEngine()

    try:
        # Start browser
        await controller.start()
        logger.info("Browser started")

        # Execute task
        result = await engine.execute_task(controller, task)

        if result.get("success"):
            logger.info("Task completed successfully!")
            if result.get("final_message"):
                print("\n" + "="*50)
                print("RESULT:")
                print("="*50)
                print(result["final_message"])
        else:
            logger.error(f"Task failed: {result.get('error')}")

        # Optionally analyze the final page
        if result.get("success"):
            analysis = await engine.analyze_page(controller, "general")
            if analysis.get("success"):
                print("\n" + "="*50)
                print("PAGE ANALYSIS:")
                print("="*50)
                print(analysis.get("analysis", "No analysis"))

        return result

    except Exception as e:
        logger.error(f"Error running task: {e}")
        return {"success": False, "error": str(e)}

    finally:
        await controller.close()


async def interactive_mode(headless: bool):
    """Run in interactive mode - enter tasks via console"""
    from src.browser_controller import BrowserController
    from src.task_engine import TaskEngine

    logger.info("Starting interactive mode. Type 'exit' to quit.")

    controller = BrowserController(headless=headless)
    engine = TaskEngine()

    try:
        await controller.start()
        logger.info("Browser started - ready for tasks!")

        while True:
            task = input("\nEnter task: ").strip()
            if task.lower() in ["exit", "quit", "q"]:
                break

            if not task:
                continue

            result = await engine.execute_task(controller, task)
            print("\n" + "="*50)
            if result.get("success"):
                print(result.get("final_message", "Task completed"))
            else:
                print(f"Error: {result.get('error')}")
            print("="*50)

    except KeyboardInterrupt:
        logger.info("Interrupted")

    finally:
        await controller.close()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="AI Browser Agent - Use AI to control a browser and complete web tasks"
    )
    parser.add_argument(
        "task",
        nargs="?",
        help="Task to execute (e.g., 'search for AI trends')"
    )
    parser.add_argument(
        "--test-browser",
        action="store_true",
        help="Run browser test"
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Run in interactive mode"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,  # Default to True to protect remote server environments
        help="Run browser in headless mode"
    )

    args = parser.parse_args()

    # Sync environment flag state
    if args.headless or os.getenv("HEADLESS") == "true":
        os.environ["HEADLESS"] = "true"
        is_headless = True
    else:
        is_headless = False

    if args.test_browser:
        success = asyncio.run(test_browser(headless=is_headless))
        sys.exit(0 if success else 1)

    if args.interactive:
        asyncio.run(interactive_mode(headless=is_headless))
        sys.exit(0)

    if args.task:
        result = asyncio.run(run_task(args.task, headless=is_headless))
        sys.exit(0 if result.get("success") else 1)

    # No arguments provided
    parser.print_help()
    print("\nExamples:")
    print("  python main.py 'search for Python tutorials on YouTube'")
    print("  python main.py 'find trending tech products on Amazon'")
    print("  python main.py --interactive")
    print("  python main.py --test-browser")


if __name__ == "__main__":
    main()