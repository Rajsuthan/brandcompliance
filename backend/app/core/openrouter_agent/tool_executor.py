import json
import datetime
from typing import Dict, Any, List, Optional

from app.core.openrouter_agent.tool_definitions import execute_tool

async def execute_and_process_tool(
    tool_name: str,
    tool_args: Dict[str, Any],
    image_base64: str = None,
    frames: List[Dict[str, Any]] = None,
    tool_call_id: Optional[str] = None,
    on_stream = None,
) -> Dict[str, Any]:
    # Sanitize the tool_call_id to prevent token explosion
    # If it's too long, truncate or hash it
    MAX_TOOL_CALL_ID_LENGTH = 64  # Reasonable length for an ID
    if tool_call_id and len(str(tool_call_id)) > MAX_TOOL_CALL_ID_LENGTH:
        import hashlib
        # Hash the ID and use a prefix to identify it's been hashed
        hashed_id = hashlib.md5(str(tool_call_id).encode()).hexdigest()
        tool_call_id = f"hashed_{hashed_id}"
        print(f"\033[93m[WARNING] tool_call_id was too long, replaced with hash: {tool_call_id}\033[0m")
    """Execute a tool and prepare results for the agent response.
    
    Args:
        tool_name: The name of the tool to execute
        tool_args: Arguments to pass to the tool
        tool_call_id: Optional ID of the tool call (for OpenAI compatibility)
        on_stream: Optional streaming callback function
        
    Returns:
        A dictionary with the tool execution results and metadata
    """
    try:
        # Log input sizes
        tool_args_str = str(tool_args)
        print(f"\033[92m[TOOL EXEC] Executing {tool_name}...\033[0m")
        print(f"\033[92m[TOOL INPUT SIZE] {tool_name}: {len(tool_args_str)} chars\033[0m")
        
        # For image input, show the length but not the content
        if isinstance(tool_args, dict) and "image_base64" in tool_args and tool_args["image_base64"]:
            img_len = len(tool_args["image_base64"])
            print(f"\033[92m[IMAGE SIZE] Image in {tool_name}: {img_len} chars\033[0m")
        
        tool_result = await execute_tool(tool_name, tool_args)
        
        # Log output sizes
        tool_result_str = str(tool_result)
        print(f"\033[95m[TOOL OUTPUT SIZE] {tool_name}: {len(tool_result_str)} chars\033[0m")
        
        trunc_tool_result = tool_result_str[:300] + ("...[[TRUNCATED]]" if len(tool_result_str) > 300 else "")
        print(f"\033[95m[TOOL RESULT] {tool_name}: {trunc_tool_result}\033[0m")
    except Exception as e:
        print(f"\033[91m[ERROR] Exception in {tool_name}: {e}\033[0m")
        tool_result = {"error": str(e)}
        trunc_tool_result = str(tool_result)
    
    # Create the result record for the tool trace
    trace_record = {
        "timestamp": datetime.datetime.now().isoformat(),
        "tool_name": tool_name,
        "tool_input": tool_args,
        "truncated_result": trunc_tool_result,
        "full_result": tool_result if tool_name == "attempt_completion" else None
    }
    
    # Stream tool result to the client if needed
    if on_stream:
        # Remove image_base64 and images_base64 from tool_input before sending
        filtered_tool_args = dict(tool_args) if isinstance(tool_args, dict) else tool_args
        if isinstance(filtered_tool_args, dict):
            filtered_tool_args.pop("image_base64", None)
            filtered_tool_args.pop("images_base64", None)
        
        await on_stream({
            "type": "tool",
            "tool_name": tool_name,
            "content": json.dumps({
                "tool_name": tool_name,
                "tool_input": filtered_tool_args,
                "tool_result": tool_result
            })
        })
    
    # Prepare a SIMPLIFIED message format for OpenAI compatibility
    # Only include a summarized version of the tool result to prevent token explosion
    # Maximum length for tool result in the message format
    MAX_TOOL_RESULT_LENGTH = 5000  # Reasonable limit to prevent explosion
    
    # If the tool result is too long, truncate it drastically
    tool_result_str = str(tool_result)
    if len(tool_result_str) > MAX_TOOL_RESULT_LENGTH:
        print(f"\033[91m[WARNING] Tool result too large ({len(tool_result_str)} chars), truncating to {MAX_TOOL_RESULT_LENGTH}\033[0m")
        # For JSON results, try to preserve structure by truncating internal content
        if tool_result_str.startswith('{') and tool_result_str.endswith('}'):
            try:
                # Parse the JSON and truncate large string values - use the already imported json
                # (don't reimport within the function)
                result_obj = json.loads(tool_result_str)
                # Helper function to truncate nested object values
                def truncate_values(obj, max_len=1000):
                    if isinstance(obj, dict):
                        return {k: truncate_values(v, max_len) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [truncate_values(item, max_len) for item in obj[:5]] + (["...truncated..."] if len(obj) > 5 else [])
                    elif isinstance(obj, str) and len(obj) > max_len:
                        return obj[:max_len] + "...truncated..."
                    else:
                        return obj
                
                # Truncate the object
                truncated_obj = truncate_values(result_obj)
                truncated_result = json.dumps(truncated_obj)
                # Final safety check
                if len(truncated_result) > MAX_TOOL_RESULT_LENGTH:
                    truncated_result = truncated_result[:MAX_TOOL_RESULT_LENGTH] + "...truncated..."
            except:
                # Fallback to simple truncation if JSON parsing fails
                truncated_result = tool_result_str[:MAX_TOOL_RESULT_LENGTH] + "...truncated..."
        else:
            # Simple truncation for non-JSON results
            truncated_result = tool_result_str[:MAX_TOOL_RESULT_LENGTH] + "...truncated..."
    else:
        truncated_result = tool_result_str
    
    # Create the simplified message format
    message_format = {
        "tool_call_id": tool_call_id,
        "name": tool_name,
        "content": truncated_result
    }
    
    # Log the size of all components for debugging
    tool_call_id_len = len(str(tool_call_id)) if tool_call_id else 0
    print(f"\033[93m[DEBUG] tool_call_id length: {tool_call_id_len} chars\033[0m")
    print(f"\033[93m[DEBUG] Original tool result length: {len(tool_result_str)} chars\033[0m")
    print(f"\033[93m[DEBUG] Truncated result length: {len(truncated_result)} chars\033[0m")
    print(f"\033[93m[DEBUG] Final message format length: {len(str(message_format))} chars\033[0m")
    
    # Return the tool result in the proper OpenAI/OpenRouter compatible format
    return message_format
