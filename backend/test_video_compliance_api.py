import asyncio
import sys
import os
import requests
import json
from pathlib import Path
from sseclient import SSEClient

# Add the backend directory to the Python path
backend_dir = str(Path(__file__).resolve().parent)
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

# Test user credentials
TEST_USER = {
    "username": "testuser2",
    "email": "test2@example.com",
    "full_name": "Test User 2",
    "password": "testpassword123",
}


def test_signup(base_url):
    """Test user signup"""
    print("\n=== Testing User Signup ===")

    # Check if user already exists
    try:
        response = requests.post(f"{base_url}/signup", json=TEST_USER)

        if response.status_code == 200:
            print("User created successfully")
            return response.json()
        elif (
            response.status_code == 400
            and "already registered" in response.json().get("detail", "")
        ):
            print("User already exists")
            return None
        else:
            print(f"Error creating user: {response.status_code}")
            print(response.json())
            return None
    except Exception as e:
        print(f"Error: {str(e)}")
        return None


def test_login(base_url):
    """Test user login and get token"""
    print("\n=== Testing User Login ===")

    try:
        response = requests.post(
            f"{base_url}/token",
            json={"username": TEST_USER["username"], "password": TEST_USER["password"]},
        )

        if response.status_code == 200:
            token_data = response.json()
            print("Login successful")
            print(f"Token: {token_data['access_token'][:20]}...")
            return token_data["access_token"]
        else:
            print(f"Login failed: {response.status_code}")
            print(response.json())
            return None
    except Exception as e:
        print(f"Error: {str(e)}")
        return None


async def test_video_compliance_api():
    """Test the video compliance API endpoint."""
    # Replace with your actual API endpoint and authentication
    base_url = "http://localhost:8000"
    api_endpoint = f"{base_url}/api/compliance/check-video"

    # First create a test user
    test_signup(base_url)

    # Then get authentication token
    token = test_login(base_url)
    if not token:
        print("Login failed, cannot continue tests")
        return

    try:
        # Prepare headers with authentication
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # Prepare video data
        video_data = {
            "video_url": "https://www.youtube.com/watch?v=9cPxh2DikIA",
            "message": "Analyze this video for brand compliance, focusing on logo usage, colors, and tone of voice.",
            "analysis_modes": ["visual", "brand_voice"],
        }

        # Make the API request with streaming response
        print(f"Sending request to {api_endpoint}...")
        response = requests.post(
            api_endpoint, json=video_data, headers=headers, stream=True
        )
        response.raise_for_status()

        # Process the streaming response
        client = SSEClient(response)
        for event in client.events():
            if event.data:
                event_type, event_content = event.data.split(":", 1)
                print(f"\nEvent Type: {event_type}")

                if event_type == "complete":
                    # Parse the final results
                    results = json.loads(event_content)
                    print("\nAnalysis complete!")
                    print(f"Results saved to: {results['filepath']}")

                    # Print a summary of the results
                    print("\nResults summary:")
                    for mode, result in results["results"].items():
                        print(f"\n{mode.upper()} Analysis:")
                        # Print the first 200 characters of each result
                        print(f"{result[:200]}..." if len(result) > 200 else result)
                else:
                    print(
                        f"Content: {event_content[:100]}..."
                        if len(event_content) > 100
                        else event_content
                    )

    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {str(e)}")
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(test_video_compliance_api())
