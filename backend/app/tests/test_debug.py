#!/usr/bin/env python3
"""
Simple debug script to check environment and imports
"""

import os
import sys
import importlib.util
from pathlib import Path

def check_file_exists(path):
    """Check if a file exists and print result"""
    exists = os.path.exists(path)
    print(f"  {'✅' if exists else '❌'} {path} - {'exists' if exists else 'not found'}")
    return exists

def check_module_importable(module_name):
    """Check if a module can be imported"""
    try:
        import importlib
        importlib.import_module(module_name)
        print(f"  ✅ {module_name} - can be imported")
        return True
    except ImportError as e:
        print(f"  ❌ {module_name} - import error: {str(e)}")
        return False

def main():
    """Run basic diagnostics"""
    # Print basic environment info
    print("\n=== Environment Information ===")
    print(f"Python version: {sys.version}")
    print(f"Current directory: {os.getcwd()}")
    print(f"Python path: {sys.path}")
    
    # Check project structure
    print("\n=== Project Structure Check ===")
    backend_dir = Path(__file__).parent.parent.parent
    print(f"Backend directory: {backend_dir}")
    
    # Add backend dir to python path
    if str(backend_dir) not in sys.path:
        print(f"Adding {backend_dir} to sys.path")
        sys.path.append(str(backend_dir))
    
    # Check key files
    print("\n=== Key Files Check ===")
    files_to_check = [
        os.path.join(backend_dir, "app", "core", "openrouter_agent", "tools", "search_video.py"),
        os.path.join(backend_dir, "app", "db", "firestore_twelve_labs.py"),
        os.path.join(backend_dir, "app", "core", "video_agent", "twelve_labs_processor.py"),
        os.path.join(backend_dir, "app", "assets", "BurgerKing_NonCompliant_LogoInversion (1).mp4"),
    ]
    
    all_files_exist = True
    for file_path in files_to_check:
        exists = check_file_exists(file_path)
        all_files_exist = all_files_exist and exists
    
    # Try basic imports
    print("\n=== Import Tests ===")
    modules_to_check = [
        "app.db.firebase_utils", 
        "app.db.firestore_twelve_labs",
        "app.core.twelve_labs.client",
        "app.core.openrouter_agent.tools.search_video"
    ]
    
    all_imports_ok = True
    for module in modules_to_check:
        success = check_module_importable(module)
        all_imports_ok = all_imports_ok and success
    
    # Check firebase setup
    print("\n=== Firebase Setup ===")
    try:
        from app.db.firebase_utils import get_firestore_client
        client = get_firestore_client()
        print("  ✅ Firestore client initialized successfully")
    except Exception as e:
        print(f"  ❌ Error initializing Firestore client: {str(e)}")
    
    # Summary
    print("\n=== Diagnostic Summary ===")
    print(f"Files check: {'✅ OK' if all_files_exist else '❌ ISSUES'}")
    print(f"Import check: {'✅ OK' if all_imports_ok else '❌ ISSUES'}")
    
    if not all_files_exist or not all_imports_ok:
        print("\n⚠️  Fix the issues above before running the test script")

if __name__ == "__main__":
    main()
