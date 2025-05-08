"""
Benchmark runner module for the benchmark system.

This module provides functions to run the benchmark on test cases from the Excel file.
"""

import os
import time
import base64
import asyncio
import json
from typing import List, Dict, Optional, Any, Tuple
import logging

# Import the OpenRouterAgent
from app.core.openrouter_agent.native_agent import OpenRouterAgent

# Import video processing functions
from app.core.video_agent.gemini_llm import extract_frames

# Import the evaluators
from app.core.benchmark.evaluator import evaluate_benchmark_results
from app.core.benchmark.gemini_evaluator import evaluate_benchmark_results as evaluate_benchmark_results_gemini

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def process_image(image_path: str) -> str:
    """
    Process an image file and convert it to base64.

    Args:
        image_path: Path to the image file

    Returns:
        Base64-encoded image data
    """
    try:
        with open(image_path, "rb") as f:
            image_data = f.read()

        # Convert to base64
        image_base64 = base64.b64encode(image_data).decode("utf-8")
        logger.info(f"Processed image: {image_path}")
        return image_base64
    except Exception as e:
        logger.error(f"Error processing image {image_path}: {str(e)}")
        raise

async def process_video(video_path: str, initial_interval: float = 1.0, similarity_threshold: float = 0.8) -> List[Dict[str, Any]]:
    """
    Process a video file and extract frames as base64.

    Args:
        video_path: Path to the video file
        initial_interval: Initial interval between frames in seconds
        similarity_threshold: Threshold for frame similarity

    Returns:
        List of frame dictionaries with image_data
    """
    try:
        # Extract frames from the video
        frames = await extract_frames(
            video_path,
            initial_interval=initial_interval,
            similarity_threshold=similarity_threshold
        )

        # The frames should already have both 'base64' and 'image_data' keys
        # from our updated extract_frames function, but let's verify and ensure consistency
        processed_frames = []
        for i, frame in enumerate(frames):
            # Check if the frame has base64 data (should always be present)
            if 'base64' in frame:
                # Create a copy of the frame to avoid modifying the original
                processed_frame = frame.copy()

                # Ensure both keys are present
                if 'image_data' not in processed_frame:
                    processed_frame['image_data'] = processed_frame['base64']

                # Ensure timestamp and frame_number are present
                if 'timestamp' not in processed_frame:
                    processed_frame['timestamp'] = i * initial_interval
                if 'frame_number' not in processed_frame:
                    processed_frame['frame_number'] = i

                processed_frames.append(processed_frame)

        logger.info(f"Extracted {len(processed_frames)} frames from video: {video_path}")
        return processed_frames
    except Exception as e:
        logger.error(f"Error processing video {video_path}: {str(e)}")
        raise

async def run_test_case(
    test_case: Dict[str, Any],
    model: Optional[str] = None,
    api_key: str = "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"
) -> Dict[str, Any]:
    """
    Run a single test case.

    Args:
        test_case: Test case dictionary
        model: Model to use for compliance checking (optional)
        api_key: API key for the LLM service (default: hardcoded OpenRouter API key)

    Returns:
        Test case dictionary with results
    """
    test_id = test_case["test_id"]
    asset_type = test_case["asset_type"].lower()
    asset_path = test_case.get("asset_path")

    # Skip if no asset path or asset doesn't exist
    if not asset_path or not test_case.get("asset_exists", False):
        logger.warning(f"Skipping test case {test_id}: No valid asset path")
        test_case["status"] = "skipped"
        test_case["error"] = "No valid asset path"
        return test_case

    logger.info(f"Running test case {test_id} ({asset_type})")

    # Create a copy of the test case to avoid modifying the original
    result = test_case.copy()

    # Add timing information
    start_time = time.time()

    try:
        # Create the OpenRouterAgent
        agent = OpenRouterAgent(model='anthropic/claude-3.7-sonnet', api_key=api_key)

        # Generate a prompt based on the test case
        prompt = generate_prompt(test_case)

        # Process the asset based on its type
        if asset_type == "image":
            # Process the image
            image_base64 = await process_image(asset_path)

            # Store the image data for evaluation
            result["image_data"] = image_base64

            # Run the agent
            agent_result = await agent.process(
                user_prompt=prompt,
                image_base64=image_base64
            )

        elif asset_type == "video":
            # Process the video
            frames = await process_video(asset_path)

            # Store the frames for evaluation
            result["frames"] = frames

            # Run the agent
            agent_result = await agent.process(
                user_prompt=prompt,
                frames=frames
            )

        else:
            raise ValueError(f"Unsupported asset type: {asset_type}")

        # Extract the final result
        if isinstance(agent_result, dict) and "final_result" in agent_result:
            actual_results = agent_result["final_result"]
        else:
            actual_results = str(agent_result)

        # Add the actual results to the test case
        result["actual_results"] = actual_results
        result["status"] = "completed"
        result["error"] = None

    except Exception as e:
        # Log the error
        logger.error(f"Error processing test case {test_id}: {str(e)}")

        # Add error information to the test case
        result["actual_results"] = None
        result["status"] = "failed"
        result["error"] = str(e)

    # Add timing information
    end_time = time.time()
    result["processing_time"] = end_time - start_time

    logger.info(f"Completed test case {test_id} in {result['processing_time']:.2f} seconds")
    return result

