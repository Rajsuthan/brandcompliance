import json
import asyncio
import sys
import os
import base64
import mimetypes
from typing import List, Dict, Any, Optional, Callable
from uuid import uuid4
from pydantic import BaseModel
from openai import OpenAI
import re
import xmltodict

# Add the project root to the Python path
current_file = os.path.abspath(__file__)
backend_dir = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
)
sys.path.insert(0, backend_dir)

from app.core.agent.tools import claude_tools, get_tool_function
from app.core.agent.prompt import gemini_system_prompt

def encode_image_to_base64(image_path):
    """
    Read an image file and convert it to base64 encoding.
    """
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")

    media_type = mimetypes.guess_type(image_path)[0]
    if not media_type:
        media_type = "image/png"

    return encoded_string, media_type

class Message(BaseModel):
    role: str
    content: List[Dict[str, Any]] | str

class GeminiAgent:
    def __init__(
        self,
        model: str = "gemini-2.0-flash",
        available_tools: Optional[List[Dict]] = None,
        on_stream: Optional[Callable] = None,
        on_stop: Optional[Callable] = None,
        messages: Optional[List[Message]] = None,
        user_id: Optional[str] = None,
        message_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ):
        print(f"\n📋 Initializing GeminiAgent with model: {model}")
        self.model = model
        self.available_tools = available_tools or claude_tools
        self.messages = (
            [msg.model_dump(exclude={"timestamp"}) for msg in messages]
            if messages
            else []
        )
        self.on_stream = self.container_on_stream if on_stream else None
        self._original_on_stream = on_stream
        self.on_stop = on_stop
        self.tool_response = ""
        self.text_response = ""
        self.full_assistant_content: List[Dict[str, Any]] = []
        self.user_id = user_id
        self.message_id = message_id
        self.system_prompt = system_prompt or gemini_system_prompt

        # Initialize OpenAI client with Gemini base URL
        api_key = os.getenv("GOOGLE_API_KEY")
        print(f"\n🔑 Using API key: {api_key[:5]}...{api_key[-5:] if api_key else 'None'}")
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        print("\n🔌 OpenAI client initialized with Gemini base URL")

    async def container_on_stream(self, data: Dict[str, Any]):
        """Handle streaming data in the format expected by the frontend"""
        print(
            f"\n🔄 === Streaming Event ===\nType: {data['type']}\nContent: {data['content']}\n================"
        )
        if data["type"] in ("text", "thinking"):
            self.text_response += data["content"]
        elif data["type"] == "tool":
            self.tool_response += data["content"]
        if self._original_on_stream:
            await self._original_on_stream(data)
        return data

    async def add_message(self, role: str, content: Any):
        """Add a message to the conversation history"""
        print(f"\n💬 Adding message with role: {role}")
        if isinstance(content, str):
            message = {"role": role, "content": content}
            print(f"📝 Added text message: {content[:50]}..." if len(content) > 50 else f"📝 Added text message: {content}")
        else:
            message = {"role": role, "content": content}
            print(f"📝 Added structured message with content type: {type(content)}")
        self.messages.append(message)

    def _parse_xml_manually(self, xml_content):
        """
        Manually parse XML content when standard parsing fails.
        """
        print(f"\n🔍 Attempting to parse XML content: {xml_content[:50]}..." if len(xml_content) > 50 else f"🔍 Attempting to parse XML content: {xml_content}")
        try:
            root_tag_match = re.match(r"<([a-zA-Z0-9_]+)>", xml_content)
            if not root_tag_match:
                print("❌ No root tag found in content")
                return False, None, None, xml_content

            root_tag = root_tag_match.group(1)
            print(f"🏷️ Found root tag: {root_tag}")
            if root_tag.lower() != "tool":
                print(f"❌ Root tag is not 'tool': {root_tag}")
                return False, None, None, xml_content

            # Extract tool name
            tool_name_match = re.search(r"<name>(.*?)</name>", xml_content)
            if not tool_name_match:
                print("❌ No tool name found in XML")
                return False, None, None, xml_content

            tool_name = tool_name_match.group(1)
            print(f"🛠️ Found tool name: {tool_name}")

            try:
                xml_dict = xmltodict.parse(xml_content)
                print("✅ Successfully parsed XML with xmltodict")
                return True, tool_name, xml_dict, xml_content
            except Exception as e:
                print(f"⚠️ Failed to parse XML with xmltodict: {str(e)}")
                return False, tool_name, None, xml_content

        except Exception as e:
            print(f"❌ Exception in XML parsing: {str(e)}")
            return False, None, None, xml_content

    def _extract_tool_call(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Extract tool call information from the response content.
        """
        print(f"\n🔎 Checking for tool calls in content: {content[:50]}..." if len(content) > 50 else f"🔎 Checking for tool calls in content: {content}")
        is_xml, tool_name, xml_dict, content_to_process = self._parse_xml_manually(content)
        
        if is_xml and tool_name:
            print("🔍 Found potential tool call")
            try:
                if xml_dict:
                    # Convert XML dict to the expected tool call format
                    tool_data = {
                        "tool_name": tool_name,
                        "parameters": xml_dict["tool"].get("parameters", {})
                    }
                    print(f"✅ Successfully extracted tool call: {tool_name}")
                    return tool_data
                else:
                    print("❌ XML dictionary is empty")
            except Exception as e:
                print(f"❌ Error extracting tool call: {str(e)}")
                pass
        return None

    async def process_message(
        self, user_input: str | List[Dict[str, Any]] | Dict[str, Any]
    ) -> tuple[str, List[Dict]]:
        """
        Process a user message using Gemini via OpenAI API and return the response in the format expected by the frontend.
        """
        print(f"\n🚀 Processing message: {type(user_input)}")
        if isinstance(user_input, dict):
            print(f"📦 User input keys: {user_input.keys()}")
        elif isinstance(user_input, list):
            print(f"📦 User input list length: {len(user_input)}")
        else:
            print(f"📦 User input length: {len(user_input)} characters")
            
        # Handle different types of user input
        if isinstance(user_input, dict) and "image_base64" in user_input:
            print("📸 Processing image message")
            print(f"🖼️ Image media type: {user_input.get('media_type', 'image/png')}")
            print(f"🔢 Image base64 length: {len(user_input['image_base64'])}")
            print(f"💬 Text prompt: {user_input.get('text', 'Analyze this image.')}")
            
            # Format message with image and text
            formatted_message = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": user_input.get("media_type", "image/png"),
                        "data": user_input["image_base64"],
                    },
                },
                {
                    "type": "text",
                    "text": user_input.get("text", "Analyze this image."),
                },
            ]
            await self.add_message("user", formatted_message)
        else:
            await self.add_message("user", user_input)

        final_response = ""

        # Initialize processing loop
        self.tool_response = ""
        self.text_response = ""
        self.full_assistant_content = []

        # Create messages for Gemini in ChatCompletion format
        print("\n📋 Creating formatted messages for OpenAI API")
        formatted_messages = []
        if self.system_prompt:
            print(f"📝 Adding system prompt: {self.system_prompt[:50]}..." if len(self.system_prompt) > 50 else f"📝 Adding system prompt: {self.system_prompt}")
            formatted_messages.append({"role": "system", "content": self.system_prompt})
        
        for msg in self.messages:
            if isinstance(msg["content"], list):
                # Handle multimodal content - for now just extract text
                text_parts = []
                for part in msg["content"]:
                    if part["type"] == "text":
                        text_parts.append(part["text"])
                formatted_messages.append({
                    "role": msg["role"],
                    "content": " ".join(text_parts)
                })
            else:
                formatted_messages.append(msg)

        # Stream the response using Gemini via OpenAI compatibility layer
        print("\n🔄 Sending request to Gemini API via OpenAI SDK")
        print(f"📤 Model: {self.model}")
        print(f"📤 Number of messages: {len(formatted_messages)}")
        print(f"📤 Number of tools: {len(self.available_tools) if self.available_tools else 0}")
        
        try:
            print("🔄 Making API call to Gemini...")
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=formatted_messages,
                stream=True,
            )
            print("✅ API call successful, processing stream...")

            current_text = ""
            print("🔄 Starting to process response chunks")
            
            # Process the response stream
            async for chunk in response:
                print(f"📦 Received chunk: {chunk}")
                
                if chunk.choices and chunk.choices[0].delta.content:
                    text = chunk.choices[0].delta.content
                    current_text += text
                    print(f"📝 Chunk text: {text}")
                    
                    # Stream the text chunk to the client
                    if self.on_stream:
                        print(f"📤 Streaming text: {text}")
                        await self.on_stream({
                            "type": "text",
                            "content": text
                        })
                    else:
                        print("No streaming handler available")
                
                # Check for tool calls in accumulated text
                tool_call = self._extract_tool_call(current_text)
                if tool_call:
                    print(f"🛠️ Found tool call: {tool_call}")
                    if self.on_stream:
                        print("📤 Streaming tool call")
                        self.tool_response = json.dumps(tool_call)
                        await self.on_stream({
                            "type": "tool",
                            "content": self.tool_response
                        })
                    
                    # Execute tool
                    tool_name = tool_call["tool_name"]
                    tool_func = get_tool_function(tool_name)
                    
                    if tool_func:
                        print(f"🛠️ Executing tool: {tool_name}")
                        tool_result = await tool_func(
                            user_id=self.user_id,
                            message_id=self.message_id,
                            **tool_call.get("parameters", {})
                        )
                        
                        # Add tool result to messages
                        await self.add_message("assistant", {
                            "type": "tool_result",
                            "tool_name": tool_name,
                            "result": tool_result
                        })
                        
                        # Clear current text to prepare for next iteration
                        current_text = ""
                    else:
                        print(f"🛠️ Tool not found: {tool_name}")
                        if self.on_stream:
                            await self.on_stream({
                                "type": "text",
                                "content": f"Tool not found: {tool_name}"
                            })
            # Process final response
            print("\n🌟 Processing final response")
            if current_text:
                print(f"📝 Final response length: {len(current_text)}")
                self.text_response = current_text
                self.full_assistant_content.append({
                    "type": "text",
                    "text": current_text
                })
                final_response = current_text
                print(f"📝 Final response: {current_text[:100]}..." if len(current_text) > 100 else f"📝 Final response: {current_text}")
            else:
                print("⚠️ No text response received from Gemini")

            # Add final response to messages
            if self.full_assistant_content:
                await self.add_message("assistant", self.full_assistant_content)
                
            # Final completion event
            if self.on_stream:
                await self.on_stream({
                    "type": "complete",
                    "content": final_response
                })
                
        except Exception as e:
            import traceback
            print(f"\n❌ Error during Gemini processing: {str(e)}")
            print("\n❌ Traceback:")
            traceback.print_exc()
            
            # Stream error message to client
            if self.on_stream:
                print("📤 Streaming error message")
                await self.on_stream({
                    "type": "text",
                    "content": f"Error: {str(e)}"
                })
            return f"Error: {str(e)}", []

        return final_response, self.full_assistant_content
