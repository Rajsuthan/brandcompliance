"""
Evaluator module for the benchmark system.

This module provides functions to evaluate the results of the benchmark.
"""

import os
import json
import time
import asyncio
from typing import Dict, List, Optional, Any
import logging
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def evaluate_test_case(
    test_case: Dict[str, Any],
    model: str = "anthropic/claude-3.7-sonnet",
    api_key: str = os.getenv("OPENROUTER_API_KEY")
) -> Dict[str, Any]:
    """
    Evaluate a single test case by comparing the actual results with the expected results.

    Args:
        test_case: Test case dictionary with actual and expected results
        model: Model to use for evaluation
        api_key: API key for the LLM service

    Returns:
        Test case dictionary with evaluation results
    """
    # Skip evaluation if the test case failed or has no actual results
    if test_case.get("status") != "completed" or not test_case.get("actual_results"):
        logger.warning(f"Skipping evaluation for test case {test_case.get('test_id')}: No actual results")
        test_case["evaluation"] = {
            "score": 0,
            "feedback": "No actual results to evaluate",
            "missed_issues": [],
            "false_positives": []
        }
        return test_case

    # Get the expected and actual results
    expected_results = test_case.get("expected_results", "")
    actual_results = test_case.get("actual_results", "")

    # Create a copy of the test case to avoid modifying the original
    result = test_case.copy()

    # Add timing information
    start_time = time.time()

    try:
        # Create the prompt for the LLM
        prompt = generate_evaluation_prompt(expected_results, actual_results, test_case)

        # Call the LLM to evaluate the results
        evaluation = await call_llm_for_evaluation(prompt, model, api_key)

        # Parse the evaluation
        parsed_evaluation = parse_evaluation_response(evaluation)

        # Add the evaluation to the test case
        result["evaluation"] = parsed_evaluation

    except Exception as e:
        logger.error(f"Error evaluating test case {test_case.get('test_id')}: {str(e)}")
        result["evaluation"] = {
            "score": 0,
            "feedback": f"Evaluation failed: {str(e)}",
            "missed_issues": [],
            "false_positives": []
        }

    # Add timing information
    end_time = time.time()
    if "evaluation" in result:
        result["evaluation"]["evaluation_time"] = end_time - start_time

    logger.info(f"Completed evaluation for test case {test_case.get('test_id')} with score {result.get('evaluation', {}).get('score', 0)}")
    return result

def generate_evaluation_prompt(expected_results: str, actual_results: str, test_case: Dict[str, Any]) -> str:
    """
    Generate a prompt for the LLM to evaluate the results.

    Args:
        expected_results: Expected results from the Excel file
        actual_results: Actual results from the agent
        test_case: Test case dictionary with additional information

    Returns:
        Prompt for the LLM
    """
    # Get additional information from the test case
    brand = test_case.get("brand", "")
    asset_type = test_case.get("asset_type", "")
    asset_name = test_case.get("asset_name", "")
    compliance_status = test_case.get("compliance_status", "")

    # Create the prompt
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

Provide your evaluation in the following JSON format:
{{
    "score": <0-100>,
    "feedback": "<detailed feedback>",
    "missed_issues": ["<issue 1>", "<issue 2>", ...],
    "false_positives": ["<non-issue 1>", "<non-issue 2>", ...]
}}

The score should be between 0 and 100, where:
- 90-100: Excellent - Identified all issues with accurate details
- 70-89: Good - Identified most issues with good details
- 50-69: Fair - Identified some issues but missed others or lacked detail
- 0-49: Poor - Missed many issues or provided inaccurate analysis

