import requests
import os
import time
import json
from pprint import pprint

# API base URL
BASE_URL = "http://localhost:8001"

# Test user credentials
TEST_USER = {
    "username": "testuser2",
    "email": "test2@example.com",
    "full_name": "Test User 2",
    "password": "testpassword123",
}

# Path to the image file for testing
IMAGE_PATH = "app/image.png"  # Use the same image that's used in the agent test


def test_signup():
    """Test user signup"""
    print("\n=== Testing User Signup ===")

    # Check if user already exists
    try:
        response = requests.post(f"{BASE_URL}/signup", json=TEST_USER)

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


def test_login():
    """Test user login and get token"""
    print("\n=== Testing User Login ===")

    try:
        response = requests.post(
            f"{BASE_URL}/token",
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


def test_compliance_check(token):
    """Test the compliance check API with image upload"""
    print("\n=== Testing Compliance Check API ===")

    if not os.path.exists(IMAGE_PATH):
        print(f"Image file not found: {IMAGE_PATH}")
        return None

    try:
        # Prepare the multipart form data
        files = {
            "file": (
                os.path.basename(IMAGE_PATH),
                open(IMAGE_PATH, "rb"),
                "image/png",
            )
        }

        data = {
            "text": "Can you check if this logo usage is compliant with the brand guidelines? Please identify the brand in the image first, then check its compliance.",
        }

        headers = {"Authorization": f"Bearer {token}"}

        # Make the request with stream=True to get the streaming response
        response = requests.post(
            f"{BASE_URL}/api/compliance/check-image",
            files=files,
            data=data,
            headers=headers,
            stream=True,
        )

        if response.status_code == 200:
            print("Request successful, streaming response:")
            print("-" * 50)

            # Process the streaming response manually
            for line in response.iter_lines():
                if line:
                    # Decode the line
                    line = line.decode("utf-8")

                    # Skip lines that don't start with "data:"
                    if not line.startswith("data:"):
                        continue

                    # Extract the data part
                    data = line[5:].strip()

                    # Parse the event data
                    if ":" in data:
                        event_type, content = data.split(":", 1)

                        # Print the event data
                        if event_type == "thinking":
                            print(f"\n[Thinking] {content}")
                        elif event_type == "text":
                            print(f"\n[Text] {content}")
                        elif event_type == "tool":
                            print(f"\n[Tool] {content}")
                        elif event_type == "complete":
                            print(f"\n[Complete] {content}")
                            print("\nStreaming complete!")
                            break
                        else:
                            print(f"\n[{event_type}] {content}")

            print("-" * 50)
            return True
        else:
            print(f"Request failed: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"Error: {str(e)}")
        return None
    finally:
        # Close the file
        files["file"][1].close()


def run_tests():
    """Run all tests"""
    # Test signup
    test_signup()

    # Test login
    token = test_login()
    if not token:
        print("Login failed, cannot continue tests")
        return

    # Test compliance check
    test_compliance_check(token)

    print("\n=== All Tests Completed ===")


if __name__ == "__main__":
    run_tests()
