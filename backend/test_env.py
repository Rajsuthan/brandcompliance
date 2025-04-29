import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the OpenRouter API key
openrouter_api_key = os.getenv("OPENROUTER_API_KEY")

# Print the API key (first 5 and last 5 characters for security)
if openrouter_api_key:
    print(f"OpenRouter API Key loaded successfully: {openrouter_api_key[:5]}...{openrouter_api_key[-5:]}")
    print(f"API Key length: {len(openrouter_api_key)}")
else:
    print("OpenRouter API Key not found in environment variables")
