"""
Gemini-based evaluator module for the benchmark system.

This module provides functions to evaluate benchmark results using Gemini Pro via OpenRouter.
"""

import os
import json
import time
import asyncio
import re
import aiohttp
from typing import Dict, List, Optional, Any
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Custom function to safely parse JSON with JavaScript-style booleans
def safe_json_loads(content):
    """
    Safely parse JSON content that might contain JavaScript-style booleans.

    Args:
        content: JSON content as a string

    Returns:
        Parsed JSON object
    """
    # Log the content for debugging
    logger.info(f"Attempting to parse JSON content: {content[:200]}...")

    # First try standard JSON parsing
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.warning(f"Standard JSON parsing failed: {str(e)}")

        # Try replacing JavaScript-style booleans with Python-style booleans
        try:
            # Replace JavaScript-style booleans with Python-style booleans
            content_fixed = content.replace('true', 'True').replace('false', 'False')
            logger.info(f"Replaced JavaScript booleans: {content_fixed[:200]}...")

            # Use ast.literal_eval which is safer than eval()
            import ast
            try:
                return ast.literal_eval(content_fixed)
            except (SyntaxError, ValueError) as ast_error:
                logger.warning(f"ast.literal_eval failed: {str(ast_error)}")
        except Exception as e2:
            logger.warning(f"Boolean replacement failed: {str(e2)}")

        # Try to extract a JSON object from the content
        # This handles cases where there might be text before or after the JSON
        json_pattern = r'(\{[\s\S]*\})'
        match = re.search(json_pattern, content, re.DOTALL)
        if match:
            json_str = match.group(1)
            logger.info(f"Extracted JSON object: {json_str[:200]}...")

            # Replace JavaScript-style booleans with Python-style booleans
            json_str = json_str.replace('true', 'True').replace('false', 'False')

            try:
                # Try using ast.literal_eval first
                import ast
                try:
                    return ast.literal_eval(json_str)
                except (SyntaxError, ValueError):
                    # If that fails, try json.loads
                    return json.loads(json_str)
            except json.JSONDecodeError as e2:
                logger.warning(f"Extracted JSON parsing failed: {str(e2)}")

                # Try to clean up the JSON by removing comments and fixing common issues
                try:
                    # Remove JavaScript-style comments
                    import re
                    json_str_clean = re.sub(r'//.*?$', '', json_str, flags=re.MULTILINE)
                    # Remove trailing commas
                    json_str_clean = re.sub(r',\s*}', '}', json_str_clean)
                    json_str_clean = re.sub(r',\s*]', ']', json_str_clean)
                    logger.info(f"Cleaned JSON: {json_str_clean[:200]}...")

                    # Replace JavaScript-style booleans with Python-style booleans again
                    json_str_clean = json_str_clean.replace('true', 'True').replace('false', 'False')

                    # Try using ast.literal_eval first
                    import ast
                    try:
                        return ast.literal_eval(json_str_clean)
                    except (SyntaxError, ValueError):
                        # If that fails, try json.loads
                        return json.loads(json_str_clean)
                except Exception as e3:
                    logger.warning(f"Cleaned JSON parsing failed: {str(e3)}")

        # If all else fails, create a basic evaluation object
        logger.error(f"All JSON parsing attempts failed for content: {content[:500]}...")
        return {
            "score": 0,
            "feedback": "Failed to parse evaluation response",
            "missed_issues": [],
            "false_positives": []
        }

# OpenRouter API key
OPENROUTER_API_KEY = "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"

# Gemini model via OpenRouter
GEMINI_MODEL = "anthropic/claude-3.7-sonnet"

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

