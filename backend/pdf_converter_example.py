"""
Example showing how to use the optimized pdf_to_image function in your code.
"""

import time
from pdf_to_image import pdf_to_image, get_pdf_page_count


def example_convert_all_pages():
    """
    Example of how to convert all pages in a PDF to images.
    """
    # Path to the PDF file
    pdf_path = "app/assets/coca_cola_brand_guidelines.pdf"

    # Get the total number of pages
    page_count = get_pdf_page_count(pdf_path)
    print(f"PDF has {page_count} pages")

    # Define a progress callback function
    def progress_callback(completed, total):
        percent = (completed / total) * 100
        print(f"Progress: {completed}/{total} pages ({percent:.1f}%)")

    # Start timing
    start_time = time.time()

    # Convert all PDF pages to images with optimized settings
    results = pdf_to_image(
        pdf_path=pdf_path,
        # pages="all" is the default, so we don't need to specify it
        dpi=100,  # Lower DPI for faster conversion
        include_base64=False,  # Skip base64 encoding for speed
        parallel=True,  # Use parallel processing
        progress_callback=progress_callback,  # Show progress
        verbose=True,  # Print status messages
    )

    # Calculate elapsed time
    elapsed_time = time.time() - start_time

    # Process the results
    successful_conversions = [r for r in results if r["success"]]
    print(
        f"\nConverted {len(successful_conversions)} pages in {elapsed_time:.2f} seconds"
    )
    print(f"Average time per page: {elapsed_time / len(results):.2f} seconds")

    # Display information about each converted image
    for result in successful_conversions:
        page_num = result["page"] + 1  # Convert 0-based index to 1-based page number
        print(f"\nPage {page_num}:")
        print(f"  Filename: {result['filename']}")
        print(f"  Dimensions: {result['width']}x{result['height']} pixels")
        print(f"  Format: {result['format']}")

    return results


def example_high_quality_conversion():
    """
    Example of how to convert a single page with high quality.
    """
    # Path to the PDF file
    pdf_path = "app/assets/coca_cola_brand_guidelines.pdf"

    # Start timing
    start_time = time.time()

    # Convert only the first page with high quality
    result = pdf_to_image(
        pdf_path=pdf_path,
        pages=0,  # Just the first page (0-based index)
        dpi=300,  # Higher DPI for better quality
        include_base64=True,  # Include base64 encoding
        verbose=True,  # Print status messages
    )

    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    print(f"\nConverted page in {elapsed_time:.2f} seconds")

    # Check if conversion was successful
    if result["success"]:
        # Access the image information
        filename = result["filename"]
        image_path = result["path"]
        width = result["width"]
        height = result["height"]
        image_format = result["format"]
        base64_data = result["base64"]

        print(f"Converted to {image_format} image: {filename}")
        print(f"Image dimensions: {width}x{height} pixels")
        print(f"Base64 (truncated): {base64_data[:20]}...")

        return result
    else:
        print(f"Error: {result['error']}")
        return None


def example_batch_conversion():
    """
    Example of how to convert multiple specific pages efficiently.
    """
    # Path to the PDF file
    pdf_path = "app/assets/coca_cola_brand_guidelines.pdf"

    # Start timing
    start_time = time.time()

    # Convert specific pages
    results = pdf_to_image(
        pdf_path=pdf_path,
        pages=[0, 2, 4, 6, 8],  # Convert specific pages
        dpi=150,  # Medium quality
        include_base64=False,  # Skip base64 encoding for speed
        parallel=True,  # Use parallel processing
        verbose=True,  # Print status messages
    )

    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    print(f"\nConverted {len(results)} pages in {elapsed_time:.2f} seconds")

    # Process the results
    for result in results:
        if result["success"]:
            page_num = (
                result["page"] + 1
            )  # Convert 0-based index to 1-based page number
            print(
                f"Page {page_num}: {result['filename']} ({result['width']}x{result['height']})"
            )
        else:
            print(f"Error converting page {result['page'] + 1}: {result['error']}")

    return results


if __name__ == "__main__":
    print("=== Example: Converting All Pages ===")
    example_convert_all_pages()

    # Uncomment to run other examples
    # print("\n=== Example: High Quality Conversion ===")
    # example_high_quality_conversion()

    # print("\n=== Example: Batch Conversion of Specific Pages ===")
    # example_batch_conversion()