Your response should be ONLY the JSON object, nothing else.
"""

    return prompt

async def call_llm_for_evaluation(
    prompt: str,
    model: str = "anthropic/claude-3.7-sonnet",
    api_key: str = os.getenv("OPENROUTER_API_KEY")
) -> str:
    """
    Call the LLM to evaluate the results.

    Args:
        prompt: Prompt for the LLM
        model: Model to use for evaluation
        api_key: API key for the LLM service

    Returns:
        Response from the LLM
    """
    # Import the OpenRouterAgent
    from app.core.openrouter_agent.native_agent import OpenRouterAgent

    # Create the agent
    agent = OpenRouterAgent(
        api_key=api_key,
        model=model,
        stream=False,
        save_messages=False
    )

    # Process the prompt
    result = await agent.process(
        user_prompt=prompt,
        max_iterations=1,  # We only need one iteration for evaluation
        response_timeout=60,
        retry_count=1
    )

    # Extract the response
    if isinstance(result, dict):
        if "final_result" in result:
            return result["final_result"]
        elif "response" in result:
            return result["response"]
        else:
            # Log all available keys for debugging
            print(f"Available keys in result: {list(result.keys())}")
            return str(result)
    else:
        return str(result)

def parse_evaluation_response(response: str) -> Dict[str, Any]:
    """
    Parse the evaluation response from the LLM.

    Args:
        response: Response from the LLM

    Returns:
        Parsed evaluation
    """
    # Log the raw response for debugging
    logger.info(f"Raw evaluation response: {response[:500]}...")

    try:
        # If response is already a dict, convert it to a string first
        if isinstance(response, dict):
            logger.info(f"Response is a dict with keys: {list(response.keys())}")
            try:
                response = json.dumps(response)
            except Exception as e:
                logger.warning(f"Failed to convert dict response to JSON string: {str(e)}")
                response = str(response)

        # Try to parse the response as JSON
        try:
            evaluation = json.loads(response)
            logger.info(f"Successfully parsed response as JSON with keys: {list(evaluation.keys())}")
        except json.JSONDecodeError as json_err:
            # Try to extract JSON from the response if it contains other text
            logger.warning(f"Failed to parse response as JSON: {str(json_err)}")
            import re
            json_match = re.search(r'(\{.*\})', response, re.DOTALL)
            if json_match:
                try:
                    evaluation = json.loads(json_match.group(1))
                    logger.info(f"Extracted JSON from response with keys: {list(evaluation.keys())}")
                except json.JSONDecodeError:
                    raise
            else:
                raise

        # Ensure all required fields are present
        required_fields = ["score", "feedback", "missed_issues", "false_positives"]
        for field in required_fields:
            if field not in evaluation:
                evaluation[field] = [] if field in ["missed_issues", "false_positives"] else ""
                logger.warning(f"Added missing field '{field}' to evaluation")

        # Ensure score is an integer between 0 and 100
        try:
            evaluation["score"] = max(0, min(100, int(evaluation["score"])))
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to convert score to integer: {str(e)}")
            evaluation["score"] = 0

        return evaluation

    except Exception as e:
        logger.warning(f"Failed to parse evaluation response: {str(e)}")

        # Try to extract the score from the response
        score = 0
        for line in response.split("\n"):
            if "score" in line.lower():
                try:
                    score = int(''.join(filter(str.isdigit, line)))
                    score = max(0, min(100, score))
                    break
                except:
                    pass

        # Return a basic evaluation
        logger.warning(f"Returning basic evaluation with score {score}")
        return {
            "score": score,
            "feedback": response[:1000],  # Limit feedback length
            "missed_issues": [],
            "false_positives": []
        }

async def evaluate_benchmark_results(
    benchmark_results: List[Dict[str, Any]],
    model: str = "anthropic/claude-3.7-sonnet",
    api_key: str = os.getenv("OPENROUTER_API_KEY"),
    max_concurrent: int = 1
) -> List[Dict[str, Any]]:
    """
    Evaluate all benchmark results.

    Args:
        benchmark_results: List of test case dictionaries with actual results
        model: Model to use for evaluation
        api_key: API key for the LLM service
        max_concurrent: Maximum number of concurrent evaluations

    Returns:
        List of test case dictionaries with evaluation results
    """
    logger.info(f"Evaluating {len(benchmark_results)} benchmark results")

    # Create a semaphore to limit concurrency
    semaphore = asyncio.Semaphore(max_concurrent)

    # Create tasks for each test case
    tasks = []
    for test_case in benchmark_results:
        task = evaluate_test_case_with_semaphore(test_case, semaphore, model, api_key)
        tasks.append(task)

    # Run all tasks and gather results
    results = await asyncio.gather(*tasks)

    logger.info(f"Evaluation completed for {len(results)} test cases")
    return results

async def evaluate_test_case_with_semaphore(
    test_case: Dict[str, Any],
    semaphore: asyncio.Semaphore,
    model: str = "anthropic/claude-3.7-sonnet",
    api_key: str = os.getenv("OPENROUTER_API_KEY")
) -> Dict[str, Any]:
    """
    Evaluate a single test case with a semaphore to limit concurrency.

    Args:
        test_case: Test case dictionary with actual results
        semaphore: Semaphore to limit concurrency
        model: Model to use for evaluation
        api_key: API key for the LLM service

    Returns:
        Test case dictionary with evaluation results
    """
    async with semaphore:
        return await evaluate_test_case(test_case, model, api_key)
