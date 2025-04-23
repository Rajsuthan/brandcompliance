import os
import sys
import asyncio
from app.core.agent.index_gemini_image import Agent, encode_image_to_base64

# Path to the test image (update the filename as needed)
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "app", "assets")
IMAGE_FILENAME = "images (4).jpeg"
IMAGE_PATH = os.path.join(ASSETS_DIR, IMAGE_FILENAME)

async def test_image_agent():
    agent = Agent(model="gemini-2.0-flash-exp")
    image_data, media_type = encode_image_to_base64(IMAGE_PATH)
    image_message = {
        "image_base64": image_data,
        "media_type": media_type,
        "text": "Analyze this image for brand compliance."
    }
    response, messages = await agent.process_message(image_message)
    print("\n=== Gemini Image Agent Response ===\n", response)
    print("\n=== Full Message Trace ===\n", messages)
    # Optionally, save to file for inspection
    with open("gemini_image_agent_messages.json", "w") as f:
        import json
        json.dump(messages, f, indent=4)

if __name__ == "__main__":
    asyncio.run(test_image_agent())
