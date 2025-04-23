import json
import asyncio
import sys
import os
import base64
import mimetypes
from typing import List, Dict, Any, Optional, Callable
from uuid import uuid4
from pydantic import BaseModel

# Add the project root to the Python path
# Get the absolute path of the current file
current_file = os.path.abspath(__file__)
# Go up 4 directories (backend/app/core/agent -> backend)
backend_dir = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
)
# Add to Python path
sys.path.insert(0, backend_dir)

# Now we can import using absolute imports
from app.core.agent.llm import llm
from app.core.agent.tools import claude_tools, get_tool_function
from app.core.agent.prompt import system_prompt


def encode_image_to_base64(image_path):
    """
    Read an image file and convert it to base64 encoding.

    Args:
        image_path (str): Path to the image file

    Returns:
        tuple: (base64_encoded_string, media_type)
    """
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")

    # Determine the media type
    media_type = mimetypes.guess_type(image_path)[0]
    if not media_type:
        # Default to png if we can't determine the type
        media_type = "image/png"

    return encoded_string, media_type


# Define Pydantic model for Message only
class Message(BaseModel):
    role: str
    content: List[Dict[str, Any]] | str  # Flexible content: string or list of dicts


class Agent:
    def __init__(
        self,
        model: str = "claude-3-7-sonnet-20250219",
        available_tools: Optional[List[Dict]] = None,
        on_stream: Optional[Callable] = None,
        on_stop: Optional[Callable] = None,
        messages: Optional[List[Message]] = None,
        user_id: Optional[str] = None,
        message_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ):
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
        self.system_prompt = system_prompt

    async def container_on_stream(self, data: Dict[str, Any]):
        """Handle streaming data"""
        print(
            f"\n=== Streaming Event ===\nType: {data['type']}\nContent: {data['content']}\n================"
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
        if isinstance(content, str):
            message = {"role": role, "content": content}
        else:  # Assume content is a list of dicts
            message = {"role": role, "content": content}
        self.messages.append(message)

    async def process_message(
        self, user_input: str | List[Dict[str, Any]] | Dict[str, Any]
    ) -> tuple[str, List[Dict]]:
        """
        Process a user message and return the final response.

        Args:
            user_input: Can be:
                - A string (text-only message)
                - A list of content objects (for messages with images)
                - A dict containing image data and text
        """
        print("current messages ----->")
        print(self.messages)

        # Handle different types of user input
        if isinstance(user_input, dict) and "image_base64" in user_input:
            # Extract image data and text from the dict
            image_base64 = user_input.get("image_base64", "")
            media_type = user_input.get("media_type", "image/png")
            text = user_input.get("text", "Analyze this image.")

            # Format the message with image and text
            formatted_message = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_base64,
                    },
                },
                {
                    "type": "text",
                    "text": text,
                },
            ]

            # Add the formatted message to the conversation
            await self.add_message("user", formatted_message)
        else:
            # Add the user message to the conversation as is
            await self.add_message("user", user_input)
        final_response = ""

        while True:
            self.tool_response = ""
            self.text_response = ""
            self.full_assistant_content = []

            response, reason = await llm(
                model=self.model,
                messages=self.messages,
                on_stream=self.on_stream,
                on_stop=self.on_stop,
                available_tools=self.available_tools,
                system_prompt=self.system_prompt if self.system_prompt else None,
            )

            if self.text_response:
                # Only include type and text for text content
                self.full_assistant_content.append(
                    {"type": "text", "text": self.text_response}
                )
                final_response = self.text_response

            if self.tool_response:
                try:
                    tool_data = json.loads(self.tool_response)
                    tool_name = tool_data.get("tool_name")
                    if tool_name:
                        tool_use_id = str(uuid4())
                        tool_data.update(
                            {"user_id": self.user_id, "message_id": self.message_id}
                        )
                        # Only include fields relevant to tool_use
                        tool_content = {
                            "type": "tool_use",
                            "id": tool_use_id,
                            "name": tool_name,
                            "input": tool_data,
                        }
                        self.full_assistant_content.append(tool_content)

                        await self.add_message("assistant", self.full_assistant_content)
                        print(tool_name)
                        tool_func = get_tool_function(tool_name)
                        image_base64 = user_input.get("image_base64", "")
                        media_type = user_input.get("media_type", "image/png")
                        text = user_input.get("text", "Analyze this image.")

                        # Extract image dimensions if available
                        image_dimensions = {}
                        if image_base64:
                            try:
                                # Decode the base64 string into binary data
                                image_data = base64.b64decode(image_base64)

                                # Open the image using PIL to get dimensions
                                from PIL import Image
                                from io import BytesIO

                                with Image.open(BytesIO(image_data)) as img:
                                    image_dimensions = {
                                        "width": img.width,
                                        "height": img.height,
                                    }
                            except Exception as e:
                                print(f"Error extracting image dimensions: {str(e)}")

                        image_data_uri = f"{image_base64}"
                        tool_input = {
                            **tool_data,
                            "image_base64": image_data_uri,
                            "image_dimensions": image_dimensions,
                        }
                        tool_result = await tool_func(tool_input)
                        print("tool called ✅✅✅")

                        # Parse the stringified JSON result
                        tool_result_dict = json.loads(tool_result)

                        # Create a copy without base64 for the message
                        message_tool_result = tool_result_dict.copy()
                        if isinstance(message_tool_result, dict):
                            message_tool_result["base64"] = ""
                            # Add image dimensions to the message tool result
                            message_tool_result["image_dimensions"] = image_dimensions

                        user_message_to_add = [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": json.dumps(message_tool_result),
                            },
                        ]

                        print(tool_result_dict)

                        if tool_result_dict.get("base64"):
                            # Compress the base64 data
                            base64_data = tool_result_dict.get("base64", "")

                            def compress_base64_image(image_base64, quality=60):
                                """
                                Compress a base64-encoded image

                                Args:
                                    image_base64 (str): Base64-encoded image data
                                    quality (int, optional): JPEG quality. Defaults to 70.

                                Returns:
                                    str: Compressed base64-encoded image data
                                """
                                from io import BytesIO
                                from PIL import Image

                                # Decode the base64 string into binary data
                                image_data = base64.b64decode(image_base64)

                                # Open the image using PIL
                                image = Image.open(BytesIO(image_data))

                                # Compress the image and save it to a BytesIO object
                                with BytesIO() as output:
                                    image.save(output, format="JPEG", quality=quality)

                                    # Get the compressed image data from the BytesIO object
                                    compressed_image_data = output.getvalue()

                                # Re-encode the compressed image to base64
                                compressed_image_base64 = base64.b64encode(
                                    compressed_image_data
                                ).decode("utf-8")

                                return compressed_image_base64

                            compressed_image_base64 = compress_base64_image(base64_data)

                            user_message_to_add.append(
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/jpeg",  # Assuming JPEG
                                        "data": compressed_image_base64,
                                    },
                                },
                            )

                        # Only include fields relevant to tool_result
                        await self.add_message(
                            "user",
                            user_message_to_add,
                        )

                        if tool_name == "attempt_completion":
                            final_response = self.text_response or tool_result
                            break
                        # continue
                    else:
                        break
                except json.JSONDecodeError:
                    final_response = self.text_response or self.tool_response
                    break
            else:
                break

        if self.full_assistant_content and not any(
            m.get("role") == "assistant"
            and m.get("content") == self.full_assistant_content
            for m in self.messages
        ):
            await self.add_message("assistant", self.full_assistant_content)

        return final_response, self.messages


# Example usage
async def test():
    async def print_stream(data):
        print(f"\n=== Stream ===\n{data['type']} -> {data['content']}\n=============")

    agent = Agent(
        model="claude-3-7-sonnet-20250219",
        on_stream=print_stream,
        user_id="test_user",
        message_id="test_message",
        system_prompt=system_prompt,
    )

    # Read the image file and convert it to base64
    image_path = os.path.join(backend_dir, "app", "image.png")
    image_data, media_type = encode_image_to_base64(image_path)

    # Create a dictionary with image data and text
    image_message = {
        "image_base64": image_data,
        "media_type": media_type,
        "text": "Can you check if this logo usage is compliant with the brand guidelines? Please identify the brand in the image first, then check its compliance.",
    }

    # Process the message with image
    response, messages = await agent.process_message(image_message)

    print(f"\n=== Final Response ===\nResponse: {response}")

    # Store the messages in a json file
    with open("messages.json", "w") as f:
        json.dump(messages, f, indent=4)


if __name__ == "__main__":
    asyncio.run(test())
