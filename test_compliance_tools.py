import asyncio
import base64
import json
import os
from PIL import Image
from io import BytesIO

# Import the functions to test
from backend.app.core.agent.tools import (
    check_element_placement,
    check_layout_consistency,
)


async def test_element_placement():
    """Test the check_element_placement function with a test image."""
    print("\n=== Testing Element Placement ===")

    # Load a test image
    image_path = "test_images/Coca-Cola-Drinkable_Keerthi-1024x683.jpg"

    # Convert image to base64
    with open(image_path, "rb") as image_file:
        image_data = image_file.read()
        image_base64 = base64.b64encode(image_data).decode("utf-8")

    # Get image dimensions
    with Image.open(image_path) as img:
        width, height = img.size
        print(f"Image dimensions: {width}x{height}")

    # Create test data
    # For Coca-Cola image, let's assume the bottle is the primary element
    # and the text/logo are secondary elements
    test_data = {
        "image_base64": image_base64,
        "primary_element_coordinates": "400,150,600,550",  # Approximate bottle position
        "secondary_elements_coordinates": "100,100,350,200;650,100,900,200",  # Text/logo positions
        "safe_zone_percentage": "10,10,10,10",
        "min_spacing": 20,
        "output_directory": "compliance_results",
        "brand_name": "coca-cola",
        "task_detail": "Testing element placement",
    }

    # Call the function
    result = await check_element_placement(test_data)

    # Parse and display results
    result_json = json.loads(result)
    if "error" in result_json:
        print(f"Error: {result_json['error']}")
    else:
        print("Element Placement Analysis:")
        print(
            f"Primary element in safe zone: {result_json['placement_results']['primary_element']['in_safe_zone']}"
        )
        print(
            f"All elements in safe zone: {result_json['compliance_summary']['all_elements_in_safe_zone']}"
        )
        print(
            f"All spacing compliant: {result_json['compliance_summary']['all_spacing_compliant']}"
        )
        print(
            f"Overall compliant: {result_json['compliance_summary']['overall_compliant']}"
        )

        # Check if visualization was saved
        if os.path.exists("compliance_results"):
            files = os.listdir("compliance_results")
            element_placement_files = [f for f in files if "element_placement" in f]
            if element_placement_files:
                print(
                    f"Visualization saved to: compliance_results/{element_placement_files[-1]}"
                )


async def test_layout_consistency():
    """Test the check_layout_consistency function with a test image."""
    print("\n=== Testing Layout Consistency ===")

    # Load a test image
    image_path = (
        "test_images/its-a-steal-not-a-crime-burger-king-advert-from-2009-2M7N9J4.jpg"
    )

    # Convert image to base64
    with open(image_path, "rb") as image_file:
        image_data = image_file.read()
        image_base64 = base64.b64encode(image_data).decode("utf-8")

    # Get image dimensions
    with Image.open(image_path) as img:
        width, height = img.size
        print(f"Image dimensions: {width}x{height}")

    # Create test data
    # For Burger King ad, let's define some elements to check against a grid
    test_data = {
        "image_base64": image_base64,
        "elements_coordinates": "100,100,300,200;400,100,600,200;700,100,900,200;100,300,900,500",
        "grid_settings": "3,3,20,50",  # 3x3 grid with 20px gutters and 50px margins
        "output_directory": "compliance_results",
        "brand_name": "burger-king",
        "task_detail": "Testing layout consistency",
    }

    # Call the function
    result = await check_layout_consistency(test_data)

    # Parse and display results
    result_json = json.loads(result)
    if "error" in result_json:
        print(f"Error: {result_json['error']}")
    else:
        print("Layout Consistency Analysis:")
        print(
            f"Grid info: {result_json['grid_info']['columns']}x{result_json['grid_info']['rows']} grid"
        )
        print(
            f"Aligned elements: {result_json['layout_consistency']['aligned_elements_count']}/{result_json['layout_consistency']['total_elements']}"
        )
        print(
            f"Alignment percentage: {result_json['layout_consistency']['alignment_percentage']}%"
        )
        print(
            f"All elements grid aligned: {result_json['layout_consistency']['all_elements_grid_aligned']}"
        )

        # Check if visualization was saved
        if os.path.exists("compliance_results"):
            files = os.listdir("compliance_results")
            layout_consistency_files = [f for f in files if "layout_consistency" in f]
            if layout_consistency_files:
                print(
                    f"Visualization saved to: compliance_results/{layout_consistency_files[-1]}"
                )


async def main():
    """Run all tests."""
    # Create output directory if it doesn't exist
    os.makedirs("compliance_results", exist_ok=True)

    # Test element placement
    await test_element_placement()

    # Test layout consistency
    await test_layout_consistency()

    print(
        "\nTests completed. Check the 'compliance_results' directory for visualizations."
    )


if __name__ == "__main__":
    asyncio.run(main())
