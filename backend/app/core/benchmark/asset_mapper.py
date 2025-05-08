"""
Asset mapper module for the benchmark system.

This module provides functions to map asset names from the Excel file to local file paths.
"""

import os
import re
import json
from typing import Dict, List, Optional, Tuple, Any
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_asset_id(asset_name: str) -> str:
    """
    Generate a consistent ID from an asset name.

    Args:
        asset_name: The asset name from the Excel file

    Returns:
        A consistent ID for the asset
    """
    # Convert to lowercase
    asset_id = asset_name.lower()

    # Replace spaces and special characters
    asset_id = asset_id.replace(' ', '_').replace('-', '_')

    # Remove any other special characters
    asset_id = ''.join(c for c in asset_id if c.isalnum() or c == '_')

    return asset_id

def scan_asset_folder(folder_path: str) -> Dict[str, str]:
    """
    Scan the asset folder and create a mapping of asset IDs to file paths.

    Args:
        folder_path: Path to the folder containing the assets

    Returns:
        Dictionary mapping asset IDs to file paths
    """
    asset_mapping = {}

    # Check if the folder exists
    if not os.path.exists(folder_path):
        logger.error(f"Asset folder not found: {folder_path}")
        return asset_mapping

    # Scan the folder for files
    for filename in os.listdir(folder_path):
        # Skip hidden files and directories
        if filename.startswith('.') or os.path.isdir(os.path.join(folder_path, filename)):
            continue

        # Get the file path
        file_path = os.path.join(folder_path, filename)

        # Generate an asset ID from the filename (without extension)
        base_name = os.path.splitext(filename)[0]
        asset_id = generate_asset_id(base_name)

        # Add to the mapping
        asset_mapping[asset_id] = file_path

        # Also add a mapping with the original filename (for exact matches)
        asset_mapping[base_name] = file_path

    logger.info(f"Found {len(asset_mapping)} assets in {folder_path}")
    return asset_mapping

def create_excel_to_file_mapping(excel_asset_names: List[str], asset_folder: str) -> Dict[str, str]:
    """
    Create a mapping from Excel asset names to local file paths.

    Args:
        excel_asset_names: List of asset names from the Excel file
        asset_folder: Path to the folder containing the assets

    Returns:
        Dictionary mapping Excel asset names to local file paths
    """
    # Scan the asset folder
    asset_mapping = scan_asset_folder(asset_folder)

    # Create a mapping from Excel asset names to file paths
    excel_to_file_mapping = {}

    for asset_name in excel_asset_names:
        if not asset_name or asset_name == "HERE":
            continue

        # Try exact match first
        if asset_name in asset_mapping:
            excel_to_file_mapping[asset_name] = asset_mapping[asset_name]
            continue

        # Try with ID
        asset_id = generate_asset_id(asset_name)
        if asset_id in asset_mapping:
            excel_to_file_mapping[asset_name] = asset_mapping[asset_id]
            continue

        # Try fuzzy matching
        best_match = find_best_match(asset_name, list(asset_mapping.keys()))
        if best_match:
            excel_to_file_mapping[asset_name] = asset_mapping[best_match]
            logger.info(f"Fuzzy matched '{asset_name}' to '{best_match}'")
            continue

        logger.warning(f"No match found for asset: {asset_name}")

    logger.info(f"Mapped {len(excel_to_file_mapping)} out of {len(excel_asset_names)} Excel asset names")
    return excel_to_file_mapping

