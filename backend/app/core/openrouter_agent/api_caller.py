import os
import json
import asyncio
import time
import traceback
import datetime # Import datetime for timestamp formatting
from typing import List, Dict, Any, Optional, Callable, Awaitable

# Import necessary components from the agent
from .config import FALLBACK_MODELS
from .message_handler import MessageHandler

async def call_openrouter_api(
    client,
    messages: List[Dict[str, Any]],
    tools: List[Dict[str, Any]],
    model: str,
    temperature: float,
    max_tokens: int,
    stream: bool,
    timeout: int,
    message_handler: MessageHandler,
    timing_metrics: Dict[str, Any],
    iteration_count: int,
    retry_count: int = 2,
) -> Any:
    """
    Calls the OpenRouter API with retry and fallback logic.

    Args:
        client: The AsyncOpenAI client instance configured for OpenRouter.
        messages: The list of messages to send to the API.
        tools: The list of tool schemas.
        model: The primary model to use.
        temperature: The temperature parameter.
        max_tokens: The maximum tokens to generate.
        stream: Whether to stream the response.
        timeout: The API timeout in seconds.
        message_handler: The MessageHandler instance for streaming.
        timing_metrics: Dictionary to record timing data.
        iteration_count: The current iteration number.
        retry_count: Number of retries if API call fails.

    Returns:
        The completion response object if successful.

    Raises:
        Exception: If the API call fails after all retries and fallbacks.
    """
    api_error = None
    model_fallback_attempted = False
    current_model = model
    remaining_retries = retry_count

    while remaining_retries >= 0:
        try:
            # Record start time for LLM call
            llm_call_start = time.time()
            print(f"\033[94m[TIMING] LLM call started at {datetime.datetime.fromtimestamp(llm_call_start).strftime('%H:%M:%S.%f')[:-3]} with model {current_model}\033[0m")

            completion = await client.chat.completions.create(
                model=current_model,
                messages=messages,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
                timeout=timeout
            )

            # Record LLM call end time
            llm_call_end = time.time()
            llm_call_duration = llm_call_end - llm_call_start
            print(f"\033[94m[TIMING] LLM call completed in {llm_call_duration:.2f}s with model {current_model}\033[0m")

            # Add to timing metrics
            timing_metrics["llm_calls"].append({
                "purpose": "main_iteration",
                "iteration": iteration_count,
                "model": current_model,
                "start_time": llm_call_start,
                "end_time": llm_call_end,
                "duration": llm_call_duration,
                "fallback_attempted": model_fallback_attempted
            })

            return completion # Success

        except Exception as model_error:
            api_error = model_error
            error_msg = str(model_error)
            print(f"\033[91m[ERROR] Error with model {current_model}: {error_msg}\033[0m")

            # Check if this is a provider error that requires model fallback
            if "Provider returned error" in error_msg and not model_fallback_attempted:
                model_fallback_attempted = True

                # Stream the error to client
                if message_handler.on_stream:
                    asyncio.create_task(message_handler.on_stream({
                        "type": "text",
                        "content": f"The model {current_model} returned an error. Trying with a different model..."
                    }))

                # Try each fallback model in sequence
                for fallback_model in FALLBACK_MODELS:
                    # Skip the current model if it's in the fallback list
                    if fallback_model == current_model:
                        continue

                    print(f"\033[93m[MODEL FALLBACK] Trying fallback model: {fallback_model}\033[0m")

                    # Notify the user about the model change
                    if message_handler.on_stream:
                         asyncio.create_task(message_handler.on_stream({
                            "type": "text",
                            "content": f"Trying model: {fallback_model}"
                        }))

                    try:
                        # Try with the fallback model
                        completion = await client.chat.completions.create(
                            model=fallback_model,
                            messages=messages,
                            tools=tools,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            stream=stream,
                            timeout=timeout
                        )

                        # If we get here, the fallback model worked
                        print(f"\033[92m[MODEL FALLBACK] Successfully switched to {fallback_model}\033[0m")

                        # Update the current model for logging
                        current_model = fallback_model

                        # Clear the error since we succeeded with a fallback model
                        api_error = None

                        # Record LLM call end time for fallback
                        llm_call_end = time.time()
                        llm_call_duration = llm_call_end - llm_call_start
                        print(f"\033[94m[TIMING] LLM call completed in {llm_call_duration:.2f}s with fallback model {current_model}\033[0m")

                        # Add to timing metrics for fallback call
                        timing_metrics["llm_calls"].append({
                            "purpose": "main_iteration_fallback",
                            "iteration": iteration_count,
                            "model": current_model,
                            "start_time": llm_call_start,
                            "end_time": llm_call_end,
                            "duration": llm_call_duration,
                            "fallback_attempted": True
                        })

                        return completion # Success with fallback

                    except Exception as fallback_error:
                        # Log the fallback error and continue to the next model
                        print(f"\033[91m[ERROR] Fallback model {fallback_model} also failed: {str(fallback_error)}\033[0m")
                        api_error = fallback_error # Keep track of the last error

                # If we tried all fallbacks and still have an error, break the retry loop
                if api_error:
                    break # Exit the while loop

            # If not a provider error or fallback failed, handle retries
            remaining_retries -= 1
            if remaining_retries >= 0:
                wait_time = 2 * (retry_count - remaining_retries) # Exponential backoff
                print(f"\033[93m[WARNING] Retrying in {wait_time}s (retries left: {remaining_retries})\033[0m")
                if message_handler.on_stream:
                     asyncio.create_task(message_handler.on_stream({
                        "type": "text",
                        "content": f"Retrying API call in {wait_time} seconds..."
                    }))
                await asyncio.sleep(wait_time) # Use asyncio.sleep in async function
            else:
                # No retries left
                break # Exit the while loop

    # If we exit the loop, all attempts failed
    error_msg = f"Failed to get a response after multiple retries and fallbacks: {str(api_error)}"
    print(f"\033[91m[ERROR] {error_msg}\033[0m")
    if message_handler.on_stream:
        asyncio.create_task(message_handler.on_stream({
            "type": "error",
            "content": error_msg
        }))
    raise api_error # Re-raise the last error after all attempts fail
