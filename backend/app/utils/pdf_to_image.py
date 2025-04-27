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
import io
import time

# Import pypdfium2 (pure pip, no system dependencies)
try:
    import pypdfium2
    PDFIUM_AVAILABLE = True
except ImportError:
    PDFIUM_AVAILABLE = False
    print("Warning: pypdfium2 not available. PDF processing will be limited.")

# Import PyMuPDF (fitz) as a fallback
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    print("Warning: PyMuPDF not available. Using fallback methods for PDF processing.")

# Import pdf2image as a last-resort fallback
try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    print("Warning: pdf2image not available. Falling back to other methods for PDF processing.")


def get_pdf_page_count(pdf_path: str) -> int:
    """
    Get the number of pages in a PDF file.

    Args:
        pdf_path (str): Path to the PDF file

    Returns:
        int: Number of pages in the PDF
    """
    # Try pypdfium2 first (pure pip, no system dependencies)
    if PDFIUM_AVAILABLE:
        try:
            start_time = time.time()
            pdf = pypdfium2.PdfDocument(pdf_path)
            page_count = len(pdf)
            pdf.close()
            print(f"pypdfium2: Got page count in {time.time() - start_time:.3f}s")
            return page_count
        except Exception as e:
            print(f"pypdfium2 failed to get page count: {e}")
            # Fall back to other methods

    # Try PyMuPDF next
    if PYMUPDF_AVAILABLE:
        try:
            start_time = time.time()
            pdf = fitz.open(pdf_path)
            page_count = len(pdf)
            pdf.close()
            print(f"PyMuPDF: Got page count in {time.time() - start_time:.3f}s")
            return page_count
        except Exception as e:
            print(f"PyMuPDF failed to get page count: {e}")

    # Try pdf2image as a last resort
    if PDF2IMAGE_AVAILABLE:
        try:
            start_time = time.time()
            images = convert_from_path(pdf_path, dpi=72, first_page=1, last_page=1)
            if images:
                page_count = 1
                while True:
                    try:
                        temp = convert_from_path(pdf_path, dpi=72, first_page=page_count+1, last_page=page_count+1)
                        if not temp:
                            break
                        page_count += 1
                    except Exception:
                        break
                print(f"pdf2image: Got page count in {time.time() - start_time:.3f}s")
                return page_count
        except Exception as e:
            print(f"pdf2image failed to get page count: {e}")

    # Try PIL as a fallback
    try:
        start_time = time.time()
        with Image.open(pdf_path) as img:
            if hasattr(img, "n_frames"):
                print(f"PIL: Got page count in {time.time() - start_time:.3f}s")
                return img.n_frames
            return 1
    except Exception:
        return 0


def pdf_to_image_fitz(
    pdf_path: str,
    pages: Union[int, List[int], str] = "all",
    dpi: int = 100,
    include_base64: bool = False,
    max_workers: Optional[int] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    verbose: bool = False,
) -> List[Dict]:
    """
    Convert PDF pages to images using pdf2image (Poppler-based PDF converter) while keeping function name compatibility.
    Falls back to PyMuPDF or other methods if pdf2image is not available.
    
    Args:
        pdf_path (str): Path to the PDF file
        pages (int, list, or str): Pages to convert (0-based indices)
        dpi (int): DPI for the output images (default: 100)
        include_base64 (bool): Whether to include base64 encoding of the images
        max_workers (int): Maximum number of worker processes (default: CPU count)
        progress_callback (callable): Function to call with progress updates
        verbose (bool): Whether to print status messages
        
    Returns:
        List[Dict]: List of dictionaries with image information
    """
    if PDF2IMAGE_AVAILABLE:
        # Use pdf2image as the primary method
        # Determine which pages to process
        if pages == "all":
            # For all pages, we need to get the page count first
            total_pages = get_pdf_page_count(pdf_path)
            page_indices = list(range(total_pages))
        elif isinstance(pages, int):
            page_indices = [pages]
        else:
            page_indices = list(pages)
        
        results = []
        total_to_process = len(page_indices)
        
        if verbose:
            print(f"Processing {total_to_process} pages with pdf2image")
        
        # Process each page
        for i, page_idx in enumerate(page_indices):
            try:
                # Convert using pdf2image (note: pdf2image uses 1-based indexing)
                images = convert_from_path(
                    pdf_path,
                    dpi=dpi,
                    first_page=page_idx+1,
                    last_page=page_idx+1
                )
                
                if images and len(images) > 0:
                    # Save to a temporary buffer
                    img_buffer = io.BytesIO()
                    img_format = "PNG"
                    images[0].save(img_buffer, format=img_format)
                    img_buffer.seek(0)
                    
                    # Create result dictionary
                    result = {
                        "page": page_idx,
                        "width": images[0].width,
                        "height": images[0].height,
                        "format": img_format,
                        "success": True,
                        "error": None,
                        "image": images[0]  # Store the PIL image
                    }
                    
                    # Add base64 encoding if requested
                    if include_base64:
                        base64_data = base64.b64encode(img_buffer.getvalue()).decode("utf-8")
                        result["base64"] = f"data:image/{img_format.lower()};base64,{base64_data}"
                    
                    results.append(result)
                
                # Report progress
                if progress_callback:
                    progress_callback(i + 1, total_to_process)
                elif verbose and (i + 1) % 10 == 0:
                    print(f"Processed {i + 1}/{total_to_process} pages")
            except Exception as e:
                if verbose:
                    print(f"Error processing page {page_idx} with pdf2image: {e}")
        
        if results:
            # Sort results by page number
            results.sort(key=lambda x: x["page"])
            return results
        elif verbose:
            print("pdf2image processing failed. Falling back to standard method.")
            
    # If pdf2image failed or isn't available, fall back to the standard method
    if verbose:
        print("Falling back to standard method.")
        
    return pdf_to_image(
        pdf_path=pdf_path,
        pages=pages,
        dpi=dpi,
        include_base64=include_base64,
        verbose=verbose,
    )


