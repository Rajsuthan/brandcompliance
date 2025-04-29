import os
import asyncio
import base64
import json
import sys
from typing import Dict, Any

# Add the backend directory to the Python path
# This makes imports like 'from app.core...' work correctly
sys.path.append('/Users/shanjairaj/Documents/projects/compliance-proj/backend')

# Now we can import our modules
from app.core.openrouter_agent.native_agent import OpenRouterAgent

# Get the OpenRouter API key from environment variables
API_KEY = os.environ.get("OPENROUTER_API_KEY")
if not API_KEY or API_KEY == "your_api_key_here":
    print("\n\033[91mError: Please set a valid OPENROUTER_API_KEY environment variable\033[0m")
    print("Run the script with: OPENROUTER_API_KEY=your_actual_key python -m backend.app.tests.test_native_agent\n")
    sys.exit(1)

# Path to test image
IMAGE_PATH = "/Users/shanjairaj/Documents/projects/compliance-proj/backend/app/assets/screenshot.png"

# Function to read and encode the image as base64
def get_base64_image(image_path: str) -> str:
    """Read an image file and encode it as base64."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

# Callback for processing streaming responses
async def on_stream(content: Dict[str, Any]) -> None:
    """Process streaming content from the agent."""
    content_type = content.get("type")
    
    if content_type == "text":
        print(f"TEXT: {content.get('content')}")
    elif content_type == "tool":
        print(f"TOOL: {content.get('tool_name')}")
        # Attempt to format the tool result for better readability
        try:
            tool_data = json.loads(content.get('content', '{}'))
            print(f"  Input: {json.dumps(tool_data.get('tool_input'), indent=2)[:100]}...")
            print(f"  Result: {json.dumps(tool_data.get('tool_result'), indent=2)[:100]}...")
        except json.JSONDecodeError:
            print(f"  Raw content: {content.get('content')[:100]}...")
    elif content_type == "complete":
        print(f"COMPLETE: {content.get('content')}")

# Main test function
async def test_native_agent() -> None:
    """Test the OpenRouter agent with an image."""
    print("\n🔍 Testing OpenRouter Native Agent...\n")
    
    # Initialize agent with streaming
    agent = OpenRouterAgent(
        api_key=API_KEY,
        model="anthropic/claude-3.5-sonnet",  # Use the specified model ID
        on_stream=on_stream,
        temperature=0.2,
        stream=True,
    )
    
    print(f"\033[94mUsing API key: {API_KEY[:4]}...{API_KEY[-4:]}\033[0m")
    
    # Get test image as base64
    try:
        image_base64 = get_base64_image(IMAGE_PATH)
        print(f"📷 Loaded test image: {IMAGE_PATH}")
    except Exception as e:
        print(f"❌ Failed to load test image: {e}")
        return
    
    # Test prompt that's specific about image analysis and provides clear instructions
    prompt = "This is a static image (not a video) from a Burger King advertisement. Perform a brand compliance analysis focusing on: 1) color scheme adherence to brand guidelines, 2) logo placement and usage, 3) typography standards, and 4) any text content. This analysis is for internal review purposes."
    
    print(f"🔊 Sending prompt: '{prompt}'")
    print("⏳ Waiting for response...\n")
    
    try:
        # Process the request with image
        # Limit iterations to 5 for testing purposes
        result = await agent.process(
            user_prompt=prompt,
            image_base64=image_base64,
            max_iterations=2,  # Strict limit on iterations for testing
            retry_count=1,     # Just one retry for quicker testing
            max_tokens=200,    # Limit token generation to prevent verbose responses
            response_timeout=60  # Increased timeout for proper testing
        )
        
        # Print the final result
        print("\n✅ Test completed")
        print(f"📊 Success: {result.get('success')}")
        
        # Print tool trace
        tool_trace = result.get('tool_trace', [])
        if tool_trace:
            print(f"🔧 Tools used: {len(tool_trace)}")
            for i, tool in enumerate(tool_trace):
                print(f"  Tool {i+1}: {tool.get('tool')}")
        else:
            print("❓ No tools were used")
            
    except KeyboardInterrupt:
        print("\n⛔️ Test interrupted by user")
        return
    except Exception as e:
        if "401" in str(e) or "auth" in str(e).lower():
            print(f"\n❗️ Authentication error: Check your OPENROUTER_API_KEY\n{str(e)}")
        else:
            print(f"\n❗️ Test failed: {e}")

# Run the test
if __name__ == "__main__":
    asyncio.run(test_native_agent())
