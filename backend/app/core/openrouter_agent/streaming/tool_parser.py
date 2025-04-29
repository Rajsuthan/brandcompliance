import json
from typing import Dict, Any, List, Optional

def extract_tool_call_from_response(
    response_content: str,
    response_tool_calls: Optional[List[Dict[str, Any]]] = None
) -> Optional[Dict[str, Any]]:
    """Extract tool call information from a response.
    
    Args:
        response_content: Text content from the response
        response_tool_calls: Tool calls from the response, if available
        
    Returns:
        Extracted tool call or None if no tool call found
    """
    if response_tool_calls:
        # If tool_calls is available directly, use the first one
        if response_tool_calls and len(response_tool_calls) > 0:
            first_tool_call = response_tool_calls[0]
            
            if (
                "function" in first_tool_call and 
                "name" in first_tool_call["function"] and 
                "arguments" in first_tool_call["function"]
            ):
                try:
                    # Parse the arguments as JSON
                    args_str = first_tool_call["function"]["arguments"]
                    return {
                        "name": first_tool_call["function"]["name"],
                        "arguments": json.loads(args_str) if args_str else {}
                    }
                except json.JSONDecodeError:
                    print(f"\033[91m[ERROR] Failed to parse tool arguments: {first_tool_call['function']['arguments']}\033[0m")
                    return {
                        "name": first_tool_call["function"]["name"],
                        "arguments": {}
                    }
    
    # If no tool call was found or args couldn't be parsed
    return None
