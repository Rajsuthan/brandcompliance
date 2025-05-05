import json
import datetime
from typing import Dict, Any, List, Optional, Callable, Awaitable
from pathlib import Path

class MessageHandler:
    """A class to handle message operations for the OpenRouter agent.
    
    This handles adding messages to the conversation, streaming responses,
    and optional file-based logging.
    """
    
    def __init__(
        self,
        conversation_id: str,
        on_stream: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
        save_messages: bool = True,
    ):
        self.conversation_id = conversation_id
        self.on_stream = on_stream
        self.save_messages = save_messages
        self.messages = []
        
        # Set up logging if enabled
        if self.save_messages:
            self.logs_dir = Path("logs/conversations")
            self.logs_dir.mkdir(parents=True, exist_ok=True)
            self.messages_file = self.logs_dir / f"{self.conversation_id}.json"
            print(f"\033[94m[LOG] MessageHandler: Messages will be saved to {self.messages_file}\033[0m")
    
    async def add_message(self, role: str, content: Any):
        """Add a message to the conversation history.
        
        Args:
            role: The role of the message sender (system, user, assistant, tool)
            content: The content of the message
        """
        message = {
            "role": role, 
            "content": content, 
            "timestamp": datetime.datetime.now().isoformat()
        }
        self.messages.append(message)
        # Save messages in real-time if enabled
        await self.save_messages_to_file()
    
    async def save_messages_to_file(self):
        """Save current messages to a JSON file in real-time."""
        if not self.save_messages:
            return

        try:
            timestamp = datetime.datetime.now().isoformat()
            data = {
                "conversation_id": self.conversation_id,
                "timestamp": timestamp,
                "messages": self.messages
            }

            with open(self.messages_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)

            print(f"\033[92m[LOG] Saved messages to {self.messages_file}\033[0m")
        except Exception as e:
            print(f"\033[91m[ERROR] Failed to save messages to file: {e}\033[0m")
    
    async def stream_content(self, content: str):
        """Stream text content to the client.
        
        Args:
            content: Text content to stream
        """
        if self.on_stream:
            await self.on_stream({
                "type": "text",
                "content": content
            })
    
    async def stream_tool_result(self, tool_name: str, tool_input: Dict[str, Any], tool_result: Any):
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
    
    async def stream_complete(self, content: Any):
        """Signal completion to the client.
        
        Args:
            content: Completion content to send
        """
        if self.on_stream:
            await self.on_stream({
                "type": "complete",
                "content": content
            })
    
    def get_formatted_messages(self, max_messages=None):
        """Format messages for the OpenAI API, optionally limiting to the most recent messages.
        
        Args:
            max_messages: If provided, limit to this many most recent non-system messages
                          while keeping all system messages.
                          
        Returns:
            List of formatted messages for the API
        """
        # Always include all system messages
        system_messages = [m for m in self.messages if m["role"] == "system"]
        non_system_messages = [m for m in self.messages if m["role"] != "system"]
        
        # # Limit message history if max_messages is specified
        # if max_messages is not None and len(non_system_messages) > max_messages:
        #     # Keep only the most recent messages
        #     non_system_messages = non_system_messages[-max_messages:]
        #     print(f"\033[93m[INFO] Limiting conversation history to {max_messages} most recent non-system messages\033[0m")
            
        # Combine system and limited non-system messages
        formatted_messages = []
        
        # Add system messages first
        for message in system_messages:
            formatted_messages.append({
                "role": message["role"],
                "content": message["content"]
            })
        
        # Add non-system messages, with special handling for image data
        image_already_included = False  # Track if we've already included an image
        
        for message in non_system_messages:
            # Handle different message types based on role and content
            if message["role"] == "assistant" and isinstance(message["content"], dict) and "tool_calls" in message["content"]:
                # Handle assistant messages with tool calls (OpenAI format)
                formatted_message = {
                    "role": "assistant"
                }
                
                # Add content if present and not None
                if message["content"].get("content") is not None:
                    formatted_message["content"] = message["content"].get("content")
                
                # Add tool_calls - this must be included as a top-level field per OpenRouter docs
                formatted_message["tool_calls"] = message["content"].get("tool_calls", [])
                
                formatted_messages.append(formatted_message)
            
            elif message["role"] == "tool":
                # Handle tool messages per OpenRouter docs
                # If content is a dict with tool response info, extract the fields
                if isinstance(message["content"], dict):
                    formatted_messages.append({
                        "role": "tool",
                        "tool_call_id": message["content"].get("tool_call_id", ""),
                        "name": message["content"].get("name", ""),
                        "content": message["content"].get("content", "")
                    })
                # If the message already contains proper tool fields, use them directly
                elif "tool_call_id" in message and "name" in message and "content" in message:
                    formatted_messages.append({
                        "role": "tool",
                        "tool_call_id": message["tool_call_id"],
                        "name": message["name"],
                        "content": message["content"]
                    })
                else:
                    # Fallback for incorrectly formatted tool messages
                    print(f"\033[93m[WARNING] Malformed tool message: {message}\033[0m")
                    formatted_messages.append({
                        "role": message["role"],
                        "content": str(message["content"])
                    })
                    
            # Handle standard text messages
            elif isinstance(message["content"], str):
                formatted_messages.append({
                    "role": message["role"],
                    "content": message["content"]
                })
                
            # Handle multimodal messages with potential image data
            elif isinstance(message["content"], list):
                has_image = any(item.get("type") == "image_url" for item in message["content"])
                
                # For brand compliance analysis, we ALWAYS need the full image in every message
                # so the model can properly analyze it - let's ensure it's always included
                if has_image and message["role"] == "user":
                    # We always include the image data for compliance analysis, regardless
                    # of whether we've seen it before - this is crucial for accurate image analysis
                    formatted_messages.append({
                        "role": message["role"],
                        "content": message["content"]
                    })
                    # No longer track image_already_included since we always include it
                    # This ensures the model can see the image in every iteration
                else:
                    # Non-user messages or messages without images
                    formatted_messages.append({
                        "role": message["role"],
                        "content": message["content"]
                    })
        
        # Ensure the last message is a user message
        if formatted_messages and formatted_messages[-1]["role"] != "user":
            print(f"\033[93m[INFO] Adding a simple user message at the end to ensure proper LLM response\033[0m")
            formatted_messages.append({
                "role": "user",
                "content": "Go ahead"
            })
        
        return formatted_messages
        
    def get_message_token_estimate(self) -> int:
        """Get a rough estimate of the total token count for all messages.
        
        This is an approximation to help with context management.
        4 characters ~= 1 token as a rough rule of thumb.
        For image data, we use a more realistic token estimation.
        
        Returns:
            Estimated token count
        """
        total_chars = 0
        image_already_counted = False  # Only count the first image fully
        
        for message in self.messages:
            # Count text content
            if isinstance(message["content"], str):
                total_chars += len(message["content"])
            # Count multimodal content
            elif isinstance(message["content"], list):
                for item in message["content"]:
                    if item.get("type") == "text":
                        total_chars += len(item.get("text", ""))
                    elif item.get("type") == "image_url" and not image_already_counted:
                        # Images use a lot of tokens (base64 encoding)
                        url = item.get("image_url", {}).get("url", "")
                        detail_level = item.get("image_url", {}).get("detail", "high")
                        
                        if "base64" in url:
                            # Get base64 length as approximation of image size
                            base64_part = url.split("base64,")[-1] if "base64," in url else url
                            image_size_kb = len(base64_part) / 1024
                            
                            # More realistic token estimate for images
                            token_multiplier = 0.05  # Much lower multiplier - 1/20th of base64 length
                            image_tokens = int(len(base64_part) * token_multiplier)
                            
                            # Set reasonable bounds
                            image_tokens = max(300, min(image_tokens, 1500))
                            total_chars += image_tokens * 4  # Convert tokens to chars
                            image_already_counted = True
                            print(f"\033[94m[INFO] Estimated image tokens: {image_tokens} (image size: {image_size_kb:.1f}KB)\033[0m")
                        else:
                            # URL only, much smaller
                            total_chars += len(url)
        
        # More accurate estimation based on empirical data: 1 token ~= 4.54 characters for Claude models
        # (From the provided ratio: 8468 chars = 1864 tokens)
        CHARS_PER_TOKEN = 4.54
        estimated_tokens = int(total_chars / CHARS_PER_TOKEN)
        print(f"\033[94m[TOKEN INFO] Total characters: {total_chars}, Estimated tokens: {estimated_tokens} (using ratio of {CHARS_PER_TOKEN} chars/token)\033[0m")
        return estimated_tokens