def _convert_page_fitz(pdf_path, page_idx, dpi, include_base64, verbose=False):
    """Convert a single page using pdf2image (keeping original function name for compatibility)"""
    try:
        if verbose:
            print(f"Converting page {page_idx} with pdf2image...")
            
        # Convert using pdf2image (note: pdf2image uses 1-based indexing)
        images = convert_from_path(
            pdf_path,
            dpi=dpi,
            first_page=page_idx+1,
            last_page=page_idx+1
        )
        
        if not images or len(images) == 0:
            raise ValueError("No images returned from pdf2image")
            
        img = images[0]
        width, height = img.width, img.height
        
        # Create a buffer for the image
        img_buffer = io.BytesIO()
        img_format = "PNG"
        img.save(img_buffer, format=img_format)
        img_buffer.seek(0)
        
        img_data = {
            "page": page_idx,
            "width": width,
            "height": height,
            "format": img_format,
            "success": True,
            "error": None,
            "image": img  # Include the PIL image object
        }
        
        # Add base64 encoded image if requested
        if include_base64:
            base64_data = base64.b64encode(img_buffer.getvalue()).decode("utf-8")
            img_data["base64"] = f"data:image/{img_format.lower()};base64,{base64_data}"
        
        return img_data
    
    except Exception as e:
        if verbose:
            print(f"pdf2image failed: {e}")
            
        # Fallback methods would be here
        error_data = {
            "page": page_idx,
            "width": 0,
            "height": 0,
            "format": None,
            "success": False,
            "error": str(e)
        }
        return error_data


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


def _convert_page(pdf_path, page_idx, output_path, dpi, verbose=False):
    """
    Convert a single PDF page to an image.

    Returns:
        tuple: (success, page_idx, output_path, error_message)
    """
    success = False
    error_message = ""

    # Try pypdfium2 first (pure pip, no system dependencies)
    if PDFIUM_AVAILABLE:
        if verbose:
            print(f"Trying pypdfium2 for page {page_idx}...")
        try:
            pdf = pypdfium2.PdfDocument(pdf_path)
            page = pdf.get_page(page_idx)
            pil_image = page.render(scale=dpi/72).to_pil()
            pil_image.save(output_path)
            page.close()
            pdf.close()
            if verbose:
                print(f"pypdfium2 succeeded for page {page_idx}")
            return True, page_idx, output_path, ""
        except Exception as e:
            error_message = f"pypdfium2 error: {str(e)}"
            if verbose:
                print(error_message)

    # Try pdf2image next if available
    if PDF2IMAGE_AVAILABLE:
        if verbose:
            print(f"Trying pdf2image for page {page_idx}...")
        try:
            images = convert_from_path(
                pdf_path,
                dpi=dpi,
                first_page=page_idx+1,
                last_page=page_idx+1
            )
            if images and len(images) > 0:
                images[0].save(output_path)
                if verbose:
                    print(f"pdf2image succeeded for page {page_idx}")
                return True, page_idx, output_path, ""
            else:
                error_message = "pdf2image returned no images"
                if verbose:
                    print(error_message)
        except Exception as e:
            error_message = f"pdf2image error: {str(e)}"
            if verbose:
                print(error_message)

    # Try pdftoppm next (system dependency)
    if verbose:
        print(f"Trying pdftoppm for page {page_idx}...")

    try:
        success = _convert_with_pdftoppm(pdf_path, page_idx + 1, output_path, dpi, verbose)
        if success:
            return True, page_idx, output_path, ""
    except Exception as e:
        error_message += f" | pdftoppm error: {str(e)}"
        if verbose:
            print(error_message)

    # If pdftoppm fails, try PIL as fallback
    if verbose:
        print(f"Trying PIL for page {page_idx}...")

    try:
        success = _convert_with_pil(pdf_path, page_idx, output_path, verbose)
        if success:
            return True, page_idx, output_path, ""
        else:
            error_message += " | PIL conversion failed"
    except Exception as e:
        error_message += f" | PIL error: {str(e)}"
        if verbose:
            print(f"PIL failed: {str(e)}")

    return False, page_idx, output_path, error_message


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
