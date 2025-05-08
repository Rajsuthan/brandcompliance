#!/usr/bin/env python3
"""
Script to analyze the benchmark Excel file.

This script reads the benchmark Excel file and prints information about its structure
and the test cases it contains.
"""

import os
import sys
import json
from app.core.benchmark.excel_reader import read_and_analyze_benchmark

def main():
    """Main function to analyze the benchmark Excel file."""
    # Default path to the benchmark Excel file
    default_excel_path = "benchmark/benchark_excel.xlsx"

    # Get the Excel file path from command line arguments or use the default
    excel_path = sys.argv[1] if len(sys.argv) > 1 else default_excel_path

    # Get the asset directory from command line arguments or use None
    asset_dir = None
    if len(sys.argv) > 2 and not sys.argv[2].startswith("--"):
        asset_dir = sys.argv[2]

    # Check if we should require assets to exist
    require_assets = "--require-assets" in sys.argv

    # Get the mapping file from command line arguments or use the default
    mapping_file = None
    for arg in sys.argv:
        if arg.startswith("--mapping="):
            mapping_file = arg.split("=")[1]
            break

    # If no mapping file is specified, use the default
    if not mapping_file:
        default_mapping = "benchmark/asset_mapping.json"
        if os.path.exists(default_mapping):
            mapping_file = default_mapping

    print(f"Analyzing benchmark Excel file: {excel_path}")
    if asset_dir:
        print(f"Using asset directory: {asset_dir}")
    if mapping_file:
        print(f"Using asset mapping file: {mapping_file}")
    print(f"Requiring assets to exist: {require_assets}")

    try:
        # Read and analyze the benchmark Excel file
        results = read_and_analyze_benchmark(excel_path, asset_dir, mapping_file, require_assets)

        # Print the results
        print("\n=== Excel Structure ===")
        print(f"Columns: {results['structure']['columns']}")
        print(f"Row count: {results['structure']['row_count']}")
        print(f"Asset types: {results['structure']['asset_types']}")
        print(f"Missing values: {results['structure']['missing_values']}")

        print("\n=== Test Cases ===")
        print(f"Total: {len(results['test_cases'])}")
        print(f"Valid: {len(results['valid_test_cases'])}")
        print(f"Invalid: {len(results['invalid_test_cases'])}")

        # Print a sample valid test case
        if results['valid_test_cases']:
            print("\n=== Sample Valid Test Case ===")
            print(json.dumps(results['valid_test_cases'][0], indent=2))

        # Print a sample invalid test case
        if results['invalid_test_cases']:
            print("\n=== Sample Invalid Test Case ===")
            print(json.dumps(results['invalid_test_cases'][0], indent=2))

        # Print all test cases if requested
        if "--all" in sys.argv:
            print("\n=== All Test Cases ===")
            for i, test_case in enumerate(results['test_cases']):
                print(f"\nTest Case {i+1}:")
                print(json.dumps(test_case, indent=2))

        # Save the results to a JSON file if requested
        if "--save" in sys.argv:
            output_file = "benchmark_analysis.json"
            with open(output_file, "w") as f:
                json.dump(results, f, indent=2)
            print(f"\nResults saved to {output_file}")

        # Save just the test cases to a JSON file if requested
        if "--save-test-cases" in sys.argv:
            output_file = "benchmark_test_cases.json"
            with open(output_file, "w") as f:
                json.dump(results['valid_test_cases'], f, indent=2)
            print(f"\nTest cases saved to {output_file}")

    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
