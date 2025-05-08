#!/usr/bin/env python3
"""
Script to test the asset mapping.

This script reads the benchmark Excel file and maps the asset names to local file paths.
"""

import os
import sys
import json
from app.core.benchmark.excel_reader import read_benchmark_excel, extract_test_cases
from app.core.benchmark.asset_mapper import update_test_cases_with_file_paths, save_asset_mapping

def main():
    """Main function to test the asset mapping."""
    # Default path to the benchmark Excel file
    default_excel_path = "benchmark/benchark_excel.xlsx"
    
    # Default path to the asset folder
    default_asset_folder = "files_for_testing"
    
    # Get the Excel file path from command line arguments or use the default
    excel_path = sys.argv[1] if len(sys.argv) > 1 else default_excel_path
    
    # Get the asset folder from command line arguments or use the default
    asset_folder = sys.argv[2] if len(sys.argv) > 2 else default_asset_folder
    
    print(f"Testing asset mapping with Excel file: {excel_path}")
    print(f"Using asset folder: {asset_folder}")
    
    try:
        # Read the Excel file
        df = read_benchmark_excel(excel_path)
        
        # Extract test cases
        test_cases = extract_test_cases(df)
        
        # Update test cases with file paths
        updated_test_cases = update_test_cases_with_file_paths(test_cases, asset_folder)
        
        # Count test cases with and without assets
        with_assets = sum(1 for tc in updated_test_cases if tc.get('asset_exists', False))
        without_assets = len(updated_test_cases) - with_assets
        
        print(f"\n=== Asset Mapping Results ===")
        print(f"Total test cases: {len(updated_test_cases)}")
        print(f"Test cases with mapped assets: {with_assets}")
        print(f"Test cases without mapped assets: {without_assets}")
        
        # Print test cases with mapped assets
        print("\n=== Test Cases with Mapped Assets ===")
        for i, tc in enumerate(updated_test_cases):
            if tc.get('asset_exists', False):
                print(f"\n{i+1}. {tc.get('asset_name', 'Unknown')}")
                print(f"   Asset path: {tc.get('asset_path', 'Unknown')}")
                print(f"   Asset type: {tc.get('asset_type', 'Unknown')}")
        
        # Print test cases without mapped assets
        print("\n=== Test Cases without Mapped Assets ===")
        for i, tc in enumerate(updated_test_cases):
            if not tc.get('asset_exists', False):
                print(f"\n{i+1}. {tc.get('asset_name', 'Unknown')}")
                print(f"   Asset type: {tc.get('asset_type', 'Unknown')}")
        
        # Save the mapping to a JSON file if requested
        if "--save" in sys.argv:
            # Create a mapping from asset names to file paths
            mapping = {}
            for tc in updated_test_cases:
                if tc.get('asset_exists', False) and tc.get('asset_name') and tc.get('asset_path'):
                    mapping[tc['asset_name']] = tc['asset_path']
            
            # Save the mapping
            output_file = "asset_mapping.json"
            save_asset_mapping(mapping, output_file)
    
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
