"""Configuration module for Twelve Labs SDK integration.

This module handles environment setup and SDK initialization.
"""

import os
from typing import Optional

from twelvelabs import TwelveLabs
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key from environment variables
TWELVE_LABS_API_KEY = os.getenv("TWELVE_LABS_API_KEY")


def get_client(api_key: Optional[str] = None) -> TwelveLabs:
    """Initialize and return the Twelve Labs SDK client.
    
    Args:
        api_key: Optional API key to use instead of the one from environment variables
        
    Returns:
        Initialized TwelveLabs client
        
    Raises:
        ValueError: If no API key is provided and none is found in environment variables
    """
    # Use provided API key or fallback to environment variable
    api_key = api_key or TWELVE_LABS_API_KEY
    
    if not api_key:
        raise ValueError(
            "Twelve Labs API key not found. "
            "Please provide an API key or set the TWELVE_LABS_API_KEY environment variable."
        )
    
    # Initialize the SDK client
    return TwelveLabs(api_key=api_key)
