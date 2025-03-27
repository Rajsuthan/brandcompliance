"""
PDF to Image Converter

A simple module to convert PDF pages to images and get basic information about them.
"""

import os
import subprocess
import base64
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List, Optional, Union, Callable
from PIL import Image


def get_pdf_page_count(pdf_path: str) -> int:
    """
    Get the number of pages in a PDF file.

    Args:
        pdf_path (str): Path to the PDF file

    Returns:
        int: Number of pages in the PDF
    """
    try:
        # Try using pdfinfo to get page count
        result = subprocess.run(
            ["pdfinfo", pdf_path],
            capture_output=True,
            text=True,
            check=True,
        )

        # Parse the output to find the page count
        for line in result.stdout.split("\n"):
            if line.startswith("Pages:"):
                return int(line.split(":")[1].strip())

        raise ValueError("Could not find page count in pdfinfo output")

    except (subprocess.SubprocessError, ValueError, FileNotFoundError):
        # Try using PIL as fallback
        try:
            with Image.open(pdf_path) as img:
                if hasattr(img, "n_frames"):
                    return img.n_frames
                return 1
        except Exception:
            return 0


def pdf_to_image(
    pdf_path: str,
    pages: Union[int, List[int], str] = "all",
    output_dir: Optional[str] = None,
    output_filename_pattern: Optional[str] = None,
    dpi: int = 100,  # Lower default DPI for faster conversion
    include_base64: bool = False,  # Don't include base64 by default for speed
    max_pages: Optional[int] = None,  # Limit number of pages to convert
    parallel: bool = True,  # Use parallel processing by default
    progress_callback: Optional[Callable[[int, int], None]] = None,  # Progress callback
    verbose: bool = False,
) -> Union[Dict, List[Dict]]:
    """
    Convert PDF pages to images and return basic information about them.

    Args:
        pdf_path (str): Path to the PDF file
        pages (int, list, or str):
            - If int: Single page number to convert (0-based index)
            - If list: List of page numbers to convert (0-based indices)
            - If "all": Convert all pages (default)
        output_dir (str, optional): Directory to save the output images
            If None, save in the same directory as the PDF
        output_filename_pattern (str, optional): Pattern for output filenames
            Use {pdf_name} for the PDF filename without extension
            Use {page_num} for the page number (1-based)
            Use {page_idx} for the page index (0-based)
            Default: "{pdf_name}_page_{page_num}.png"
        dpi (int): DPI for the output images (default: 300)
        include_base64 (bool): Whether to include base64 encoding of the images (default: True)
        verbose (bool): Whether to print status messages (default: False)

    Returns:
        Union[Dict, List[Dict]]:
            - If converting a single page: Dictionary with image information
            - If converting multiple pages: List of dictionaries with image information

            Each dictionary contains:
            - "filename": Name of the image file
            - "path": Full path to the image file
            - "page": Page number (0-based index)
            - "width": Width of the image in pixels
            - "height": Height of the image in pixels
            - "format": Format of the image (e.g., "PNG", "JPEG")
            - "base64": Base64 encoding of the image (if include_base64 is True)
            - "success": Whether the conversion was successful
            - "error": Error message if conversion failed
    """
    # Validate PDF path
    if not os.path.exists(pdf_path):
        error_result = {"success": False, "error": f"PDF file not found: {pdf_path}"}
        return error_result

    # Determine output directory
    if output_dir is None:
        output_dir = os.path.dirname(pdf_path)
    os.makedirs(output_dir, exist_ok=True)

    # Get PDF filename without extension
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]

    # Set default filename pattern if not provided
    if output_filename_pattern is None:
        output_filename_pattern = "{pdf_name}_page_{page_num}.png"

    # Determine which pages to convert
    page_numbers = []
    if pages == "all":
        # Convert all pages
        page_count = get_pdf_page_count(pdf_path)
        if page_count == 0:
            return {"success": False, "error": "Could not determine page count"}
        page_numbers = list(range(page_count))
    elif isinstance(pages, int):
        # Convert a single page
        page_numbers = [pages]
    elif isinstance(pages, list):
        # Convert specific pages
        page_numbers = pages
    else:
        return {"success": False, "error": "Invalid 'pages' parameter"}

    # Apply max_pages limit if specified
    if max_pages is not None and len(page_numbers) > max_pages:
        page_numbers = page_numbers[:max_pages]

    # Prepare conversion parameters
    conversion_params = []
    for page_idx in page_numbers:
        # Create output filename
        output_filename = output_filename_pattern.format(
            pdf_name=pdf_name, page_num=page_idx + 1, page_idx=page_idx, ext="png"
        )
        output_path = os.path.join(output_dir, output_filename)

        # Add to conversion parameters
        conversion_params.append((pdf_path, page_idx, output_path, dpi, verbose))

    # Convert pages
    results = []

    # Function to process conversion results
    def process_result(result_tuple):
        success, page_idx, output_path, error = result_tuple
        if success:
            result = _get_image_result(output_path, include_base64)
            result["page"] = page_idx
            return result
        else:
            return {
                "success": False,
                "page": page_idx,
                "error": error,
            }

    # Use parallel processing if enabled and more than one page
    if parallel and len(page_numbers) > 1:
        # Determine number of workers (use half of available cores to avoid overloading)
        num_workers = max(1, multiprocessing.cpu_count() // 2)

        # Convert pages in parallel
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            # Submit all conversion tasks
            future_to_idx = {
                executor.submit(_convert_page, *params): i
                for i, params in enumerate(conversion_params)
            }

            # Process results as they complete
            completed = 0
            total = len(future_to_idx)
            for future in future_to_idx:
                result = process_result(future.result())
                results.append(result)

                # Update progress if callback provided
                completed += 1
                if progress_callback:
                    progress_callback(completed, total)
    else:
        # Convert pages sequentially
        total = len(conversion_params)
        for i, params in enumerate(conversion_params):
            result = process_result(_convert_page(*params))
            results.append(result)

            # Update progress if callback provided
            if progress_callback:
                progress_callback(i + 1, total)

    # Return a single result if only one page was converted
    if len(results) == 1 and isinstance(pages, int):
        return results[0]

    return results


def _convert_page(pdf_path, page_idx, output_path, dpi, verbose):
    """
    Convert a single PDF page to an image.

    Returns:
        tuple: (success, page_idx, output_path, error_message)
    """
    try:
        # Try using pdftoppm (from poppler-utils) if available
        if _convert_with_pdftoppm(pdf_path, page_idx, output_path, dpi, verbose):
            return (True, page_idx, output_path, None)

        # If pdftoppm fails, try using PIL
        if _convert_with_pil(pdf_path, page_idx, output_path, verbose):
            return (True, page_idx, output_path, None)

        # If both methods fail
        return (
            False,
            page_idx,
            output_path,
            "Failed to convert PDF to image using all available methods",
        )

    except Exception as e:
        return (False, page_idx, output_path, str(e))


def _convert_with_pdftoppm(
    pdf_path: str, page_num: int, output_path: str, dpi: int, verbose: bool
) -> bool:
    """
    Convert PDF to image using pdftoppm.

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create a temporary output file path without extension
        temp_output_prefix = os.path.splitext(output_path)[0]

        # pdftoppm uses 1-based page numbers
        page_num_1_based = page_num + 1

        # Run pdftoppm command with optimized settings
        subprocess.run(
            [
                "pdftoppm",
                "-f",
                str(page_num_1_based),
                "-l",
                str(page_num_1_based),
                "-png",
                "-r",
                str(dpi),
                # Add optimization flags
                "-aa",
                "no",  # Disable anti-aliasing for speed
                "-aaVector",
                "no",  # Disable vector anti-aliasing
                pdf_path,
                temp_output_prefix,
            ],
            check=True,
            capture_output=True,  # Always capture output for speed
        )

        # Find the generated file and rename it
        generated_files = [
            f
            for f in os.listdir(os.path.dirname(temp_output_prefix))
            if f.startswith(os.path.basename(temp_output_prefix)) and f.endswith(".png")
        ]

        if not generated_files:
            return False

        generated_file_path = os.path.join(
            os.path.dirname(temp_output_prefix), generated_files[0]
        )

        # Rename if needed
        if generated_file_path != output_path:
            os.rename(generated_file_path, output_path)

        if verbose:
            print(f"Successfully converted page {page_num+1} to image: {output_path}")

        return True

    except Exception as e:
        if verbose:
            print(f"pdftoppm conversion failed: {e}")
        return False


def _convert_with_pil(
    pdf_path: str, page_num: int, output_path: str, verbose: bool
) -> bool:
    """
    Convert PDF to image using PIL.

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Open the PDF file as an image
        img = Image.open(pdf_path)

        # If the PDF has multiple pages, seek to the desired page
        if hasattr(img, "n_frames") and img.n_frames > 1:
            img.seek(page_num)

        # Convert to RGB mode if necessary
        if img.mode != "RGB":
            img = img.convert("RGB")

        # Save the image with optimization
        img.save(output_path, optimize=True)

        if verbose:
            print(f"Successfully converted page {page_num+1} to image: {output_path}")

        return True

    except Exception as e:
        if verbose:
            print(f"PIL conversion failed: {e}")
        return False


def _get_image_result(image_path: str, include_base64: bool) -> Dict:
    """
    Get information about the converted image.

    Returns:
        Dict: Image information
    """
    try:
        # Check if file exists
        if not os.path.exists(image_path):
            return {"success": False, "error": f"Image file not found: {image_path}"}

        # Get image dimensions and format using PIL
        with Image.open(image_path) as img:
            width, height = img.size
            format = img.format

        # Create result dictionary
        result = {
            "success": True,
            "filename": os.path.basename(image_path),
            "path": image_path,
            "width": width,
            "height": height,
            "format": format,
        }

        # Add base64 encoding if requested
        if include_base64:
            with open(image_path, "rb") as img_file:
                base64_data = base64.b64encode(img_file.read()).decode("utf-8")
                result["base64"] = base64_data

        return result

    except Exception as e:
        return {"success": False, "error": str(e)}
