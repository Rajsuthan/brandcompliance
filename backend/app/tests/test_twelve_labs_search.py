#!/usr/bin/env python3
"""
Simple Test Script for Twelve Labs Video Search Integration

This script provides a command-line interface to test the Twelve Labs video search functionality.
It allows you to:
1. List processed videos for a user
2. Perform searches on a processed video
"""

import os
import sys
import asyncio
import argparse
import traceback
from pathlib import Path

print("Current directory:", os.getcwd())

# Add project root to path for imports
root_path = str(Path(__file__).parent.parent.parent)
print(f"Adding to Python path: {root_path}")
sys.path.append(root_path)

# Try importing with better error handling
try:
    print("Importing firestore_twelve_labs...")
    from app.db.firestore_twelve_labs import get_twelve_labs_mapping, list_twelve_labs_videos
    print("Successfully imported firestore_twelve_labs")
except ImportError as e:
    print(f"Error importing firestore_twelve_labs: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("Importing search_video...")
    from app.core.openrouter_agent.tools.search_video import search_video
    print("Successfully imported search_video")
except ImportError as e:
    print(f"Error importing search_video: {e}")
    traceback.print_exc()
    sys.exit(1)

# Set default values
DEFAULT_USER_ID = "test-user"  # Replace with a real user ID if needed
DEFAULT_QUERY = "burger king logo"
DEFAULT_THRESHOLD = "medium"

async def list_videos(user_id):
    """List all processed videos for a user"""
    print(f"\n=== Processed Videos for User: {user_id} ===\n")
    
    try:
        videos = await list_twelve_labs_videos(user_id)
        
        if not videos or len(videos) == 0:
            print("No processed videos found for this user ID.")
            return
            
        print(f"Found {len(videos)} processed videos:")
        for i, video in enumerate(videos):
            status = video.get("status", "unknown")
            url = video.get("video_url", "unknown")
            created_at = video.get("created_at", "unknown")
            print(f"\n{i+1}. Video URL: {url}")
            print(f"   Status: {status}")
            print(f"   Created: {created_at}")
            
    except Exception as e:
        print(f"Error listing videos: {str(e)}")

async def search_test(video_url, user_id, query, threshold):
    """Test searching a video"""
    print(f"\n=== Searching Video ===\n")
    print(f"Video URL: {video_url}")
    print(f"User ID: {user_id}")
    print(f"Query: '{query}'")
    print(f"Threshold: {threshold}")
    
    try:
        # Create args for search_video function
        args = {
            "query": query,
            "threshold": threshold,
            "task_detail": "Testing video search",
            "video_url": video_url,
            "user_id": user_id
        }
        
        # Execute search
        print("\nExecuting search...")
        result = await search_video(args)
        
        # Print results
        print("\n=== Search Results ===\n")
        print(f"Status: {result.get('status', 'unknown')}")
        
        if "error" in result:
            print(f"Error: {result['error']}")
            return
        
        message = result.get("message", "No message provided")
        print(f"Message: {message}")
        
        results = result.get("results", [])
        if results:
            print("\nFound segments:")
            for i, segment in enumerate(results):
                print(f"\n{i+1}. Timestamp: {segment['timestamp']}")
                print(f"   Confidence: {segment['confidence']}")
                print(f"   Score: {segment['score']}")
        
    except Exception as e:
        print(f"Error during search: {str(e)}")
        import traceback
        traceback.print_exc()

async def main():
    """Parse arguments and execute the requested command"""
    parser = argparse.ArgumentParser(description="Test Twelve Labs Video Search Integration")
    
    # Add subcommands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List processed videos")
    list_parser.add_argument("-u", "--user-id", default=DEFAULT_USER_ID, 
                            help=f"User ID (default: {DEFAULT_USER_ID})")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search a video")
    search_parser.add_argument("video_url", help="URL of the video to search")
    search_parser.add_argument("-u", "--user-id", default=DEFAULT_USER_ID,
                              help=f"User ID (default: {DEFAULT_USER_ID})")
    search_parser.add_argument("-q", "--query", default=DEFAULT_QUERY,
                              help=f"Search query (default: '{DEFAULT_QUERY}')")
    search_parser.add_argument("-t", "--threshold", default=DEFAULT_THRESHOLD,
                              choices=["high", "medium", "low", "none"],
                              help=f"Confidence threshold (default: {DEFAULT_THRESHOLD})")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Execute command
    if args.command == "list":
        await list_videos(args.user_id)
    elif args.command == "search":
        await search_test(args.video_url, args.user_id, args.query, args.threshold)
    else:
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())
