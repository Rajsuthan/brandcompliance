import os
import sys
import base64
import asyncio
from pathlib import Path

# Ensure backend/ is in sys.path for absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

from app.core.openrouter_agent.stream_processor import stream_tool_execution
from app.core.openrouter_agent.native_agent import OpenRouterAgent

def load_image_base64(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

async def main():
    # Load API key from env or .env
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key and os.path.exists("../../../.env"):
        from dotenv import load_dotenv
        load_dotenv("../../../.env")
        api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set in environment or .env file")

    # Use the test image
    image_path = "app/assets/screenshot.png"
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    image_base64 = load_image_base64(image_path)

    # Instantiate the agent with streaming disabled
    agent = OpenRouterAgent(
        api_key=api_key,
        model="anthropic/claude-3.7-sonnet",  # Use your production model if different
        stream=False,
        on_stream=None,  # No streaming callback
        save_messages=False
    )

    # Run the process (no streaming)
    result = await agent.process(
        user_prompt="Check this image for brand compliance.",
        image_base64=image_base64,
        frames=None,
        max_iterations=3,
        response_timeout=60,
        retry_count=0
    )

    print("=== AGENT RESULT ===")
    import json
    print(json.dumps(result, indent=2))
    # Print error metadata if present
    if result and "error" in result and isinstance(result["error"], dict):
        error = result["error"]
        if "metadata" in error:
            print("Error metadata:", json.dumps(error["metadata"], indent=2))
            if "raw" in error["metadata"]:
                print("Provider raw error:", error["metadata"]["raw"])

if __name__ == "__main__":
    asyncio.run(main())
