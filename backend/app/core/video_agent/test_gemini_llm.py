import asyncio
import sys
import os
from pathlib import Path

# Ensure project root is in sys.path for absolute imports
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from app.core.video_agent.gemini_llm import generate

# Usage: python test_gemini_llm.py <local_video_path>

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_gemini_llm.py <local_video_path>")
        sys.exit(1)
    video_path = sys.argv[1]
    if not os.path.exists(video_path):
        print(f"Video file does not exist: {video_path}")
        sys.exit(1)
    print(f"Testing Gemini LLM video compliance on: {video_path}")
    try:
        results = asyncio.run(generate(video_path))
        print("\n===== Gemini LLM Analysis Results =====")
        print(results)
        print("\nTest completed successfully.")
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
