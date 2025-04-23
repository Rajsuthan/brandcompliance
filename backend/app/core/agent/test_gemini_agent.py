import os
import asyncio
import json
from typing import Dict, Any
from dotenv import load_dotenv
from app.core.agent.gemini_agent import GeminiAgent, encode_image_to_base64

# Load environment variables
load_dotenv()

# Get the absolute path of the test image
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets")
TEST_IMAGE = os.path.join(ASSETS_DIR, "images (4).jpeg")

async def on_stream(data: Dict[str, Any]):
    """Callback function to handle streaming events"""
    print(f"\n=== Streaming Event ===")
    print(f"Type: {data['type']}")
    print(f"Content: {data['content']}")
    print("=====================")

async def test_image_analysis():
    """Test the GeminiAgent with an image analysis task"""
    print("\n🚀 Starting Gemini Agent test...")
    
    # Check for API key
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("\n❌ Error: GOOGLE_API_KEY environment variable is not set")
        print("Please set it in your .env file or environment variables")
        return
    
    print(f"\n🔑 Using API key: {api_key[:5]}...{api_key[-5:]}")
    
    # Create an agent instance
    agent = GeminiAgent(
        model="gemini-2.0-flash",
        on_stream=on_stream,
        user_id="test_user",
        message_id="test_message"
    )
    
    # Prepare the image message
    with open(TEST_IMAGE, "rb") as f:
        image_message = {
            "image_base64": encode_image_to_base64(TEST_IMAGE)[0],
            "media_type": "image/jpeg",
            "text": "Analyze this image for brand compliance. Focus on the following aspects:\n" + 
                   "1. Visual Identity (logos, colors, typography)\n" +
                   "2. Brand Voice and Tone\n" +
                   "3. Core Messaging\n" +
                   "4. Overall Compliance Score. Brand name is In-N-Out"
        }
    
    print("\n📸 Processing image:", TEST_IMAGE)
    
    try:
        print("\n📦 Sending request to Gemini API...")
        # Process the image
        final_response, messages = await agent.process_message(image_message)
        
        print("\n✅ Test completed successfully!")
        
        if final_response:
            print("\n💬 Final Response:", final_response)
        else:
            print("\n⚠️ Warning: No final response received")
            
        if messages:
            print("\n📃 Full Messages:", json.dumps(messages, indent=2))
        else:
            print("\n⚠️ Warning: No messages received")
        
    except Exception as e:
        import traceback
        print("\n❌ Test failed with error:", str(e))
        print("\n📝 Traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_image_analysis())
