"""Example usage of the Twelve Labs video search implementation.

This script demonstrates how to use the TwelveLabsClient for video upload,
processing, and search functionality.
"""

import os
from dotenv import load_dotenv
from client import TwelveLabsClient

# Load environment variables
load_dotenv()

# Initialize the client
def main():
    """Demonstrate the complete Twelve Labs video search workflow."""
    # Check if API key is set
    api_key = os.getenv("TWELVE_LABS_API_KEY")
    if not api_key:
        print("Please set the TWELVE_LABS_API_KEY environment variable.")
        return
    
    # Initialize the client
    client = TwelveLabsClient()
    
    # Step 1: Create an index
    print("\n=== Creating a new index ===")
    index_name = "brand_compliance_videos"
    index_id = client.create_index(index_name)
    if not index_id:
        print("Failed to create index. Exiting.")
        return
    print(f"Created index: {index_id}")
    
    # Step 2: Upload a video
    print("\n=== Uploading a video ===")
    # Replace with your video path or URL
    video_path = input("Enter path to video file or press Enter to use a URL: ").strip()
    video_url = None
    
    if not video_path:
        video_url = input("Enter video URL: ").strip()
        if not video_url:
            print("No video source provided. Exiting.")
            return
    
    upload_result = client.upload_video(
        index_id=index_id,
        video_file=video_path if video_path else None,
        video_url=video_url
    )
    
    if not upload_result:
        print("Failed to upload video. Exiting.")
        return
    
    task_id = upload_result["task_id"]
    video_id = upload_result["video_id"]
    print(f"Uploaded video: Task ID: {task_id}, Video ID: {video_id}")
    
    # Step 3: Wait for processing to complete
    print("\n=== Waiting for video processing to complete ===")
    if client.wait_for_task_completion(task_id):
        print("Video processing completed successfully")
    else:
        print("Video processing failed. Exiting.")
        return
    
    # Step 4: Search for content in the video
    print("\n=== Searching video content ===")
    while True:
        search_query = input("\nEnter search query (or 'q' to quit): ").strip()
        if search_query.lower() == 'q':
            break
        
        print(f"Searching for: '{search_query}'...")
        results = client.search_videos(
            index_id=index_id,
            query_text=search_query
        )
        
        # Display results
        print(f"\nFound {len(results)} matches:")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['start_time_formatted']} - {result['end_time_formatted']} "
                  f"(Confidence: {result['confidence']}, Score: {result['score']:.2f})")
    
    print("\nSearch demonstration completed.")


if __name__ == "__main__":
    main()
