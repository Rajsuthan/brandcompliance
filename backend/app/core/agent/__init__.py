"""
Agent module for handling AI interactions and tool usage.

This package provides functionality for creating and managing AI agents
that can process messages, use tools, and generate responses.
"""

# Import main components to expose at the package level
from .index import Agent
from .llm import llm
from .tools import claude_tools, get_tool_function

# Define what gets imported with "from app.core.agent import *"
__all__ = ["Agent", "llm", "claude_tools", "get_tool_function"]
