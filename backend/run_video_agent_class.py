import asyncio
import sys
import os
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = str(Path(__file__).resolve().parent)
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from app.core.video_agent.video_agent_class import VideoAgent


async def main():
    # Create an instance of the VideoAgent
    agent = VideoAgent()

    # Define the video URL and message
    video_url = "https://www.youtube.com/watch?v=9cPxh2DikIA"
    message = "Analyze this video for brand compliance, focusing on logo usage, colors, and tone of voice."

    # Optional: Define specific analysis modes (default is ["visual", "brand_voice", "tone"])
    analysis_modes = ["visual", "brand_voice"]

    print(f"Starting analysis of video: {video_url}")
    print(f"With message: {message}")

    # Generate the analysis
    results = await agent.generate(video_url, message, analysis_modes)

    print("\nAnalysis complete!")
    print(f"Results saved to: {results['filepath']}")

    # Print a summary of the results
    print("\nResults summary:")
    for mode, result in results["results"].items():
        print(f"\n{mode.upper()} Analysis:")
        # Print the first 200 characters of each result
        print(f"{result[:200]}..." if len(result) > 200 else result)


if __name__ == "__main__":
    asyncio.run(main())
