import os
import requests
import json
import base64
from pathlib import Path
import asyncio
import time

# Test the compliance API with the new native agent implementation

def test_compliance_api_with_native_agent():
    """Test the image compliance API with our native agent implementation"""
    
    print("\033[94m[TEST] Testing compliance API with native agent implementation\033[0m")
    
    # Path to the test image
    image_path = Path(os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "screenshot.png"))
    
    if not image_path.exists():
        print(f"\033[91m[ERROR] Test image not found at {image_path}\033[0m")
        return False
    
    print(f"\033[92m[TEST] Using test image: {image_path}\033[0m")
    
    # Define the server URL
    base_url = "http://localhost:8000"
    endpoint = "/api/compliance/check-image"  # Correct path includes /api prefix
    
    # Use the provided token directly
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0dXNlcjIiLCJleHAiOjE3NDU5MzEyMDN9.GFb8xsOdM6DtnykEhSmdafIR1eUZbCdMUz7BcLyyGkI"
    print(f"\033[92m[TEST] Using provided token: {token[:10]}...\033[0m")
    
    # Set up headers with the auth token
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # Prepare the multipart form data
    files = {
        "file": (image_path.name, open(image_path, "rb"), "image/png")
    }
    
    data = {
        "text": "This is a Burger King advertisement. Analyze it for brand compliance focusing on logo, colors, typography, and layout."
    }
    
    # Send the request to the server
    try:
        print(f"\033[94m[TEST] Sending request to {base_url + endpoint}\033[0m")
        response = requests.post(
            base_url + endpoint,
            headers=headers,
            files=files,
            data=data,
            stream=True  # Enable streaming
        )
        
        if response.status_code != 200:
            print(f"\033[91m[ERROR] API returned status code {response.status_code}\033[0m")
            print(f"\033[91m[ERROR] Response: {response.text}\033[0m")
            return False
        
        # Process the streaming response
        print("\033[94m[TEST] Processing streaming response...\033[0m")
        
        event_counts = {
            "text": 0,
            "tool": 0,
            "complete": 0,
            "status": 0,
            "error": 0,
            "unknown": 0
        }
        
        # Process the streaming response with more debugging and error handling
        print("\033[94m[TEST] Starting to read SSE response stream...\033[0m")
        
        # Timeout handling
        start_time = time.time()
        max_wait_time = 180  # 3-minute timeout
        last_activity_time = start_time
        
        try:
            for line in response.iter_lines():
                if not line:
                    continue
                    
                # Reset activity timer
                last_activity_time = time.time()
                
                # Decode and print raw line for debugging
                line_str = line.decode('utf-8')
                print(f"\033[96m[RAW] {line_str[:100]}\033[0m")
                
                if not line_str.startswith('data:'):
                    print(f"\033[93m[WARNING] Unexpected line format: {line_str}\033[0m")
                    continue
                    
                # Parse the event
                try:
                    parts = line_str[5:].split(':', 1)
                    if len(parts) != 2:
                        print(f"\033[93m[WARNING] Invalid event format: {line_str}\033[0m")
                        continue
                        
                    event_type, event_data = parts
                    event_type = event_type.strip()
                    event_data = event_data.strip()
                    
                    # Update event counts
                    if event_type in event_counts:
                        event_counts[event_type] += 1
                    else:
                        event_counts["unknown"] += 1
                        print(f"\033[93m[WARNING] Unknown event type: {event_type}\033[0m")
                    
                    # Print event information with more details
                    if event_type == "text":
                        print(f"\033[92m[TEXT EVENT] Received text chunk ({len(event_data)} chars)\033[0m")
                        print(f"\033[92m  First 50 chars: {event_data[:50]}...\033[0m")
                    elif event_type == "tool":
                        print(f"\033[93m[TOOL EVENT] Received tool event ({len(event_data)} chars)\033[0m")
                        try:
                            tool_data = json.loads(event_data)
                            tool_name = tool_data.get("tool_name", "unknown")
                            print(f"\033[93m  Tool name: {tool_name}\033[0m")
                            print(f"\033[93m  Tool input: {tool_data.get('tool_input', {})}\033[0m")
                        except json.JSONDecodeError as e:
                            print(f"\033[91m[ERROR] Invalid tool JSON: {e}\033[0m")
                            print(f"\033[91m  Data: {event_data[:100]}...\033[0m")
                    elif event_type == "complete":
                        print(f"\033[94m[COMPLETE EVENT] Received completion ({len(event_data)} chars)\033[0m")
                        try:
                            if event_data.startswith('{'):
                                completion_data = json.loads(event_data)
                                status = completion_data.get("compliance_status", "unknown")
                                print(f"\033[94m  Compliance status: {status}\033[0m")
                                print(f"\033[94m  Has detailed_report: {'detailed_report' in completion_data}\033[0m")
                                if 'detailed_report' in completion_data:
                                    report_length = len(completion_data['detailed_report'])
                                    print(f"\033[94m  Report length: {report_length} chars\033[0m")
                                    print(f"\033[94m  Report preview: {completion_data['detailed_report'][:100]}...\033[0m")
                        except json.JSONDecodeError as e:
                            print(f"\033[91m[ERROR] Invalid completion JSON: {e}\033[0m")
                            print(f"\033[91m  Data: {event_data[:100]}...\033[0m")
                    else:
                        print(f"\033[95m[OTHER EVENT] Type: {event_type}, Length: {len(event_data)}\033[0m")
                    
                    # If we got a completion event, we're done
                    if event_type == "complete":
                        print("\033[94m[TEST] Received completion event, ending test\033[0m")
                        break
                        
                except Exception as e:
                    print(f"\033[91m[ERROR] Failed to parse event: {str(e)}\033[0m")
                    event_counts["unknown"] += 1
                
                # Check for timeout
                current_time = time.time()
                if current_time - start_time > max_wait_time:
                    print(f"\033[91m[ERROR] Test timed out after {max_wait_time} seconds\033[0m")
                    break
                if current_time - last_activity_time > 30:
                    print(f"\033[93m[WARNING] No activity for 30 seconds\033[0m")
                    # Don't break here, just warn
        except requests.exceptions.ChunkedEncodingError as e:
            print(f"\033[91m[ERROR] Chunked encoding error: {e}\033[0m")
            print("\033[93m[WARNING] This can happen with streaming responses and may not indicate a failure\033[0m")
        
        print("\033[94m[TEST] Streaming complete, event summary:\033[0m")
        for event_type, count in event_counts.items():
            print(f"\033[94m    - {event_type}: {count}\033[0m")
        
        return event_counts["complete"] > 0
        
    except Exception as e:
        print(f"\033[91m[ERROR] Exception during API test: {e}\033[0m")
        return False
    finally:
        # Clean up
        files["file"][1].close()

if __name__ == "__main__":
    test_compliance_api_with_native_agent()
