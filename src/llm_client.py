"""
LLM Client Factory - Unified interface for OpenAI, Anthropic, Ollama, and NVIDIA NIM
"""
import os
import json
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

load_dotenv()


class LLMClient(ABC):
    """Base class for LLM clients"""

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Send a chat request"""
        pass

    @abstractmethod
    def chat_stream(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None):
        """Send a streaming chat request"""
        pass


class OpenAIClient(LLMClient):
    """OpenAI GPT client"""

    def __init__(self, api_key: str, model: str):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def chat(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
        params = {
            "model": self.model,
            "messages": messages,
        }
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        response = self.client.chat.completions.create(**params)
        return self._parse_response(response)

    def chat_stream(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None):
        params = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }
        if tools:
            params["tools"] = tools

        return self.client.chat.completions.create(**params)

    def _parse_response(self, response) -> Dict[str, Any]:
        """Parse OpenAI response to standard format"""
        choice = response.choices[0]
        result = {
            "content": choice.message.content or "",
            "finish_reason": choice.finish_reason,
        }

        if choice.message.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.id,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in choice.message.tool_calls
            ]

        return result


class AnthropicClient(LLMClient):
    """Anthropic Claude client"""

    def __init__(self, api_key: str, model: str):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def _convert_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Convert messages to Anthropic format"""
        converted = []
        for msg in messages:
            role = msg["role"]
            if role == "system":
                converted.append({"role": "user", "content": msg["content"]})
            else:
                converted.append(msg)
        return converted

    def chat(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
        params = {
            "model": self.model,
            "messages": self._convert_messages(messages),
            "max_tokens": 4096,
        }

        if tools:
            # Anthropic uses tool_use instead of tools
            tool_schemas = []
            for tool in tools:
                tool_schemas.append({
                    "name": tool["function"]["name"],
                    "description": tool.get("description", ""),
                    "input_schema": tool["function"]["parameters"]
                })
            params["tools"] = tool_schemas

        response = self.client.messages.create(**params)

        result = {
            "content": "",
            "finish_reason": "stop" if response.stop_reason else "unknown",
        }

        for block in response.content:
            if block.type == "text":
                result["content"] += block.text
            elif block.type == "tool_use":
                result["tool_calls"] = [{
                    "id": block.id,
                    "function": {
                        "name": block.name,
                        "arguments": json.dumps(block.input)
                    }
                }]

        return result

    def chat_stream(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None):
        # Streaming not fully implemented for Anthropic
        return self.chat(messages, tools)


class OllamaClient(LLMClient):
    """Ollama local LLM client"""

    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def chat(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
        import requests

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }

        response = requests.post(f"{self.base_url}/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()

        result = {
            "content": data.get("message", {}).get("content", ""),
            "finish_reason": "stop",
        }

        return result

    def chat_stream(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None):
        import requests

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }

        response = requests.post(f"{self.base_url}/api/chat", json=payload, stream=True)
        return response.iter_lines()


class NIMClient(LLMClient):
    """NVIDIA NIM client"""

    def __init__(self, base_url: str, model: str):
        # FIX: Sanitize the base URL string to remove trailing slashes or hidden newlines
        cleaned_url = base_url.strip().rstrip("/")
        
        # If the URL already contains the version path string '/v1', slice it off
        # so appending '/v1/chat/completions' below doesn't duplicate the route
        if cleaned_url.endswith("/v1"):
            self.base_url = cleaned_url[:-3]
        else:
            self.base_url = cleaned_url

        self.model = model

    def chat(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
        import requests

        # NVIDIA NIM uses OpenAI-compatible API format
        headers = {
            "Authorization": f"Bearer {os.getenv('NIM_API_KEY', '')}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 4096,
            "temperature": 0.7,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        data = response.json()

        result = {
            "content": data["choices"][0]["message"]["content"] or "",
            "finish_reason": data["choices"][0]["finish_reason"] or "stop",
        }

        if "tool_calls" in data["choices"][0]["message"]:
            result["tool_calls"] = [{
                "id": tc["id"],
                "function": {
                    "name": tc["function"]["name"],
                    "arguments": tc["function"]["arguments"]
                }
            } for tc in data["choices"][0]["message"]["tool_calls"]]

        return result

    def chat_stream(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None):
        import requests

        # NVIDIA NIM uses OpenAI-compatible API format for streaming
        headers = {
            "Authorization": f"Bearer {os.getenv('NIM_API_KEY', '')}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 4096,
            "temperature": 0.7,
            "stream": True,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            headers=headers,
            json=payload,
            stream=True
        )
        return response.iter_lines()


def create_llm_client() -> LLMClient:
    """Factory function to create LLM client based on environment config"""
    provider = os.getenv("LLM_PROVIDER", "openai").lower()

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_MODEL", "gpt-4o")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set in .env")
        return OpenAIClient(api_key, model)

    elif provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in .env")
        return AnthropicClient(api_key, model)

    elif provider == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        model = os.getenv("OLLAMA_MODEL", "llama3")
        return OllamaClient(base_url, model)

    elif provider == "nim":
        base_url = os.getenv("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
        model = os.getenv("NIM_MODEL", "mistralai/mixtral-8x22b-instruct-v0.1")
        api_key = os.getenv("NIM_API_KEY")
        if not api_key:
            raise ValueError("NIM_API_KEY not set in .env")
        return NIMClient(base_url, model)

    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}. Use: openai, anthropic, ollama, or nim")


# Default browser control tools for the LLM
BROWSER_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "navigate",
            "description": "Navigate to a URL",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to navigate to"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "click",
            "description": "Click on an element (button, link, etc.)",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector for the element"}
                },
                "required": ["selector"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "type",
            "description": "Type text into an input field",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector for the input"},
                    "text": {"type": "string", "description": "Text to type"}
                },
                "required": ["selector", "text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_page_content",
            "description": "Get the current page content (HTML or text)",
            "parameters": {
                "type": "object",
                "properties": {
                    "format": {"type": "string", "enum": ["html", "text"], "default": "text"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "screenshot",
            "description": "Take a screenshot of the current page",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to save screenshot"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "scroll",
            "description": "Scroll the page",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {"type": "string", "enum": ["up", "down"], "default": "down"},
                    "amount": {"type": "integer", "description": "Number of pixels to scroll"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "wait",
            "description": "Wait for a specified time (seconds)",
            "parameters": {
                "type": "object",
                "properties": {
                    "seconds": {"type": "number", "description": "Seconds to wait"}
                },
                "required": ["seconds"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_element",
            "description": "Find an element on the page and get its details",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector"}
                },
                "required": ["selector"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_google",
            "description": "Search Google for a query",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            }
        }
    }
]