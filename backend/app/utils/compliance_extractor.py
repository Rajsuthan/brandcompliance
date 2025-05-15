"""
Utility functions for extracting structured information from compliance analysis reports.

This module provides functions to:
1. Extract brand name and compliance score from a detailed compliance report
2. Format the extracted information in a consistent, easily parsable format
3. Parse the formatted information to extract the brand name and score
"""

import os
import json
import re
import asyncio
from typing import Dict, Any, Tuple, Optional, Union

from openai import AsyncOpenAI

# Constants
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_TIMEOUT = 30  # 30 seconds timeout for extraction API calls
DEFAULT_MODEL = "anthropic/claude-3.7-sonnet"  # Default model for extraction

# Extraction prompt template
EXTRACTION_PROMPT = """
You are a specialized data extraction system. Your task is to analyze a compliance report and extract:
1. The brand name being analyzed
2. A numerical compliance score as a percentage (0-100)

Extract this information from the provided compliance report and format your response EXACTLY as follows:

brand:
[extracted brand name]
-----
score:
[numerical score 0-100]

IMPORTANT INSTRUCTIONS:
- For the brand name, extract the specific brand being analyzed (e.g., "Nike", "Coca-Cola", "Apple")
- For the score, provide a numerical value between 0-100 representing the overall compliance percentage
- If the score is not explicitly stated, estimate it based on the overall assessment (e.g., "Major Issues" might be 40-60%)
- If you cannot determine a brand name, use "Unknown"
- If you cannot determine a score, use "50" as a neutral value
- DO NOT include any explanations, just the extracted information in the exact format specified
- DO NOT include any other text outside the specified format

Here is the compliance report to analyze:
"""

async def extract_brand_and_score(
    compliance_report: Union[str, Dict[str, Any]],
    api_key: str = OPENROUTER_API_KEY,
    model: str = DEFAULT_MODEL,
    timeout: int = OPENROUTER_TIMEOUT
) -> Tuple[str, int]:
    """
    Extract brand name and compliance score from a compliance report.
    
    Args:
        compliance_report: The compliance report text or dictionary
        api_key: OpenRouter API key
        model: Model to use for extraction
        timeout: Timeout in seconds for the API call
        
    Returns:
        Tuple of (brand_name, compliance_score)
    """
    # Convert dictionary to string if needed
    if isinstance(compliance_report, dict):
        report_text = json.dumps(compliance_report)
    else:
        report_text = str(compliance_report)
    
    # Initialize OpenAI client with OpenRouter settings
    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        default_headers={
            "HTTP-Referer": "https://brandguideline.ai",
            "X-Title": "Brand Compliance AI"
        }
    )
    
    # Create the full prompt
    full_prompt = EXTRACTION_PROMPT + report_text
    
    try:
        # Make the API call
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a specialized data extraction system."},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.1,  # Low temperature for consistent results
            max_tokens=200,   # Limit tokens since we expect a short response
            stream=False,
            timeout=timeout
        )
        
        # Extract the response text
        response_text = response.choices[0].message.content.strip()
        
        # Parse the response to extract brand and score
        brand_name, compliance_score = parse_extraction_response(response_text)
        
        return brand_name, compliance_score
        
    except Exception as e:
        print(f"\033[91m[ERROR] Failed to extract brand and score: {str(e)}\033[0m")
        # Return default values if extraction fails
        return "Unknown", 50

def parse_extraction_response(response_text: str) -> Tuple[str, int]:
    """
    Parse the extraction response to get brand name and compliance score.
    
    Args:
        response_text: The formatted response text
        
    Returns:
        Tuple of (brand_name, compliance_score)
    """
    # Default values
    brand_name = "Unknown"
    compliance_score = 50
    
    try:
        # Extract brand name using regex
        brand_match = re.search(r'brand:\s*(.+?)\s*-----', response_text, re.DOTALL)
        if brand_match:
            brand_name = brand_match.group(1).strip()
        
        # Extract score using regex
        score_match = re.search(r'score:\s*(\d+)', response_text)
        if score_match:
            score_str = score_match.group(1).strip()
            try:
                compliance_score = int(score_str)
                # Ensure score is within valid range
                compliance_score = max(0, min(100, compliance_score))
            except ValueError:
                # If conversion fails, keep default
                pass
    
    except Exception as e:
        print(f"\033[93m[WARNING] Error parsing extraction response: {str(e)}\033[0m")
        print(f"\033[93m[WARNING] Response text: {response_text}\033[0m")
    
    return brand_name, compliance_score