def generate_prompt(test_case: Dict[str, Any]) -> str:
    """
    Generate a prompt for the agent based on the test case.

    Args:
        test_case: Test case dictionary

    Returns:
        Prompt for the agent
    """
    # If the test case has a specific prompt, use it
    if "prompt" in test_case and test_case["prompt"]:
        return test_case["prompt"]

    # Otherwise, generate a generic prompt
    asset_type = test_case["asset_type"].lower()
    brand = test_case.get("brand", "")

    if asset_type == "image":
        return f"Analyze this {brand} image for brand compliance issues."
    elif asset_type == "video":
        return f"Analyze this {brand} video for brand compliance issues."
    else:
        return f"Analyze this {brand} asset for brand compliance issues."

async def run_benchmark(
    test_cases: List[Dict[str, Any]],
    model: Optional[str] = None,
    api_key: str = "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",
    max_concurrent: int = 1,
    output_file: Optional[str] = None,
    evaluate: bool = True,
    use_gemini_evaluator: bool = True
) -> List[Dict[str, Any]]:
    """
    Run the benchmark on all test cases.

    Args:
        test_cases: List of test case dictionaries
        model: Model to use for compliance checking (optional)
        api_key: API key for the LLM service (default: hardcoded OpenRouter API key)
        max_concurrent: Maximum number of concurrent test cases to run
        output_file: Path to save results after each test case (optional)
        evaluate: Whether to evaluate the results (default: True)
        use_gemini_evaluator: Whether to use the Gemini evaluator (default: True)

    Returns:
        List of test case dictionaries with results and evaluations
    """
    logger.info(f"Running benchmark on {len(test_cases)} test cases")

    # Create a semaphore to limit concurrency
    semaphore = asyncio.Semaphore(max_concurrent)

    # Create a list to store results
    results = []

    # Process test cases one by one
    for i, test_case in enumerate(test_cases):
        logger.info(f"Processing test case {i+1}/{len(test_cases)}")

        # Run the test case
        async with semaphore:
            result = await run_test_case(test_case, model, api_key)

        # Add to results
        results.append(result)

        # Save results to file if requested
        if output_file:
            with open(output_file, "w") as f:
                json.dump(results, f, indent=2)
            logger.info(f"Saved results to {output_file}")

    logger.info(f"Benchmark completed for {len(results)} test cases")

    # Evaluate the results if requested
    if evaluate:
        logger.info("Evaluating benchmark results...")

        # Choose the evaluator based on the use_gemini_evaluator flag
        if use_gemini_evaluator:
            logger.info("Using Gemini evaluator...")
            results = await evaluate_benchmark_results_gemini(results, max_concurrent)
        else:
            logger.info("Using default evaluator...")
            results = await evaluate_benchmark_results(results, model, api_key, max_concurrent)

        # Save evaluated results to file if requested
        if output_file:
            with open(output_file, "w") as f:
                json.dump(results, f, indent=2)
            logger.info(f"Saved evaluated results to {output_file}")

    return results

if __name__ == "__main__":
    # Example usage
    import sys
    from app.core.benchmark.excel_reader import read_and_analyze_benchmark

    if len(sys.argv) < 2:
        print("Usage: python benchmark_runner.py <excel_file_path> [mapping_file] [output_file]")
        sys.exit(1)

    excel_file = sys.argv[1]
    mapping_file = sys.argv[2] if len(sys.argv) > 2 else "benchmark/asset_mapping.json"
    output_file = sys.argv[3] if len(sys.argv) > 3 else "benchmark_results.json"

    async def main():
        try:
            # Read the benchmark Excel file
            results = read_and_analyze_benchmark(excel_file, mapping_file=mapping_file)

            # Run the benchmark
            benchmark_results = await run_benchmark(
                results["valid_test_cases"],
                output_file=output_file
            )

            print(f"Benchmark completed. Results saved to {output_file}")

        except Exception as e:
            print(f"Error: {str(e)}")
            sys.exit(1)

    # Run the main function
    asyncio.run(main())
