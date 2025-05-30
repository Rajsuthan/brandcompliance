#!/usr/bin/env python3
"""
Very basic script to debug issues with output and trace where errors occur.

This script uses only the most basic Python built-ins to minimize chances of errors.
"""

import os
import sys

# Force print to stdout
def force_print(message):
    print(message, flush=True)
    sys.stdout.flush()

force_print("Starting minimal test...")
force_print(f"Python version: {sys.version}")
force_print(f"Current directory: {os.getcwd()}")

# Try importing our modules one by one
try:
    force_print("\nImporting core twelve_labs module...")
    from app.core.twelve_labs.client import TwelveLabsClient
    force_print("✓ Successfully imported TwelveLabsClient")
    
    # Try to initialize the client
    force_print("\nInitializing TwelveLabsClient...")
    try:
        client = TwelveLabsClient()
        force_print("✓ Successfully initialized TwelveLabsClient")
    except Exception as e:
        force_print(f"✗ Failed to initialize TwelveLabsClient: {str(e)}")
    
except ImportError as e:
    force_print(f"✗ Failed to import TwelveLabsClient: {str(e)}")

# Check if we have the API key
force_print("\nChecking environment variables...")
twelve_labs_api_key = os.environ.get("TWELVE_LABS_API_KEY")
if twelve_labs_api_key:
    force_print("✓ TWELVE_LABS_API_KEY is set")
else:
    force_print("✗ TWELVE_LABS_API_KEY is not set")

# Try importing Firebase utilities
try:
    force_print("\nImporting Firebase utilities...")
    from app.db.firebase_utils import get_firestore_client
    force_print("✓ Successfully imported Firebase utilities")
    
    # Try to get Firestore client
    force_print("\nGetting Firestore client...")
    try:
        db = get_firestore_client()
        force_print("✓ Successfully initialized Firestore client")
    except Exception as e:
        force_print(f"✗ Failed to get Firestore client: {str(e)}")
    
except ImportError as e:
    force_print(f"✗ Failed to import Firebase utilities: {str(e)}")

force_print("\nMinimal test completed")
