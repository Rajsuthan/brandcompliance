from typing import Literal, Callable, Awaitable
from datetime import datetime
import json
import asyncio
import os
from dotenv import load_dotenv
from openai import OpenAI, AsyncAzureOpenAI, AzureOpenAI
from anthropic import AsyncAnthropic, Anthropic
from anthropic.types import MessageStreamEvent

# Load environment variables
load_dotenv()

# Client Initializations
gemini_client = OpenAI(
    api_key=os.getenv("GOOGLE_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

azure_client = AzureOpenAI(
    api_key=os.getenv("AZURE_API_KEY"),
    api_version="2024-08-01-preview",
    azure_endpoint=os.getenv("AZURE_ENDPOINT"),
)

async_openai_client = AsyncAzureOpenAI(
    api_key=os.getenv("AZURE_API_KEY"),
    api_version="2024-08-01-preview",
    azure_endpoint=os.getenv("AZURE_ENDPOINT"),
)

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

claude_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

async_claude_client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

models = [
    "gemini-2.0-flash-exp",
    "gemini-1.5-flash",
    "gemma-2-2b-it",
    "gpt-4o",
    "gemini-2.0-flash-thinking-exp-1219",
    "claude-3-7-sonnet-20250219",
    "o1-mini",
    "o1-preview",
    "gemini-2.0-flash-lite",
]


async def llm(
    model: Literal[
        "gemini-2.0-flash-exp",
        "gemini-1.5-flash",
        "gemma-2-2b-it",
        "gpt-4o",
        "gemini-2.0-flash-thinking-exp-1219",
        "claude-3-7-sonnet-20250219",
        "o1-mini",
        "o1-preview",
        "gemini-2.0-flash-lite",
    ] = "gemini-2.0-flash-exp",
    messages=[],
    response_format=None,
    system_prompt=None,
    on_stream: Callable[[dict], Awaitable] | None = None,
    stopwords=["(end_conversation)"],
    available_tools=None,
    on_stop: Callable[[str], Awaitable] | None = None,
    enable_thinking: bool = False,
):
    client = (
        gemini_client
        if "gemini" in model
        else (
            azure_client
            if model == "gpt-4o"
            else openai_client if "o1" in model else claude_client
        )
    )
    async_client = async_claude_client if "claude" in model else async_openai_client

    system_role = "user" if "o1" in model else "system"
    system_prompt = (
        f"Today's date: {datetime.now().strftime('%B %d, %Y')}\n"
        + (str(system_prompt) if system_prompt else "")
    ).replace(
        "<tools>", f"<tools>\n{str(available_tools or available_tools)}\n</tools>\n"
    )

    if not any(msg["role"] == "system" for msg in messages) and system_prompt:
        messages = [{"role": system_role, "content": system_prompt}] + messages

    # with open("llm_messages.json", "a") as f:
    #     json.dump(
    #         {
    #             "timestamp": datetime.now().isoformat(),
    #             "model": model,
    #             "messages": messages,
    #         },
    #         f,
    #     )
    #     f.write("\n")

    max_errors = 5
    errors = 0
    current_index = models.index(model) if model in models else 0

    while errors < max_errors:
        try:
            if "claude" in model:
                filtered_messages = [msg for msg in messages if msg["role"] != "system"]
                system_text = next(
                    (msg["content"] for msg in messages if msg["role"] == "system"),
                    None,
                )
                full_response = ""

                # Handle three distinct Claude streaming cases
                if enable_thinking:
                    # Thinking mode
                    with client.messages.stream(
                        model=model,
                        max_tokens=3200,
                        thinking={"type": "enabled", "budget_tokens": 3000},
                        messages=filtered_messages,
                        system=system_text,
                        stop_sequences=stopwords,
                    ) as stream:
                        thinking_state = "not-started"
                        for event in stream:
                            if event.type == "thinking":
                                if thinking_state == "not-started":
                                    thinking_state = "started"
                                if on_stream:
                                    await on_stream(
                                        {"type": "thinking", "content": event.thinking}
                                    )
                            elif event.type == "text":
                                if thinking_state != "finished":
                                    thinking_state = "finished"
                                full_response += event.text
                                if on_stream:
                                    await on_stream(
                                        {"type": "text", "content": event.text}
                                    )
                            elif event.type == "message_stop":
                                if on_stop:
                                    await on_stop("stop")
                                return full_response, "stop"

                elif available_tools or available_tools:
                    # Tools mode (async)
                    async with async_client.messages.stream(
                        model=model,
                        max_tokens=8192,
                        messages=filtered_messages,
                        system=system_text,
                        tools=available_tools,
                        stop_sequences=stopwords,
                    ) as stream:
                        async for event in stream:
                            if event.type == "content_block_delta":
                                if event.delta.type == "text_delta":
                                    full_response += event.delta.text
                                    if on_stream:
                                        await on_stream(
                                            {
                                                "type": "text",
                                                "content": event.delta.text,
                                            }
                                        )
                                elif event.delta.type == "input_json_delta":
                                    full_response += event.delta.partial_json
                                    if on_stream:
                                        await on_stream(
                                            {
                                                "type": "tool",
                                                "content": event.delta.partial_json,
                                            }
                                        )
                            elif event.type == "message_stop":
                                if on_stop:
                                    await on_stop("stop")
                                return full_response, "stop"

                else:
                    # Normal text streaming (async)
                    async with async_client.messages.stream(
                        model=model,
                        max_tokens=8192,
                        messages=filtered_messages,
                        system=system_text,
                        stop_sequences=stopwords,
                    ) as stream:
                        async for event in stream:
                            if (
                                event.type == "content_block_delta"
                                and event.delta.type == "text_delta"
                            ):
                                full_response += event.delta.text
                                if on_stream:
                                    await on_stream(
                                        {"type": "text", "content": event.delta.text}
                                    )
                            elif event.type == "message_stop":
                                if on_stop:
                                    await on_stop("stop")
                                return full_response, "stop"

            else:
                # Non-Claude handling remains the same
                if response_format:
                    response = client.beta.chat.completions.parse(
                        model=model,
                        messages=messages,
                        response_format=response_format,
                        stop=stopwords,
                    )
                    json_string = json.dumps(
                        response.choices[0].message.parsed.model_dump()
                    )
                    return json.loads(json_string), response.choices[0].finish_reason

                full_response = ""
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    stream=True,
                    stop=stopwords,
                )

                for message in response:
                    if message.choices and message.choices[0].delta:
                        if message.choices[0].finish_reason:
                            if on_stop:
                                await on_stop(message.choices[0].finish_reason)
                            return full_response, message.choices[0].finish_reason
                        if message.choices[0].delta.content:
                            content = str(message.choices[0].delta.content)
                            full_response += content
                            if on_stream:
                                await on_stream({"type": "text", "content": content})

        except Exception as e:
            print(f"❌ Error with {model}: {str(e)}")
            errors += 1
            if errors < max_errors:
                current_index = (current_index + 1) % len(models)
                model = models[current_index]
            else:
                raise Exception(f"Failed after {max_errors} attempts: {str(e)}")

    raise Exception("Unexpected error: Loop completed without return")


# # Example usage
# if __name__ == "__main__":

#     async def print_stream(data):
#         print(f"{data['type'].capitalize()}: {data['content']}", end="", flush=True)

#     async def print_stop(reason):
#         print(f"\nStopped: {reason}")

#     async def test():
#         # Test thinking mode
#         print("Testing thinking mode:")
#         response, reason = await llm(
#             model="claude-3-7-sonnet-20250219",
#             messages=[{"role": "user", "content": "Create a haiku about AI"}],
#             on_stream=print_stream,
#             on_stop=print_stop,
#             enable_thinking=True,
#         )
#         print(f"\nFinal response: {response}\n")

#         # Test tools mode
#         print("Testing tools mode:")
#         response, reason = await llm(
#             model="claude-3-7-sonnet-20250219",
#             messages=[{"role": "user", "content": "What’s the weather in SF?"}],
#             on_stream=print_stream,
#             on_stop=print_stop,
#             available_tools=claude_tools,
#         )
#         print(f"\nFinal response: {response}\n")

#         # Test normal streaming
#         print("Testing normal streaming:")
#         response, reason = await llm(
#             model="claude-3-7-sonnet-20250219",
#             messages=[{"role": "user", "content": "Hello! Tell me about Python"}],
#             on_stream=print_stream,
#             on_stop=print_stop,
#         )
#         print(f"\nFinal response: {response}")

#     asyncio.run(test())
