from typing import List, Dict, Any, Optional, Callable, Awaitable

class StreamHandler:
    """Handles streaming functionality for the OpenRouter agent.
    
    This class provides methods for handling streaming responses from the
    OpenRouter API, including content and tool call streaming.
    """
    
    def __init__(self, on_stream: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None):
        """Initialize the StreamHandler.
        
        Args:
            on_stream: Optional callback function for streaming responses
        """
        self.on_stream = on_stream
    
    async def stream_content(self, content: str) -> None:
        """Stream text content to the client.
        
        Args:
            content: Text content to stream
        """
        if self.on_stream:
            await self.on_stream({
                "type": "text",
                "content": content
            })
    
    async def stream_tool_result(self, tool_name: str, tool_input: Dict[str, Any], tool_result: Any) -> None:
        """Stream tool execution result to the client.
        
        Args:
            tool_name: Name of the tool that was executed
            tool_input: Arguments passed to the tool (filtered to remove image data)
            tool_result: Result of the tool execution
        """
        if self.on_stream:
            import json
            await self.on_stream({
                "type": "tool",
                "tool_name": tool_name,
                "content": json.dumps({
                    "tool_name": tool_name,
                    "tool_input": tool_input,
                    "tool_result": tool_result
                })
            })
    
    async def stream_complete(self, content: Any) -> None:
        """Signal completion to the client.
        
        Args:
            content: Completion content to send
        """
        if self.on_stream:
            await self.on_stream({
                "type": "complete",
                "content": content
            })
