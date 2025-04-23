import json
import asyncio
import sys
import os
import base64
import mimetypes
from typing import List, Dict, Any, Optional, Callable
from uuid import uuid4
from pydantic import BaseModel
import inspect

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
        if isinstance(content, str):
            message = {"role": role, "content": content}
        else:
            message = {"role": role, "content": content}
        self.messages.append(message)

    async def process_message(
        self, user_input: str | List[Dict[str, Any]] | Dict[str, Any]
    ) -> tuple[str, List[Dict]]:
        print("📝 Current messages ----->")
        print(self.messages)

        if isinstance(user_input, dict) and "image_base64" in user_input:
            image_base64 = user_input.get("image_base64", "")
            media_type = user_input.get("media_type", "image/png")
            text = user_input.get("text", "Analyze this image.")

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
            await self.add_message("user", formatted_message)
        else:
            await self.add_message("user", user_input)
        final_response = ""

        while True:
            self.tool_response = ""
            self.text_response = ""
            self.full_assistant_content = []

            available_models = [
                "claude-3-5-sonnet-20241022",
                "claude-3-7-sonnet-20250219",
                "claude-3-5-haiku-20241022",
            ]
            if self.model in available_models:
                model_order = [self.model] + [m for m in available_models if m != self.model]
            else:
                model_order = available_models

            last_exception = None
            for model_name in model_order:
                try:
                    response, reason = await llm(
                        model=model_name,
                        messages=self.messages,
                        on_stream=self.on_stream,
                        on_stop=self.on_stop,
                        available_tools=self.available_tools,
                        system_prompt=self.system_prompt if self.system_prompt else None,
                    )
                    self.model = model_name
                    break
                except Exception as e:
                    if hasattr(e, "status_code") and getattr(e, "status_code", None) == 429:
                        print(f"Model {model_name} hit 429. Trying next model...")
                        last_exception = e
                        continue
                    elif "429" in str(e) or "Too Many Requests" in str(e):
                        print(f"Model {model_name} hit 429. Trying next model...")
                        last_exception = e
                        continue
                    else:
                        raise
            else:
                if last_exception:
                    raise last_exception
                else:
                    raise RuntimeError("All models failed for unknown reasons.")

            if self.text_response:
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
                        tool_content = {
                            "type": "tool_use",
                            "id": tool_use_id,
                            "name": tool_name,
                            "input": tool_data,
                        }
                        self.full_assistant_content.append(tool_content)

                        await self.add_message("assistant", self.full_assistant_content)
                        print(f"🔧 Using tool: {tool_name}")
                        tool_func = get_tool_function(tool_name)
                        image_base64 = user_input.get("image_base64", "")
                        media_type = user_input.get("media_type", "image/png")
                        text = user_input.get("text", "Analyze this image.")

                        image_dimensions = {}
                        if image_base64:
                            try:
                                image_data = base64.b64decode(image_base64)
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
                        print("🔧 Tool called ✅")

                        tool_result_dict = json.loads(tool_result)

                        message_tool_result = tool_result_dict.copy()
                        if isinstance(message_tool_result, dict):
                            message_tool_result["base64"] = ""
                            message_tool_result["image_dimensions"] = image_dimensions

                        user_message_to_add = [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": json.dumps(message_tool_result),
                            },
                        ]

                        print(f"📊 Tool result: {tool_result_dict}")

                        if tool_result_dict.get("base64"):
                            base64_data = tool_result_dict.get("base64", "")

                            def compress_base64_image(image_base64, quality=60):
                                from io import BytesIO
                                from PIL import Image

                                image_data = base64.b64decode(image_base64)
                                image = Image.open(BytesIO(image_data))

                                with BytesIO() as output:
                                    image.save(output, format="JPEG", quality=quality)
                                    compressed_image_data = output.getvalue()

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
                                        "media_type": "image/jpeg",
                                        "data": compressed_image_base64,
                                    },
                                },
                            )

                        await self.add_message(
                            "user",
                            user_message_to_add,
                        )

                        if tool_name == "attempt_completion":
                            final_response = self.text_response or tool_result
                            break
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

        with open("messages.json", "w") as f:
            json.dump(self.messages, f, indent=4)

        return final_response, self.messages


# # Example usage
# async def test():
#     async def print_stream(data):
#         print(f"\n=== Stream ===\n{data['type']} -> {data['content']}\n=============")

#     agent = Agent(
#         model="claude-3-haiku-20240307",
#         on_stream=print_stream,
#         user_id="test_user",
#         message_id="test_message",
#         system_prompt=system_prompt,
#     )

#     # Read the image file and convert it to base64
#     image_path = os.path.join(backend_dir, "app", "image.png")
#     image_data, media_type = encode_image_to_base64(image_path)

#     # Create a dictionary with image data and text
#     image_message = {
#         "image_base64": image_data,
#         "media_type": media_type,
#         "text": "Can you check if this logo usage is compliant with the brand guidelines? Please identify the brand in the image first, then check its compliance.",
#     }

#     # Process the message with image
#     response, messages = await agent.process_message(image_message)

#     print(f"\n=== Final Response ===\nResponse: {response}")

#     # Store the messages in a json file
#     with open("messages.json", "w") as f:
#         json.dump(messages, f, indent=4)


# if __name__ == "__main__":
#     asyncio.run(test())