async def evaluate_with_gemini(
    expected_results: str,
    actual_results: str,
    test_case: Dict[str, Any],
    image_base64: Optional[str] = None,
    frames: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Evaluate benchmark results using Gemini Pro via OpenRouter.

    Args:
        expected_results: Expected results from the Excel file
        actual_results: Actual results from the agent
        test_case: Test case dictionary with additional information
        image_base64: Optional base64-encoded image for image test cases
        frames: Optional list of video frames with base64 data for video test cases

    Returns:
        Evaluation results as a dictionary
    """
    # Get additional information from the test case
    brand = test_case.get("brand", "")
    asset_type = test_case.get("asset_type", "")
    asset_name = test_case.get("asset_name", "")
    compliance_status = test_case.get("compliance_status", "")

    # Create the prompt with instructions for our custom format
    prompt = f"""
You are an expert evaluator of brand compliance analysis. Your task is to compare the expected results with the actual results from a compliance checking system and provide a detailed evaluation.

# Test Case Information
- Brand: {brand}
- Asset Type: {asset_type}
- Asset Name: {asset_name}
- Compliance Status: {compliance_status}

# Expected Results:
{expected_results}

# Actual Results:
{actual_results}

Please evaluate how well the actual results match the expected results. Consider the following criteria:
1. Completeness: Did it identify all the issues mentioned in the expected results?
2. Accuracy: Did it correctly describe the issues?
3. Precision: Did it avoid identifying non-issues?
4. Detail: Did it provide sufficient detail about each issue?

Your evaluation will be used to score the compliance checking system. Be thorough and fair in your assessment.

The score should be between 0 and 100, where:
- 90-100: Excellent - Identified all issues with accurate details
- 70-89: Good - Identified most issues with good details
- 50-69: Fair - Identified some issues but missed others or lacked detail
- 0-49: Poor - Missed many issues or provided inaccurate analysis

IMPORTANT: Format your response exactly as shown below, with each section separated by "----------":

score:
[A number from 0-100 indicating how well the actual results match the expected results]
----------
feedback:
[Detailed feedback explaining your evaluation]
----------
missed_issues:
[List each missed issue on a separate line. If none, write "None"]
----------
false_positives:
[List each false positive on a separate line. If none, write "None"]

Example response:

score:
85
----------
feedback:
The actual results captured most of the key issues but missed some important details about logo placement. The analysis was thorough in identifying color palette issues.
----------
missed_issues:
Logo blur on secondary packaging
Incorrect placement of disclaimer text
----------
false_positives:
Incorrect font usage
"""

    # Create the message content
    message_content = []

    # Add text prompt
    message_content.append({
        "type": "text",
        "text": prompt
    })

    # Add image if available
    if image_base64:
        message_content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{image_base64}"
            }
        })

    # Add video frames if available
    if frames and len(frames) > 0:
        # Limit to a reasonable number of frames to avoid token limits
        max_frames = min(10, len(frames))
        selected_frames = frames[:max_frames]

        logger.info(f"Adding {len(selected_frames)} video frames to the evaluation prompt")

        for frame in selected_frames:
            if "base64" in frame:
                message_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{frame['base64']}"
                    }
                })
            elif "image_data" in frame:
                message_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{frame['image_data']}"
                    }
                })

    # Call OpenRouter API directly using aiohttp
    try:
        start_time = time.time()

        # Log what we're about to do
        logger.info(f"Calling OpenRouter API with model {GEMINI_MODEL}")

        # Create the request payload for OpenRouter with structured output
        payload = {
            "model": GEMINI_MODEL,
            "messages": [
                {"role": "user", "content": message_content}
            ],
            # Instead of using JSON schema, we'll use a custom format with separators
            # that's easier to parse reliably
        }

        # Make the API call
        async with aiohttp.ClientSession() as session:
            async with session.post(
                OPENROUTER_API_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"OpenRouter API error: {response.status} - {error_text}")
                    return {
                        "score": 0,
                        "feedback": f"Evaluation failed: OpenRouter API error {response.status}",
                        "missed_issues": [],
                        "false_positives": [],
                        "evaluation_time": time.time() - start_time
                    }

                # Parse the response
                result = await response.json()

                # Log the successful API call
                logger.info(f"OpenRouter API call successful, received response")

                # Save the full response.json() in a txt file
                # Create the file if it doesn't exist
                with open("response.txt", "w+") as f:
                    json.dump(result, f)

                # Extract the content from the response exactly as shown in the OpenRouter example
                content = result["choices"][0]["message"]["content"]

                # Log token usage if available
                if "usage" in result:
                    prompt_tokens = result["usage"].get("prompt_tokens", 0)
                    completion_tokens = result["usage"].get("completion_tokens", 0)
                    total_tokens = result["usage"].get("total_tokens", 0)
                    logger.info(f"Token usage - Prompt: {prompt_tokens}, Completion: {completion_tokens}, Total: {total_tokens}")

                # Parse the custom format response
                try:
                    # Log the content for debugging
                    logger.info(f"Response content: {content[:200]}...")

                    # Validate that content is a string
                    if not isinstance(content, str):
                        logger.warning(f"Content is not a string but {type(content)}. Converting to string.")
                        content = str(content)

                    # Check if content is empty
                    if not content or content.isspace():
                        logger.error("Content is empty or whitespace")
                        raise ValueError("Empty content")

                    # Parse the custom format with sections separated by "----------"
                    # We know exactly what sections to expect in what order
                    sections = content.split("----------")

                    # Initialize the evaluation dictionary
                    evaluation = {
                        "score": 0,
                        "feedback": "",
                        "missed_issues": [],
                        "false_positives": []
                    }

                    # We should have 4 sections: score, feedback, missed_issues, false_positives
                    if len(sections) >= 4:
                        # Extract score (first section)
                        score_section = sections[0].strip()
                        if "score:" in score_section.lower():
                            score_text = score_section.split("score:", 1)[1].strip()
                            try:
                                evaluation["score"] = int(float(score_text))
                            except (ValueError, TypeError):
                                # If direct conversion fails, try to find any number in the text
                                import re
                                score_match = re.search(r'\d+', score_text)
                                if score_match:
                                    evaluation["score"] = int(score_match.group())

                        # Extract feedback (second section)
                        feedback_section = sections[1].strip()
                        if "feedback:" in feedback_section.lower():
                            evaluation["feedback"] = feedback_section.split("feedback:", 1)[1].strip()

                        # Extract missed issues (third section)
                        missed_section = sections[2].strip()
                        if "missed_issues:" in missed_section.lower():
                            missed_text = missed_section.split("missed_issues:", 1)[1].strip()
                            if missed_text.lower() != "none":
                                evaluation["missed_issues"] = [issue.strip() for issue in missed_text.split("\n") if issue.strip()]

                        # Extract false positives (fourth section)
                        if len(sections) > 3:
                            false_pos_section = sections[3].strip()
                            if "false_positives:" in false_pos_section.lower():
                                false_pos_text = false_pos_section.split("false_positives:", 1)[1].strip()
                                if false_pos_text.lower() != "none":
                                    evaluation["false_positives"] = [issue.strip() for issue in false_pos_text.split("\n") if issue.strip()]

                    logger.info(f"Successfully parsed custom format response: score={evaluation['score']}, feedback length={len(evaluation['feedback'])}, missed_issues={len(evaluation['missed_issues'])}, false_positives={len(evaluation['false_positives'])}")

                    # Add evaluation time
                    evaluation["evaluation_time"] = time.time() - start_time

                    # Add token usage if available
                    if "usage" in result:
                        evaluation["token_usage"] = result["usage"]

                    return evaluation

                except Exception as e:
                    logger.error(f"Failed to parse custom format response: {str(e)}")

                    # Try JSON parsing as a fallback
                    try:
                        # Try to parse as JSON first
                        evaluation = json.loads(content)
                        logger.info("Successfully parsed as JSON content")

                        # Add evaluation time
                        evaluation["evaluation_time"] = time.time() - start_time

                        return evaluation
                    except json.JSONDecodeError:
                        # Try our safe_json_loads function as a second fallback
                        try:
                            evaluation = safe_json_loads(content)
                            logger.info("Successfully parsed using safe_json_loads")

                            # Add evaluation time
                            evaluation["evaluation_time"] = time.time() - start_time

                            return evaluation
                        except Exception as e2:
                            logger.error(f"All parsing attempts failed: {str(e2)}")

                            # Return a basic evaluation
                            return {
                                "score": 0,
                                "feedback": f"Failed to parse evaluation: {content[:500]}...",
                                "missed_issues": [],
                                "false_positives": [],
                                "evaluation_time": time.time() - start_time
                            }

    except Exception as e:
        logger.error(f"Error evaluating with Gemini: {str(e)}")
        # Log the full exception traceback for debugging
        import traceback
        logger.error(f"Exception traceback: {traceback.format_exc()}")

        return {
            "score": 0,
            "feedback": f"Evaluation failed: {str(e)}",
            "missed_issues": [],
            "false_positives": [],
            "evaluation_time": time.time() - start_time if 'start_time' in locals() else 0
        }

async def evaluate_benchmark_results(
    benchmark_results: List[Dict[str, Any]],
    max_concurrent: int = 1
) -> List[Dict[str, Any]]:
    """
    Evaluate all benchmark results using Gemini Pro.

    Args:
        benchmark_results: List of test case dictionaries with actual results
        max_concurrent: Maximum number of concurrent evaluations

    Returns:
        List of test case dictionaries with evaluation results
    """
    logger.info(f"Evaluating {len(benchmark_results)} benchmark results with Gemini")

    # Create a semaphore to limit concurrency
    semaphore = asyncio.Semaphore(max_concurrent)

    # Create a list to store results
    results = []

    # Process test cases one by one
    for i, test_case in enumerate(benchmark_results):
        logger.info(f"Evaluating test case {i+1}/{len(benchmark_results)}")

        # Skip evaluation if the test case failed or has no actual results
        if test_case.get("status") != "completed" or not test_case.get("actual_results"):
            logger.warning(f"Skipping evaluation for test case {test_case.get('test_id')}: No actual results")
            test_case["evaluation"] = {
                "score": 0,
                "feedback": "No actual results to evaluate",
                "missed_issues": [],
                "false_positives": [],
                "evaluation_time": 0
            }
            results.append(test_case)
            continue

        # Get the expected and actual results
        expected_results = test_case.get("expected_results", "")
        actual_results = test_case.get("actual_results", "")

        # Create a copy of the test case to avoid modifying the original
        result = test_case.copy()

        # Get image or video frames if available
        image_base64 = None
        frames = None

        if test_case.get("asset_type") == "image" and "image_data" in test_case:
            image_base64 = test_case["image_data"]
            logger.info(f"Using image data for evaluation of test case {test_case.get('test_id')}")
        elif test_case.get("asset_type") == "video" and "frames" in test_case:
            frames = test_case["frames"]
            logger.info(f"Using {len(frames)} video frames for evaluation of test case {test_case.get('test_id')}")

        # Evaluate the results
        async with semaphore:
            evaluation = await evaluate_with_gemini(
                expected_results,
                actual_results,
                test_case,
                image_base64=image_base64,
                frames=frames
            )

            # Add the evaluation to the test case
            result["evaluation"] = evaluation

            # Add to results
            results.append(result)

    logger.info(f"Evaluation completed for {len(results)} test cases")
    return results

if __name__ == "__main__":
    # Example usage
    import sys
    import json

    async def main():
        if len(sys.argv) < 2:
            print("Usage: python gemini_evaluator.py <benchmark_results.json>")
            sys.exit(1)

        # Load benchmark results
        with open(sys.argv[1], "r") as f:
            benchmark_results = json.load(f)

        # Evaluate benchmark results
        evaluated_results = await evaluate_benchmark_results(benchmark_results)

        # Save evaluated results
        output_file = "evaluated_benchmark_results.json"
        with open(output_file, "w") as f:
            json.dump(evaluated_results, f, indent=2)

        print(f"Evaluation completed. Results saved to {output_file}")

    # Run the main function
    asyncio.run(main())
