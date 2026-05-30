"""
Task Engine - Plans tasks and makes human-like decisions
"""
import json
import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from src.llm_client import create_llm_client, LLMClient, BROWSER_TOOLS

load_dotenv()


class TaskEngine:
    """
    AI-powered task planning and execution engine.
    Makes decisions like a human would, not a checklist.
    """

    def __init__(self):
        self.llm: LLMClient = create_llm_client()
        self.tools = BROWSER_TOOLS
        self.conversation_history: List[Dict[str, str]] = []
        self.task_history: List[Dict[str, Any]] = []
        self.max_iterations = int(os.getenv("MAX_ITERATIONS", "10"))

    def _get_system_prompt(self) -> str:
        """Get the system prompt that defines the AI's behavior"""
        return """You are an AI browser assistant that controls a web browser to complete tasks.

Your role:
- You are helpful, curious, and thorough
- You analyze web pages like a human would - looking at layout, context, and meaning
- You don't just check boxes - you understand and interpret content
- You adapt when things don't go as expected
- You take screenshots to understand visual context

Guidelines:
1. When given a task, plan the steps needed to accomplish it
2. Take actions one at a time and observe results
3. If something isn't working, try a different approach
4. Analyze content thoughtfully, not just mechanically
5. Remember what you've done - learn from failures
6. When you see interesting or relevant information, note it

You have access to browser tools:
- navigate(url): Go to a webpage
- click(selector): Click an element
- type(selector, text): Type into an input
- get_page_content(format): Get page text or HTML
- screenshot(path): Take a screenshot
- scroll(direction, amount): Scroll up/down
- wait(seconds): Wait briefly
- find_element(selector): Get element details
- search_google(query): Search Google

After each action, explain what you did and what you observed.
Then decide on the next step.

When task is complete, provide a summary of what was accomplished."""

    async def execute_task(self, controller, task: str) -> Dict[str, Any]:
        """Execute a task using the browser and LLM"""

        # Initialize conversation with system prompt
        self.conversation_history = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": f"TASK: {task}\n\nPlease begin by planning the steps to accomplish this task."}
        ]

        iteration = 0
        final_result = {"success": False, "iterations": 0, "actions": []}

        while iteration < self.max_iterations:
            iteration += 1
            final_result["iterations"] = iteration

            # Get LLM response with tools
            try:
                response = self.llm.chat(
                    messages=self.conversation_history,
                    tools=self.tools
                )
            except Exception as e:
                return {"success": False, "error": f"LLM Error: {str(e)}"}

            # Check for tool calls
            if response.get("tool_calls"):
                for tool_call in response["tool_calls"]:
                    tool_name = tool_call["function"]["name"]
                    tool_args = json.loads(tool_call["function"]["arguments"])

                    # Execute the tool
                    from src.browser_controller import handle_tool_call
                    result = await handle_tool_call(controller, tool_name, tool_args)

                    # Add tool result to conversation
                    tool_result_str = json.dumps(result)
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": f"Action: {tool_name}({json.dumps(tool_args)})\n\nResult: {tool_result_str}"
                    })

                    # Append user message for next iteration
                    self.conversation_history.append({
                        "role": "user",
                        "content": "Based on this result, what's your next step? Continue or finish?"
                    })

                    final_result["actions"].append({
                        "tool": tool_name,
                        "args": tool_args,
                        "result": result
                    })

            # Check if task is complete
            if response.get("finish_reason") == "stop" or not response.get("tool_calls"):
                final_result["success"] = True
                final_result["final_message"] = response.get("content", "")
                final_result["analysis"] = await self._summarize_findings()
                break

        return final_result

    async def _summarize_findings(self) -> str:
        """Ask LLM to summarize what was learned/accomplished"""
        summary_prompt = {
            "role": "user",
            "content": "Based on the conversation history, provide a brief summary of what was accomplished and any key findings."
        }

        response = self.llm.chat(
            messages=self.conversation_history + [summary_prompt],
            tools=None
        )
        return response.get("content", "No summary available")

    async def analyze_page(self, controller, analysis_type: str = "general") -> Dict[str, Any]:
        """Analyze the current page in different ways"""

        prompts = {
            "general": "Analyze this webpage thoroughly. What is it about? What's the main content? Any notable elements?",
            "products": "Analyze this page for products. List each product with key details (name, price, description, ratings).",
            "people": "Analyze for people/profiles. List each person with relevant details (name, title, company, bio).",
            "trends": "Analyze for trends and trending topics. What seems to be popular or getting attention?",
            "video": "Analyze this video page. What is the video about? What might make it successful? (Title, thumbnail, engagement)",
        }

        # Get page content
        page_content = await controller.get_page_content("text")
        screenshot_result = await controller.screenshot()

        # Ask LLM to analyze
        analysis_prompt = {
            "role": "user",
            "content": f"""{prompts.get(analysis_type, prompts['general'])}

PAGE CONTENT:
{page_content.get('content', 'Could not get page content')}

SCREENSHOT: {screenshot_result.get('path', 'No screenshot')}

Please provide a thorough analysis as a human would."""
        }

        response = self.llm.chat(
            messages=[analysis_prompt],
            tools=None
        )

        return {
            "success": True,
            "analysis": response.get("content", ""),
            "screenshot": screenshot_result.get("path")
        }

    async def find_and_analyze(self, controller, search_query: str, analysis_type: str = "general") -> Dict[str, Any]:
        """Search for something and analyze the results"""

        # First search
        search_result = await controller.search_google(search_query)
        if not search_result.get("success"):
            return search_result

        # Wait for page to load
        await controller.wait(2)

        # Analyze the results
        analysis = await self.analyze_page(controller, analysis_type)

        return {
            "success": True,
            "search_query": search_query,
            "analysis": analysis.get("analysis"),
            "screenshot": analysis.get("screenshot")
        }

    def reset(self):
        """Reset conversation history for a new task"""
        self.conversation_history = []
        self.task_history = []