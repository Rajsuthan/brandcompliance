"""
Excel reader module for the benchmark system.

This module provides functions to read and parse the benchmark Excel file.
"""

import os
import pandas as pd
from typing import List, Dict, Optional, Tuple, Any
import logging

# Import the asset mapper
from app.core.benchmark.asset_mapper import update_test_cases_with_file_paths

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def read_benchmark_excel(file_path: str) -> pd.DataFrame:
    """
    Read the benchmark Excel file and return a DataFrame.

    Args:
        file_path: Path to the Excel file

    Returns:
        DataFrame containing the benchmark data

    Raises:
        FileNotFoundError: If the Excel file doesn't exist
        ValueError: If the Excel file has an invalid format
    """
    # Check if the file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Excel file not found: {file_path}")

    # Read the Excel file
    try:
        df = pd.read_excel(file_path)
        logger.info(f"Successfully read Excel file: {file_path}")
        logger.info(f"Found {len(df)} rows in the Excel file")
        return df
    except Exception as e:
        logger.error(f"Failed to read Excel file: {str(e)}")
        raise ValueError(f"Failed to read Excel file: {str(e)}")

def analyze_excel_structure(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyze the structure of the Excel file and return information about it.

    Args:
        df: DataFrame containing the benchmark data

    Returns:
        Dictionary with information about the Excel structure
    """
    # Get the column names
    columns = list(df.columns)

    # Count the number of rows
    row_count = len(df)

    # Count the number of asset types
    if 'asset_type' in columns or 'Asset Type' in columns:
        asset_type_col = 'asset_type' if 'asset_type' in columns else 'Asset Type'
        asset_types = df[asset_type_col].value_counts().to_dict()
    else:
        asset_types = {}

    # Check for missing values
    missing_values = {}
    for col in columns:
        missing_count = df[col].isna().sum()
        if missing_count > 0:
            missing_values[col] = missing_count

    # Return the analysis
    return {
        'columns': columns,
        'row_count': row_count,
        'asset_types': asset_types,
        'missing_values': missing_values
    }

def extract_test_cases(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Extract test cases from the DataFrame.

    Args:
        df: DataFrame containing the benchmark data

    Returns:
        List of test case dictionaries
    """
    # Based on the actual benchmark Excel file structure
    # The columns are: Brand, Asset Type, Asset Name, File, Compliant/Non-Compliant,
    # Expected Issues, Expected Positives, Brand Guidelines Reference, Score, Comments, Feedback, Good to Use

    # Map the columns to our standard format
    column_mapping = {
        'test_id': None,  # We'll generate this
        'asset_type': 'Asset Type',
        'asset_path': 'File',
        'expected_results': 'Expected Issues',  # Primary expected results
        'brand': 'Brand',
        'asset_name': 'Asset Name',
        'compliance_status': 'Compliant/Non-Compliant',
        'expected_positives': 'Expected Positives',
        'brand_guidelines_reference': 'Brand Guidelines Reference',
        'score': 'Score',
        'comments': 'Comments',
        'feedback': 'Feedback',
        'good_to_use': 'Good to Use'
    }

    # Extract test cases
    test_cases = []
    for i, row in df.iterrows():
        test_case = {}

        # Generate a test_id if not present
        test_case['test_id'] = f"{row['Brand'].lower().replace(' ', '_')}_{row['Asset Type'].lower()}_{i+1}"

        # Add mapped columns
        for key, col in column_mapping.items():
            if col and col in df.columns and pd.notna(row[col]):
                test_case[key] = row[col]

        # Special handling for expected results
        # Combine Expected Issues and Expected Positives if both are present
        expected_issues = row.get('Expected Issues', '')
        expected_positives = row.get('Expected Positives', '')

        combined_results = []
        if pd.notna(expected_issues) and expected_issues:
            combined_results.append(f"Expected Issues: {expected_issues}")
        if pd.notna(expected_positives) and expected_positives:
            combined_results.append(f"Expected Positives: {expected_positives}")

        if combined_results:
            test_case['expected_results'] = "\n\n".join(combined_results)
        elif 'expected_results' not in test_case:
            # If no expected results, use compliance status
            compliance = row.get('Compliant/Non-Compliant', '')
            if pd.notna(compliance) and compliance:
                test_case['expected_results'] = f"This asset is {compliance.lower()}"

        # Ensure asset_path is present
        if 'asset_path' not in test_case or pd.isna(test_case['asset_path']):
            # Use a placeholder if File is missing
            test_case['asset_path'] = "HERE"

        # Add the test case to the list
        test_cases.append(test_case)

    logger.info(f"Extracted {len(test_cases)} test cases from the Excel file")
    return test_cases

def validate_assets(test_cases: List[Dict[str, Any]], asset_dir: Optional[str] = None, require_assets: bool = False) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Validate that the assets exist and update the asset paths if needed.

    Args:
        test_cases: List of test case dictionaries
        asset_dir: Base directory for asset paths (optional)
        require_assets: Whether to require assets to exist (default: False)

    Returns:
        Tuple of (valid_test_cases, invalid_test_cases)
    """
    valid_test_cases = []
    invalid_test_cases = []

    for test_case in test_cases:
        # Skip if no asset path
        if 'asset_path' not in test_case:
            if require_assets:
                test_case['error'] = "No asset path specified"
                invalid_test_cases.append(test_case)
            else:
                # Mark as valid even without asset path
                test_case['asset_exists'] = False
                valid_test_cases.append(test_case)
            continue

        # Get the asset path
        asset_path = test_case['asset_path']

        # Skip validation for placeholder paths
        if asset_path == "HERE":
            if require_assets:
                test_case['error'] = "Placeholder asset path"
                invalid_test_cases.append(test_case)
            else:
                # Mark as valid even with placeholder path
                test_case['asset_exists'] = False
                valid_test_cases.append(test_case)
            continue

        # If asset_dir is provided, join it with the asset path
        if asset_dir:
            full_path = os.path.join(asset_dir, asset_path)
        else:
            full_path = asset_path

        # Check if the asset exists
        if os.path.exists(full_path):
            # Update the asset path to the full path
            test_case['asset_path'] = full_path
            test_case['asset_exists'] = True
            valid_test_cases.append(test_case)
        else:
            if require_assets:
                # Add to invalid test cases
                test_case['error'] = f"Asset not found: {full_path}"
                invalid_test_cases.append(test_case)
            else:
                # Mark as valid even if asset doesn't exist
                test_case['asset_exists'] = False
                valid_test_cases.append(test_case)

    logger.info(f"Found {len(valid_test_cases)} valid test cases and {len(invalid_test_cases)} invalid test cases")
    return valid_test_cases, invalid_test_cases

def read_and_analyze_benchmark(file_path: str, asset_dir: Optional[str] = None, mapping_file: Optional[str] = None, require_assets: bool = False) -> Dict[str, Any]:
    """
    Read the benchmark Excel file, analyze its structure, and extract test cases.

    Args:
        file_path: Path to the Excel file
        asset_dir: Base directory for asset paths (optional)
        mapping_file: Path to the asset mapping file (optional)
        require_assets: Whether to require assets to exist (default: False)

    Returns:
        Dictionary with analysis results and test cases
    """
    # Read the Excel file
    df = read_benchmark_excel(file_path)

    # Analyze the structure
    structure = analyze_excel_structure(df)

    # Extract test cases
    test_cases = extract_test_cases(df)

    # Update test cases with file paths if asset_dir or mapping_file is provided
    if asset_dir or mapping_file:
        test_cases = update_test_cases_with_file_paths(test_cases, asset_dir, mapping_file)

    # Validate assets
    valid_test_cases, invalid_test_cases = validate_assets(test_cases, asset_dir, require_assets)

    # Return the results
    return {
        'structure': structure,
        'test_cases': test_cases,
        'valid_test_cases': valid_test_cases,
        'invalid_test_cases': invalid_test_cases
    }

def update_excel_with_results(excel_file: str, benchmark_results: List[Dict[str, Any]]) -> None:
    """
    Update the Excel file with benchmark results.

    Args:
        excel_file: Path to the Excel file
        benchmark_results: List of test case dictionaries with results

    Returns:
        None
    """
    try:
        # Read the Excel file
        df = pd.read_excel(excel_file)
        logger.info(f"Read Excel file for updating: {excel_file}")

        # Create a mapping of test_id to row index
        test_id_to_row = {}
        for i, row in df.iterrows():
            # Generate the same test_id as in extract_test_cases
            test_id = f"{row['Brand'].lower().replace(' ', '_')}_{row['Asset Type'].lower()}_{i+1}"
            test_id_to_row[test_id] = i

        # Update the Excel file with results
        updates_count = 0
        for result in benchmark_results:
            test_id = result.get("test_id")
            if test_id and test_id in test_id_to_row:
                row_idx = test_id_to_row[test_id]

                # Update the Score column if evaluation is available
                if "evaluation" in result and "score" in result["evaluation"]:
                    df.at[row_idx, "Score"] = result["evaluation"]["score"]

                    # Update the Feedback column if available
                    if "feedback" in result["evaluation"]:
                        df.at[row_idx, "Feedback"] = result["evaluation"]["feedback"]

                    # Update the Comments column with missed issues and false positives
                    comments = []
                    if "missed_issues" in result["evaluation"] and result["evaluation"]["missed_issues"]:
                        missed = ", ".join(result["evaluation"]["missed_issues"])
                        comments.append(f"Missed issues: {missed}")

                    if "false_positives" in result["evaluation"] and result["evaluation"]["false_positives"]:
                        false_pos = ", ".join(result["evaluation"]["false_positives"])
                        comments.append(f"False positives: {false_pos}")

                    if comments:
                        df.at[row_idx, "Comments"] = "\n".join(comments)

                    # Update the Good to Use column based on score
                    score = result["evaluation"]["score"]
                    if score >= 90:
                        df.at[row_idx, "Good to Use"] = "Yes"
                    elif score >= 70:
                        df.at[row_idx, "Good to Use"] = "Yes with caution"
                    else:
                        df.at[row_idx, "Good to Use"] = "No"

                    updates_count += 1

        # Save the updated Excel file
        df.to_excel(excel_file, index=False)
        logger.info(f"Updated {updates_count} rows in Excel file: {excel_file}")

    except Exception as e:
        logger.error(f"Failed to update Excel file: {str(e)}")
        raise

if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) < 2:
        print("Usage: python excel_reader.py <excel_file_path> [asset_dir]")
        sys.exit(1)

    excel_file = sys.argv[1]
    asset_dir = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        results = read_and_analyze_benchmark(excel_file, asset_dir)

        print("\n=== Excel Structure ===")
        print(f"Columns: {results['structure']['columns']}")
        print(f"Row count: {results['structure']['row_count']}")
        print(f"Asset types: {results['structure']['asset_types']}")
        print(f"Missing values: {results['structure']['missing_values']}")

        print("\n=== Test Cases ===")
        print(f"Total: {len(results['test_cases'])}")
        print(f"Valid: {len(results['valid_test_cases'])}")
        print(f"Invalid: {len(results['invalid_test_cases'])}")

        if results['valid_test_cases']:
            print("\n=== Sample Valid Test Case ===")
            print(results['valid_test_cases'][0])

        if results['invalid_test_cases']:
            print("\n=== Sample Invalid Test Case ===")
            print(results['invalid_test_cases'][0])

    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