def find_best_match(asset_name: str, candidates: List[str]) -> Optional[str]:
    """
    Find the best match for an asset name among the candidates.

    Args:
        asset_name: The asset name to match
        candidates: List of candidate asset names

    Returns:
        The best matching candidate, or None if no good match is found
    """
    # Convert to lowercase for comparison
    asset_name_lower = asset_name.lower()

    # Try exact match first (case insensitive)
    for candidate in candidates:
        if candidate.lower() == asset_name_lower:
            return candidate

    # Try to find a candidate that contains the asset name exactly
    for candidate in candidates:
        if asset_name_lower in candidate.lower():
            # Only return if it's a very close match (e.g., just missing an extension)
            if len(candidate) - len(asset_name) < 10:
                return candidate

    # Try to find a candidate that the asset name contains exactly
    for candidate in candidates:
        if candidate.lower() in asset_name_lower:
            # Only return if it's a very close match
            if len(asset_name) - len(candidate) < 10:
                return candidate

    # For exact asset names (without version numbers), try to find a match
    # This is for cases like "Burger King_Compliant_BrandVoice-1" vs "Burger King_Compliant_BrandVoice-3"
    base_name = re.sub(r'[-_\s]\d+$', '', asset_name_lower)  # Remove trailing numbers
    base_name = re.sub(r'[-_\s]v\d+$', '', base_name)  # Remove trailing version numbers (v1, v2, etc.)

    for candidate in candidates:
        candidate_lower = candidate.lower()
        candidate_base = re.sub(r'[-_\s]\d+$', '', candidate_lower)
        candidate_base = re.sub(r'[-_\s]v\d+$', '', candidate_base)

        if base_name == candidate_base:
            return candidate

    # No good match found - we're being strict about matching
    return None

def update_test_cases_with_file_paths(test_cases: List[Dict[str, Any]], asset_folder: str = None, mapping_file: str = None) -> List[Dict[str, Any]]:
    """
    Update test cases with file paths based on asset names.

    Args:
        test_cases: List of test case dictionaries
        asset_folder: Path to the folder containing the assets (optional)
        mapping_file: Path to the asset mapping file (optional)

    Returns:
        Updated list of test case dictionaries
    """
    # If mapping file is provided, use it
    if mapping_file and os.path.exists(mapping_file):
        asset_mapping = load_asset_mapping(mapping_file)
        logger.info(f"Loaded asset mapping from {mapping_file} with {len(asset_mapping)} entries")
    # Otherwise, create a new mapping from the asset folder
    elif asset_folder:
        # Extract asset names from test cases
        asset_names = []
        for test_case in test_cases:
            asset_name = test_case.get('asset_name')
            if asset_name:
                asset_names.append(asset_name)

        # Create a mapping from asset names to file paths
        asset_mapping = create_excel_to_file_mapping(asset_names, asset_folder)
    else:
        logger.warning("No asset folder or mapping file provided")
        asset_mapping = {}

    # Update test cases with file paths
    for test_case in test_cases:
        asset_name = test_case.get('asset_name')
        if asset_name and asset_name in asset_mapping:
            test_case['asset_path'] = asset_mapping[asset_name]
            test_case['asset_exists'] = True
        else:
            test_case['asset_exists'] = False

    return test_cases

def save_asset_mapping(mapping: Dict[str, str], output_file: str) -> None:
    """
    Save the asset mapping to a JSON file.

    Args:
        mapping: Dictionary mapping asset names to file paths
        output_file: Path to the output JSON file
    """
    with open(output_file, 'w') as f:
        json.dump(mapping, f, indent=2)

    logger.info(f"Asset mapping saved to {output_file}")

def load_asset_mapping(input_file: str) -> Dict[str, str]:
    """
    Load the asset mapping from a JSON file.

    Args:
        input_file: Path to the input JSON file

    Returns:
        Dictionary mapping asset names to file paths
    """
    if not os.path.exists(input_file):
        logger.warning(f"Asset mapping file not found: {input_file}")
        return {}

    with open(input_file, 'r') as f:
        mapping = json.load(f)

    logger.info(f"Asset mapping loaded from {input_file}")
    return mapping

if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) < 2:
        print("Usage: python asset_mapper.py <asset_folder> [output_file]")
        sys.exit(1)

    asset_folder = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "asset_mapping.json"

    # Scan the asset folder
    asset_mapping = scan_asset_folder(asset_folder)

    # Save the mapping to a JSON file
    save_asset_mapping(asset_mapping, output_file)

    print(f"Asset mapping saved to {output_file}")
