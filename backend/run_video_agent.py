#!/usr/bin/env python3
"""
Runner script for the video agent module.
This script ensures that the app module is in the Python path.
"""
import os
import sys

# Add the current directory (backend) to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Now import and run the video agent
from app.core.video_agent.llm import generate
import asyncio

if __name__ == "__main__":
    asyncio.run(generate())
