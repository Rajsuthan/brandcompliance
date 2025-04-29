import asyncio
import base64
import os
import json
import sys
from dotenv import load_dotenv

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
load_dotenv()

# Import the necessary modules
from app.core.openrouter_agent.agent import OpenRouterAgent
from app.core.agent.claude_prompt_updated import claude_system_prompt

# Path to the test image
IMAGE_PATH = "./assets/screenshot.png"

async def on_stream(data):
    """Callback function to handle streaming data from the agent."""
    print(f"\n[{data['type']}]")
    if data['type'] == 'text':
        print(data['content'])
    elif data['type'] == 'tool':
        try:
            tool_content = json.loads(data['content'])
            print(f"Tool call: {tool_content.get('tool_name', 'unknown')}")
        except:
            print(f"Tool content (raw): {data['content']}")
    elif data['type'] == 'complete':
        print("COMPLETION RECEIVED")

async def main():
    print("Starting Claude compliance test...")

    # Use the absolute path directly
    abs_image_path = os.path.abspath(IMAGE_PATH)
    print(f"Trying to open image at: {abs_image_path}")

    # Read and encode the image
    with open(abs_image_path, "rb") as image_file:
        image_base64 = base64.b64encode(image_file.read()).decode("utf-8")

    # Create an OpenRouterAgent instance with Claude model
    agent = OpenRouterAgent(
        model="anthropic/claude-3-7-sonnet-20250219",  # Use Claude 3.7 Sonnet
        on_stream=on_stream,
        system_prompt=claude_system_prompt,  # Use our Claude-specific prompt
    )

    # Process the image
    try:
        await agent.process(
            user_prompt="Analyze this image for brand compliance. Check for any logo blur issues, color palette compliance, and text errors.",
            image_base64=image_base64,
            media_type="image/png",
        )
    except Exception as e:
        print(f"Error during processing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
