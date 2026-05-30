"""
Tests for the NVIDIA NIM client
"""
import os
import json
from unittest.mock import patch, MagicMock
from src.llm_client import NIMClient


def test_nim_client_initialization():
    """Test NIM client initialization"""
    client = NIMClient(
        base_url="https://test.nim.api.nvidia.com/v1",
        model="test-model"
    )

    assert client.base_url == "https://test.nim.api.nvidia.com/v1"
    assert client.model == "test-model"


def test_nim_client_chat():
    """Test NIM client chat method"""
    # Mock response data
    mock_response_data = {
        "choices": [{
            "message": {
                "content": "This is a test response",
                "tool_calls": []
            },
            "finish_reason": "stop"
        }]
    }

    with patch('requests.post') as mock_post:
        # Setup mock
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_response_data
        mock_post.return_value = mock_response

        # Create client and set API key via environ
        os.environ["NIM_API_KEY"] = "test-nim-key"
        client = NIMClient(
            base_url="https://integrate.api.nvidia.com/v1",
            model="mistralai/mixtral-8x22b-instruct-v0.1"
        )

        # Test chat
        messages = [{"role": "user", "content": "Hello"}]
        result = client.chat(messages)

        # Verify
        assert result["content"] == "This is a test response"
        assert result["finish_reason"] == "stop"
        assert "tool_calls" not in result or result["tool_calls"] == []

        # Verify request was made correctly
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "https://integrate.api.nvidia.com/v1/v1/chat/completions"
        assert kwargs["json"]["model"] == "mistralai/mixtral-8x22b-instruct-v0.1"
        assert kwargs["json"]["messages"] == messages

        # Clean up
        del os.environ["NIM_API_KEY"]


def test_nim_client_chat_with_tools():
    """Test NIM client chat method with tools"""
    # Mock response data with tool calls
    mock_response_data = {
        "choices": [{
            "message": {
                "content": "I'll help you with that",
                "tool_calls": [{
                    "id": "call_123",
                    "function": {
                        "name": "test_function",
                        "arguments": "{\"param\": \"value\"}"
                    }
                }]
            },
            "finish_reason": "tool_calls"
        }]
    }

    with patch('requests.post') as mock_post:
        # Setup mock
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_response_data
        mock_post.return_value = mock_response

        # Create client
        os.environ["NIM_API_KEY"] = "test-nim-key"
        client = NIMClient(
            base_url="https://integrate.api.nvidia.com/v1",
            model="test-model"
        )

        # Define tools
        tools = [{
            "type": "function",
            "function": {
                "name": "test_function",
                "description": "A test function",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "param": {"type": "string"}
                    }
                }
            }
        }]

        # Test chat with tools
        messages = [{"role": "user", "content": "Use the test function"}]
        result = client.chat(messages, tools=tools)

        # Verify
        assert result["content"] == "I'll help you with that"
        assert result["finish_reason"] == "tool_calls"
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["function"]["name"] == "test_function"

        # Verify tools were passed in request
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs["json"]["tools"] == tools

        # Clean up
        del os.environ["NIM_API_KEY"]


if __name__ == "__main__":
    test_nim_client_initialization()
    test_nim_client_chat()
    test_nim_client_chat_with_tools()
    print("All NIM client tests passed!")