#!/usr/bin/env python3
"""
Ultra-minimal test script with extensive error handling to debug why we can't see errors.
"""

# Import only the most basic Python modules to minimize chances of import errors
import os
import sys
import traceback
import datetime

# Define a log file path for output
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_output.log")

def safe_print(message):
    """Print message to both console and log file, handling any possible errors."""
    try:
        # Print to console with flush
        print(message, flush=True)
        sys.stdout.flush()
        
        # Also write to log file
        with open(LOG_FILE, "a") as f:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {message}\n")
            f.flush()
    except Exception as e:
        # If writing to the log file fails, try one last direct print
        print(f"ERROR LOGGING: {str(e)}", flush=True)
        sys.stderr.flush()

def main():
    """Main function with extensive error handling."""
    try:
        safe_print("\n=== STARTING SUPER MINIMAL TEST ===")
        safe_print(f"Python version: {sys.version}")
        safe_print(f"Current directory: {os.getcwd()}")
        safe_print(f"Log file: {LOG_FILE}")
        
        # Check Python path
        safe_print("\n=== PYTHON PATH ===")
        for i, path in enumerate(sys.path):
            safe_print(f"  {i}: {path}")
        
        # Check environment variables
        safe_print("\n=== ENVIRONMENT VARIABLES ===")
        relevant_vars = ["PYTHONPATH", "TWELVE_LABS_API_KEY", "GOOGLE_APPLICATION_CREDENTIALS"]
        for var in relevant_vars:
            value = os.environ.get(var, "NOT SET")
            if var.endswith("KEY") and value != "NOT SET":
                # Mask API keys for security
                safe_print(f"  {var}: [MASKED]")
            else:
                safe_print(f"  {var}: {value}")
        
        # Attempt basic imports
        safe_print("\n=== TESTING IMPORTS ===")
        
        # Try importing app module
        try:
            safe_print("Trying to import 'app' module...")
            import app
            safe_print("✅ Successfully imported 'app'")
        except ImportError as e:
            safe_print(f"❌ Failed to import 'app': {str(e)}")
            safe_print(f"Traceback: {traceback.format_exc()}")
        
        # Try adding the backend directory to the path
        try:
            safe_print("\nAdding backend directory to Python path...")
            backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            if backend_dir not in sys.path:
                sys.path.insert(0, backend_dir)
                safe_print(f"Added {backend_dir} to sys.path")
            else:
                safe_print(f"{backend_dir} already in sys.path")
        except Exception as e:
            safe_print(f"❌ Failed to add backend directory: {str(e)}")
            safe_print(f"Traceback: {traceback.format_exc()}")
        
        # Try importing twelve_labs client
        try:
            safe_print("\nTrying to import TwelveLabsClient...")
            from app.core.twelve_labs.client import TwelveLabsClient
            safe_print("✅ Successfully imported TwelveLabsClient")
            
            # Try initializing the client
            try:
                safe_print("Trying to initialize TwelveLabsClient...")
                client = TwelveLabsClient()
                safe_print("✅ Successfully initialized TwelveLabsClient")
            except Exception as e:
                safe_print(f"❌ Failed to initialize TwelveLabsClient: {str(e)}")
                safe_print(f"Traceback: {traceback.format_exc()}")
                
        except ImportError as e:
            safe_print(f"❌ Failed to import TwelveLabsClient: {str(e)}")
            safe_print(f"Traceback: {traceback.format_exc()}")
        
        # Try importing Firestore utilities
        try:
            safe_print("\nTrying to import Firestore utilities...")
            from app.db.firebase_utils import get_firestore_client
            safe_print("✅ Successfully imported firebase_utils")
            
            # Try initializing Firestore client
            try:
                safe_print("Trying to initialize Firestore client...")
                db = get_firestore_client()
                safe_print("✅ Successfully initialized Firestore client")
            except Exception as e:
                safe_print(f"❌ Failed to initialize Firestore client: {str(e)}")
                safe_print(f"Traceback: {traceback.format_exc()}")
                
        except ImportError as e:
            safe_print(f"❌ Failed to import firebase_utils: {str(e)}")
            safe_print(f"Traceback: {traceback.format_exc()}")
        
        # Test if we can access the asset directory
        try:
            safe_print("\n=== CHECKING ASSET DIRECTORY ===")
            asset_dir = os.path.abspath(os.path.join(backend_dir, "app", "assets"))
            safe_print(f"Asset directory path: {asset_dir}")
            
            if os.path.exists(asset_dir):
                safe_print(f"✅ Asset directory exists")
                
                # List files in the asset directory
                files = os.listdir(asset_dir)
                safe_print(f"Files in asset directory: {files}")
                
                # Check for the specific video file
                video_filename = "BurgerKing_NonCompliant_LogoInversion (1).mp4"
                video_path = os.path.join(asset_dir, video_filename)
                
                if os.path.exists(video_path):
                    safe_print(f"✅ Test video exists at: {video_path}")
                    safe_print(f"Video size: {os.path.getsize(video_path) / (1024*1024):.2f} MB")
                else:
                    safe_print(f"❌ Test video not found at: {video_path}")
            else:
                safe_print(f"❌ Asset directory does not exist at: {asset_dir}")
                
        except Exception as e:
            safe_print(f"❌ Error checking asset directory: {str(e)}")
            safe_print(f"Traceback: {traceback.format_exc()}")
            
        safe_print("\n=== SUPER MINIMAL TEST COMPLETED ===")
        
    except Exception as e:
        safe_print(f"CRITICAL ERROR IN MAIN: {str(e)}")
        safe_print(f"TRACEBACK: {traceback.format_exc()}")

# Run the main function with top-level error handling
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Last resort error handling
        try:
            print(f"FATAL ERROR: {str(e)}", file=sys.stderr, flush=True)
            print(f"TRACEBACK: {traceback.format_exc()}", file=sys.stderr, flush=True)
            
            with open(LOG_FILE, "a") as f:
                f.write(f"\n[FATAL ERROR] {str(e)}\n")
                f.write(f"TRACEBACK: {traceback.format_exc()}\n")
        except:
            # If absolutely everything fails, try one last direct print
            print("CATASTROPHIC FAILURE - COULD NOT LOG ERROR", file=sys.stderr, flush=True)
