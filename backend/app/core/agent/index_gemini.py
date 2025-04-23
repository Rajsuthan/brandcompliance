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
current_file = os.path.abspath(__file__)
backend_dir = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
)
sys.path.insert(0, backend_dir)

from app.core.agent.prompt import gemini_system_prompt

# Gemini-specific LLM import (assume gemini_llm.py has an async llm function)
from app.core.video_agent.gemini_llm import llm as gemini_llm


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


class Agent:
    def __init__(
        self,
        on_stream: Optional[Callable] = None,
        on_stop: Optional[Callable] = None,
        messages: Optional[List[Message]] = None,
        user_id: Optional[str] = None,
        message_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ):
        self.model = "gemini-2.0-flash"
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

    async def container_on_stream(self, data: Dict[str, Any]):
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
        # --- Handle user input (match index.py) ---
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
        # --- Main Gemini LLM/Tool loop (faithful to index.py) ---
        while True:
            self.tool_response = ""
            self.text_response = ""
            self.full_assistant_content = []
            response, reason = await gemini_llm(
                model=self.model,
                messages=self.messages,
                on_stream=self.on_stream,
                on_stop=self.on_stop,
                system_prompt=self.system_prompt,
                user_id=self.user_id,
                message_id=self.message_id,
            )
            if self.text_response:
                self.full_assistant_content.append({"type": "text", "text": self.text_response})
                final_response = self.text_response
            # --- Gemini XML tool extraction (replica of gemini_llm.py logic) ---
            import re
            import xmltodict
            xml_dict = None
            json_tool_name = None
            content_to_process = None
            is_xml = False
            final_text = self.tool_response or self.text_response or ""
            # 1. Try strict code block extraction
            if ("```xml" in final_text and "```" in final_text.split("```xml")[1]):
                try:
                    xml_content = final_text.split("```xml")[1].split("```", 1)[0].strip()
                    content_to_process = xml_content
                    xml_dict = xmltodict.parse(xml_content)
                    is_xml = True
                    json_tool_name = list(xml_dict.keys())[0]
                except Exception:
                    is_xml = False
            # 2. Try direct regex extraction for <tool>...</tool>
            if not is_xml:
                xml_pattern = r"<([a-zA-Z0-9_]+)>(.*?)</\\1>"
                xml_matches = re.findall(xml_pattern, final_text, re.DOTALL)
                if xml_matches:
                    try:
                        root_tag, content = xml_matches[0]
                        reconstructed_xml = f"<{root_tag}>{content}</{root_tag}>"
                        xml_dict = xmltodict.parse(reconstructed_xml)
                        is_xml = True
                        content_to_process = reconstructed_xml
                        json_tool_name = root_tag
                    except Exception:
                        is_xml = False
            # 3. Try flexible code block regex (lenient)
            if not is_xml:
                code_block_pattern = r"```(?:xml)?\\s*(.*?)```"
                code_blocks = re.findall(code_block_pattern, final_text, re.DOTALL)
                for block in code_blocks:
                    try:
                        block = block.strip()
                        if block and block[0] == "<" and block[-1] == ">":
                            xml_dict = xmltodict.parse(block)
                            is_xml = True
                            content_to_process = block
                            json_tool_name = list(xml_dict.keys())[0]
                            break
                    except Exception:
                        continue
            # --- Tool execution and feedback loop (replica of index.py) ---
            if is_xml and xml_dict and json_tool_name:
                tool_input = xml_dict[json_tool_name]
                from app.core.agent.tools import get_tool_function
                tool_func = get_tool_function(json_tool_name)
                if tool_func:
                    try:
                        import asyncio
                        if asyncio.iscoroutinefunction(tool_func):
                            tool_result = await tool_func(tool_input)
                        else:
                            tool_result = tool_func(tool_input)
                        tool_result_msg = [{"type": "tool_result", "tool": json_tool_name, "input": tool_input, "result": tool_result}]
                        await self.add_message("assistant", tool_result_msg)
                        print(f"🔧 Using tool: {json_tool_name}")
                        continue
                    except Exception as e:
                        error_msg = f"Tool '{json_tool_name}' execution failed: {e}"
                        await self.add_message("assistant", error_msg)
                        final_response = error_msg
                        break
                else:
                    error_msg = f"Unknown tool: {json_tool_name}"
                    await self.add_message("assistant", error_msg)
                    final_response = error_msg
                    break
            else:
                break
        # --- Final assistant message and return (match index.py) ---
        if self.full_assistant_content and not any(
            m.get("role") == "assistant"
            and m.get("content") == self.full_assistant_content
            for m in self.messages
        ):
            await self.add_message("assistant", self.full_assistant_content)
        with open("messages.json", "w") as f:
            json.dump(self.messages, f, indent=4)
        return final_response, self.messages

# Example usage
def main():
    async def print_stream(data):
        print(f"\n=== Stream ===\n{data['type']} -> {data['content']}\n=============")
    agent = Agent(
        on_stream=print_stream,
        user_id="test_user",
        message_id="test_message",
    )
    image_path = os.path.join(backend_dir, "app", "image.png")
    image_data, media_type = encode_image_to_base64(image_path)
    image_message = {
        "image_base64": image_data,
        "media_type": media_type,
        "text": "Can you check if this logo usage is compliant with the brand guidelines? Please identify the brand in the image first, then check its compliance.",
    }
    async def run():
        response, messages = await agent.process_message(image_message)
        print(f"\n=== Final Response ===\nResponse: {response}")
        with open("messages.json", "w") as f:
            json.dump(messages, f, indent=4)
    asyncio.run(run())

if __name__ == "__main__":
    main()
