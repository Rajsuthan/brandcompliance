import time
from typing import List, Dict, Any, Optional, Callable, Awaitable, Tuple
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

async def process_completion_chunks(
    completion_stream,
    message_handler,
    on_update_time: Callable[[float], None],
) -> Tuple[str, List[Dict[str, Any]], bool]:
    """Process streaming chunks from OpenRouter API response.
    
    This function handles the streaming response from the OpenRouter API,
    processing both content and tool call deltas.
    
    Args:
        completion_stream: AsyncIterator of completion chunks from OpenAI SDK
        message_handler: MessageHandler instance for handling messages
        on_update_time: Callback to update last response time
        
    Returns:
        Tuple of (content string, tool calls list, is_tool_call flag)
    """
    # Initialize accumulators
    current_content = ""
    current_tool_calls = []
    is_tool_call = False
    
    # Process each chunk
    async for chunk in completion_stream:
        # Update last response time
        on_update_time(time.time())
        
        # Extract content delta if present
        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
            content_delta = chunk.choices[0].delta.content
            current_content += content_delta
            
            # Stream content delta to the client
            await message_handler.stream_content(content_delta)
        
        # Process tool call delta if present
        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.tool_calls:
            is_tool_call = True
            for tool_call_delta in chunk.choices[0].delta.tool_calls:
                # Find or create the corresponding tool call in our accumulator
                tool_call = None
                if tool_call_delta.index is not None:
                    # Find existing tool call with same index
                    for tc in current_tool_calls:
                        if tc.get("index") == tool_call_delta.index:
                            tool_call = tc
                            break
                    
                    # Create new tool call if not found
                    if not tool_call:
                        tool_call = {
                            "index": tool_call_delta.index,
                            "id": tool_call_delta.id or "",
                            "type": "function",
                            "function": {
                                "name": "",
                                "arguments": ""
                            }
                        }
                        current_tool_calls.append(tool_call)
                
                # Update tool call with delta information
                if tool_call_delta.function:
                    if tool_call_delta.function.name:
                        tool_call["function"]["name"] = tool_call_delta.function.name
                    if tool_call_delta.function.arguments:
                        tool_call["function"]["arguments"] += tool_call_delta.function.arguments
    
    return current_content, current_tool_calls, is_tool_call


async def extract_tool_arguments(tool_args_str: str) -> Dict[str, Any]:
    """Extract and parse JSON arguments from a tool call string.
    
    Args:
        tool_args_str: JSON string of tool arguments
        
    Returns:
        Parsed tool arguments as a dictionary
    """
    import json
    try:
        return json.loads(tool_args_str)
    except json.JSONDecodeError:
        print(f"\033[91m[ERROR] Failed to parse tool arguments: {tool_args_str}\033[0m")
        return {}
