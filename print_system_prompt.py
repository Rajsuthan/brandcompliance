import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from backend.app.core.openrouter_agent.prompt_manager import get_system_prompt

# Models to check
models = [
    "anthropic/claude-3.7-sonnet",  # Current test model
    "anthropic/claude-3.5-sonnet",
    "mistralai/mistral-7b",
    "meta-llama/llama-2-70b"
]

print("\n=== System Prompts by Model ===\n")

for model in models:
    print(f"\n📝 Model: {model}")
    
    # Get system prompt for this model
    system_prompt = get_system_prompt(model)
    
    # Truncate the system prompt for display
    max_length = 500
    truncated_prompt = system_prompt[:max_length] + ("..." if len(system_prompt) > max_length else "")
    
    # Print the truncated system prompt
    print(f"\nSystem Prompt (truncated):\n{truncated_prompt}")
    print("\n" + "-"*50)

print("\n✅ Done printing system prompts")
