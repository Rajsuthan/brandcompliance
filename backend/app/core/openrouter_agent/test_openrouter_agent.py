import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

import asyncio
import base64
from app.core.openrouter_agent.agent import OpenRouterAgent
from app.core.agent.prompt import gemini_system_prompt

def load_test_image_base64(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

async def test_streaming_image_compliance():
    # Use a sample image from test_images/
    image_path = os.path.join("test_images", "stock-photo-krasnoyarsk-russia-september-plastic-bottle-of-fake-coca-cola-under-the-russian-brand-2202259187.jpg")
    image_base64 = load_test_image_base64(image_path)
    media_type = "image/jpeg"
    prompt = "Analyze this image for brand compliance."

    print("Starting streaming test for image compliance...\n")

    # Define the streaming callback
    async def on_stream(data):
        event_type = data.get("type")
        if event_type in ("text", "tool", "complete"):
            print(f"{event_type}: {data.get('content', '')}")
        else:
            print(f"{event_type}: {data}")

    agent = OpenRouterAgent(
        model="anthropic/claude-3-sonnet-20240229",
        on_stream=on_stream,
        system_prompt=gemini_system_prompt,
    )

    await agent.process(
        user_prompt=prompt,
        image_base64=image_base64,
        media_type=media_type,
    )

if __name__ == "__main__":
    asyncio.run(test_streaming_image_compliance())
