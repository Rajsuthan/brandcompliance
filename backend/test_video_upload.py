import requests
import os

# Configuration
BASE_URL = "http://localhost:8001/api"  # Assuming server runs on port 8001
VIDEO_ENDPOINT = f"{BASE_URL}/upload-video/"
# Construct the absolute path to the video file relative to this script's location
script_dir = os.path.dirname(os.path.abspath(__file__))
VIDEO_FILE_PATH = os.path.join(
    script_dir, "app", "assets", "youtube_9cPxh2DikIA_1280x720_h264.mp4"
)
VIDEO_CONTENT_TYPE = "video/mp4"


def test_upload_video():
    """
    Tests uploading a video file to the API endpoint.
    """
    print(f"Attempting to upload video from: {VIDEO_FILE_PATH}")
    print(f"Target endpoint: {VIDEO_ENDPOINT}")

    if not os.path.exists(VIDEO_FILE_PATH):
        print(f"Error: Video file not found at {VIDEO_FILE_PATH}")
        return

    try:
        with open(VIDEO_FILE_PATH, "rb") as f:
            files = {"file": (os.path.basename(VIDEO_FILE_PATH), f, VIDEO_CONTENT_TYPE)}
            response = requests.post(
                VIDEO_ENDPOINT, files=files, timeout=60
            )  # Added timeout

        print(f"\n--- Response ---")
        print(f"Status Code: {response.status_code}")
        try:
            response_json = response.json()
            print("Response JSON:")
            import json

            print(json.dumps(response_json, indent=2))
        except requests.exceptions.JSONDecodeError:
            print("Response Content (non-JSON):")
            print(response.text)

        if response.status_code == 201:
            print("\nTest Result: SUCCESS - Video uploaded successfully.")
            # Optionally check response content
            if "filename" in response_json and "url" in response_json:
                print("Filename and URL found in response.")
            else:
                print("Warning: Filename or URL missing in successful response.")
        else:
            print(
                f"\nTest Result: FAILED - Received status code {response.status_code}"
            )

    except requests.exceptions.ConnectionError as e:
        print(f"\nTest Result: FAILED - Connection Error")
        print(f"Could not connect to the server at {VIDEO_ENDPOINT}.")
        print("Please ensure the backend server is running.")
        print(f"Error details: {e}")
    except requests.exceptions.Timeout:
        print(f"\nTest Result: FAILED - Request timed out after 60 seconds.")
    except Exception as e:
        print(f"\nTest Result: FAILED - An unexpected error occurred:")
        print(e)


if __name__ == "__main__":
    test_upload_video()
