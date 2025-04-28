"""
Prompt Manager for OpenRouter Agent

This module provides model-specific prompts for the OpenRouter agent.
It determines the appropriate prompt style based on the model being used.
"""

from typing import Dict, Any, Literal

ModelType = Literal["llama", "claude_3_5", "claude_3_7", "default"]


def get_model_type(model_name: str) -> ModelType:
    """
    Determine the type of model based on its name.

    Args:
        model_name: The name of the model

    Returns:
        The type of model (llama, claude_3_5, claude_3_7, or default)
    """
    model_name_lower = model_name.lower()

    if "llama" in model_name_lower:
        return "llama"
    elif "claude-3-5" in model_name_lower or "claude-3.5" in model_name_lower:
        return "claude_3_5"
    elif "claude-3-7" in model_name_lower or "claude-3.7" in model_name_lower:
        return "claude_3_7"
    else:
        return "default"


def get_tool_result_prompt(model_name: str, tool_tag: str, tool_result: str) -> str:
    """
    Get the appropriate tool result prompt for the model.

    Args:
        model_name: The name of the model
        tool_tag: The name of the tool that was called
        tool_result: The result from the tool

    Returns:
        A formatted prompt for the tool result
    """
    model_type = get_model_type(model_name)

    if model_type == "llama":
        # Llama models need very explicit, structured instructions with visual formatting
        return (
            f"### TOOL RESULT: {tool_tag}\n\n"
            f"```\n{tool_result}\n```\n\n"
            f"### NEXT STEPS:\n\n"
            f"1. **ANALYZE DEEPLY** the above result from the {tool_tag} tool\n"
            f"2. **CHECK THOROUGHLY** against all brand guidelines and compliance requirements\n"
            f"3. **DECIDE** what to do next based on this information:\n"
            f"   - If you need more information, call another tool using XML format\n"
            f"   - If you have all necessary information, provide your final compliance analysis\n\n"
            f"**FOR IMAGE ANALYSIS**:\n"
            f"- Examine all visual elements (colors, typography, layout, imagery)\n"
            f"- Check for brand consistency in all elements\n"
            f"- Verify proper logo usage and placement\n"
            f"- Assess text readability and clarity\n\n"
            f"**FOR VIDEO ANALYSIS**:\n"
            f"- Analyze ALL frames for compliance issues\n"
            f"- Check transitions, animations, and timing\n"
            f"- Verify audio elements match brand voice\n"
            f"- Examine text overlays and captions\n\n"
            f"**IF CONTINUING ANALYSIS**:\n"
            f"- Call specific tools to gather more detailed information\n"
            f"- Be methodical and thorough in your investigation\n"
            f"- Use all available tools to check every aspect of compliance\n\n"
            f"**IF READY FOR FINAL ANALYSIS**:\n"
            f"- Use the attempt_completion tool with proper XML format\n"
            f"- Include ALL compliance findings in your final report\n"
            f"- Provide specific recommendations for any issues found\n\n"
            f"Remember to use proper XML format for all tool calls and be extremely thorough in your analysis."
        )
    elif model_type == "claude_3_5":
        # Claude 3.5 Sonnet works well with clear, direct instructions and structured format
        return (
            f"### TOOL RESULT: {tool_tag}\n\n"
            f"```\n{tool_result}\n```\n\n"
            f"### NEXT STEPS:\n\n"
            f"1. Analyze the above result from the {tool_tag} tool systematically\n"
            f"2. Evaluate compliance against brand guidelines with attention to detail\n"
            f"3. Decide your next action:\n"
            f"   - Call another tool if you need more specific information\n"
            f"   - Provide your final compliance analysis if you have sufficient data\n\n"
            f"For image/video content, examine:\n"
            f"- Visual elements: colors, typography, layout, imagery, logo usage\n"
            f"- Brand consistency across all elements\n"
            f"- Text readability and clarity\n"
            f"- For videos: key frames, transitions, audio elements\n\n"
            f"When ready for final analysis:\n"
            f"- Use the attempt_completion tool with proper XML format\n"
            f"- Include comprehensive findings and specific recommendations\n\n"
            f"Remember to use proper XML format for all tool calls."
        )
    elif model_type == "claude_3_7":
        # Claude 3.7 Sonnet works best with concise, clear instructions
        return (
            f"### TOOL RESULT: {tool_tag}\n\n"
            f"```\n{tool_result}\n```\n\n"
            f"### NEXT STEPS:\n\n"
            f"1. Analyze this {tool_tag} result thoroughly against brand guidelines\n"
            f"2. For visual content, check: colors, typography, layout, imagery, logo usage, text readability\n"
            f"3. For video content, examine: key frames, transitions, animations, audio elements\n\n"
            f"If you need more information:\n"
            f"- Call another tool using proper XML format\n"
            f"- Be specific about what you're analyzing\n\n"
            f"If you have sufficient information:\n"
            f"- Use the attempt_completion tool\n"
            f"- Include comprehensive findings and specific recommendations\n"
            f"- Format using proper XML structure\n\n"
            f"Be methodical and thorough in your compliance analysis."
        )
    else:
        # Default format for other models
        return (
            f"### TOOL RESULT: {tool_tag}\n\n"
            f"```\n{tool_result}\n```\n\n"
            f"### NEXT STEPS:\n\n"
            f"1. **ANALYZE** the above result from the {tool_tag} tool\n"
            f"2. **DECIDE** what to do next based on this information:\n"
            f"   - If you need more information, call another tool using XML format\n"
            f"   - If you have all necessary information, provide your final compliance analysis\n\n"
            f"3. **IF CONTINUING ANALYSIS**:\n"
            f"   - Call another tool using proper XML format\n"
            f"   - Be specific about what you're analyzing\n\n"
            f"4. **IF READY FOR FINAL ANALYSIS**:\n"
            f"   - Use the attempt_completion tool\n"
            f"   - Format your response according to the required structure\n\n"
            f"Remember to use proper XML format for all tool calls."
        )


def get_empty_response_prompt(model_name: str) -> str:
    """
    Get the appropriate empty response prompt for the model.

    Args:
        model_name: The name of the model

    Returns:
        A formatted prompt for empty responses
    """
    model_type = get_model_type(model_name)

    if model_type == "llama":
        # Llama models need very explicit, structured instructions with visual formatting
        return (
            "### EMPTY RESPONSE DETECTED\n\n"
            "I notice you might be unsure how to proceed. You need to complete the compliance analysis "
            "and provide a final result using the attempt_completion tool.\n\n"
            "**REQUIRED ACTIONS:**\n\n"
            "1. **FINALIZE YOUR ANALYSIS** - You should be finished with your analysis by now\n"
            "2. **USE THE ATTEMPT_COMPLETION TOOL** - This is required to complete the task\n"
            "3. **FOLLOW THE EXACT FORMAT BELOW**\n\n"
            "```xml\n"
            "<attempt_completion>\n"
            "<r>\n"
            "## Compliance Analysis for [Content Type]\n\n"
            "### Executive Summary\n"
            "[Your detailed analysis here...]\n"
            "</r>\n"
            "<tool_name>attempt_completion</tool_name>\n"
            "<task_detail>Final Compliance Analysis</task_detail>\n"
            "</attempt_completion>\n"
            "```\n\n"
            "**IMPORTANT INSTRUCTIONS FOR THOROUGH COMPLIANCE ANALYSIS:**\n"
            "- Analyze ALL aspects of the content against brand guidelines\n"
            "- For images: check colors, typography, layout, imagery, logo usage, text readability\n"
            "- For videos: analyze all frames, transitions, animations, audio elements, text overlays\n"
            "- Include specific findings for each element checked\n"
            "- Provide detailed recommendations for any compliance issues\n"
            "- Format your response using the exact XML structure above\n\n"
            "This is the final step in the compliance analysis process. Please provide your complete and thorough analysis now."
        )
    elif model_type == "claude_3_5":
        # Claude 3.5 Sonnet works well with clear, direct instructions and structured format
        return (
            "### EMPTY RESPONSE DETECTED\n\n"
            "I notice you might be unsure how to proceed. You need to complete the compliance analysis "
            "and provide a final result using the attempt_completion tool.\n\n"
            "**REQUIRED ACTIONS:**\n\n"
            "1. Finalize your analysis - You should have gathered sufficient information by now\n"
            "2. Use the attempt_completion tool - This is required to complete the task\n"
            "3. Follow the exact format below:\n\n"
            "```xml\n"
            "<attempt_completion>\n"
            "<r>\n"
            "## Compliance Analysis for [Content Type]\n\n"
            "### Executive Summary\n"
            "[Your detailed analysis here...]\n"
            "</r>\n"
            "<tool_name>attempt_completion</tool_name>\n"
            "<task_detail>Final Compliance Analysis</task_detail>\n"
            "</attempt_completion>\n"
            "```\n\n"
            "**IMPORTANT INSTRUCTIONS:**\n"
            "- Analyze all visual elements systematically (colors, typography, layout, imagery, logo usage)\n"
            "- For videos, examine key frames, transitions, audio elements, and text overlays\n"
            "- Include specific findings and recommendations for any compliance issues\n"
            "- Format your response using the exact XML structure above\n\n"
            "This is the final step in the compliance analysis process. Please provide your complete analysis now."
        )
    elif model_type == "claude_3_7":
        # Claude 3.7 Sonnet works best with concise, clear instructions
        return (
            "### EMPTY RESPONSE DETECTED\n\n"
            "You need to complete the compliance analysis using the attempt_completion tool.\n\n"
            "**REQUIRED ACTIONS:**\n\n"
            "1. Finalize your analysis\n"
            "2. Use this exact format:\n\n"
            "```xml\n"
            "<attempt_completion>\n"
            "<r>\n"
            "## Compliance Analysis for [Content Type]\n\n"
            "### Executive Summary\n"
            "[Your detailed analysis here...]\n"
            "</r>\n"
            "<tool_name>attempt_completion</tool_name>\n"
            "<task_detail>Final Compliance Analysis</task_detail>\n"
            "</attempt_completion>\n"
            "```\n\n"
            "Include a thorough analysis of all visual elements, brand consistency, and compliance issues. For videos, examine key frames, transitions, and audio elements. Provide specific recommendations for any issues found.\n\n"
            "This is the final step in the compliance analysis process."
        )
    else:
        # Default format for other models
        return (
            "### EMPTY RESPONSE DETECTED\n\n"
            "I notice you might be unsure how to proceed. You need to complete the compliance analysis "
            "and provide a final result using the attempt_completion tool.\n\n"
            "**REQUIRED ACTIONS:**\n\n"
            "1. **FINALIZE YOUR ANALYSIS** - You should be finished with your analysis by now\n"
            "2. **USE THE ATTEMPT_COMPLETION TOOL** - This is required to complete the task\n"
            "3. **FOLLOW THE EXACT FORMAT BELOW**\n\n"
            "```xml\n"
            "<attempt_completion>\n"
            "<r>\n"
            "## Compliance Analysis for [Content Type]\n\n"
            "### Executive Summary\n"
            "[Your detailed analysis here...]\n"
            "</r>\n"
            "<tool_name>attempt_completion</tool_name>\n"
            "<task_detail>Final Compliance Analysis</task_detail>\n"
            "</attempt_completion>\n"
            "```\n\n"
            "**IMPORTANT INSTRUCTIONS:**\n"
            "- Copy the exact XML structure above\n"
            "- Replace the content inside the `<r>` tags with your compliance analysis\n"
            "- Keep all the XML tags exactly as shown\n"
            "- Include all required sections (Executive Summary, Analysis, etc.)\n\n"
            "This is the final step in the compliance analysis process. Please provide your complete analysis now."
        )


def get_format_guidance_prompt(model_name: str) -> str:
    """
    Get the appropriate format guidance prompt for the model.

    Args:
        model_name: The name of the model

    Returns:
        A formatted prompt for format guidance
    """
    model_type = get_model_type(model_name)

    if model_type == "llama":
        # Llama models need very explicit, structured instructions with visual formatting
        return (
            "### IMPORTANT: XML FORMAT CORRECTION NEEDED\n\n"
            "I see you're trying to provide the final compliance analysis, but you need to use the proper XML format for the attempt_completion tool.\n\n"
            "Please use this **exact** format:\n"
            "```xml\n"
            "<attempt_completion>\n"
            "<r>\n"
            "## Compliance Analysis for [Content Type]\n\n"
            "### Executive Summary\n"
            "[Your detailed analysis here...]\n"
            "</r>\n"
            "<tool_name>attempt_completion</tool_name>\n"
            "<task_detail>Final Compliance Analysis</task_detail>\n"
            "</attempt_completion>\n"
            "```\n\n"
            "**INSTRUCTIONS FOR THOROUGH COMPLIANCE ANALYSIS:**\n"
            "1. Copy the exact XML structure above\n"
            "2. Replace the content inside the `<r>` tags with your comprehensive compliance analysis\n"
            "3. Include detailed findings on ALL aspects of the content:\n"
            "   - For images: colors, typography, layout, imagery, logo usage, text readability\n"
            "   - For videos: all frames, transitions, animations, audio elements, text overlays\n"
            "4. Provide specific recommendations for any compliance issues found\n"
            "5. Keep all the XML tags exactly as shown\n"
            "6. Make sure to include `<tool_name>attempt_completion</tool_name>`\n\n"
            "Please reformat your analysis using this exact XML structure and ensure it covers all compliance aspects in detail."
        )
    elif model_type == "claude_3_5":
        # Claude 3.5 Sonnet works well with clear, direct instructions and structured format
        return (
            "### IMPORTANT: XML FORMAT CORRECTION NEEDED\n\n"
            "I see you're trying to provide the final compliance analysis, but you need to use the proper XML format for the attempt_completion tool.\n\n"
            "Please use this exact format:\n"
            "```xml\n"
            "<attempt_completion>\n"
            "<r>\n"
            "## Compliance Analysis for [Content Type]\n\n"
            "### Executive Summary\n"
            "[Your detailed analysis here...]\n"
            "</r>\n"
            "<tool_name>attempt_completion</tool_name>\n"
            "<task_detail>Final Compliance Analysis</task_detail>\n"
            "</attempt_completion>\n"
            "```\n\n"
            "**INSTRUCTIONS:**\n"
            "1. Copy the exact XML structure above\n"
            "2. Replace the content inside the `<r>` tags with your comprehensive analysis\n"
            "3. Include detailed findings on all visual elements and compliance aspects\n"
            "4. Provide specific recommendations for any issues found\n"
            "5. Keep all XML tags exactly as shown\n\n"
            "Please reformat your analysis using this exact XML structure."
        )
    elif model_type == "claude_3_7":
        # Claude 3.7 Sonnet works best with concise, clear instructions
        return (
            "### XML FORMAT CORRECTION NEEDED\n\n"
            "Please use this exact format for your compliance analysis:\n"
            "```xml\n"
            "<attempt_completion>\n"
            "<r>\n"
            "## Compliance Analysis for [Content Type]\n\n"
            "### Executive Summary\n"
            "[Your detailed analysis here...]\n"
            "</r>\n"
            "<tool_name>attempt_completion</tool_name>\n"
            "<task_detail>Final Compliance Analysis</task_detail>\n"
            "</attempt_completion>\n"
            "```\n\n"
            "Include a thorough analysis of all visual elements, brand consistency, and compliance issues. Provide specific recommendations for any issues found. Keep all XML tags exactly as shown."
        )
    else:
        # Default format for other models
        return (
            "### IMPORTANT: XML FORMAT CORRECTION NEEDED\n\n"
            "I see you're trying to provide the final compliance analysis, but you need to use the proper XML format for the attempt_completion tool.\n\n"
            "Please use this **exact** format:\n"
            "```xml\n"
            "<attempt_completion>\n"
            "<r>\n"
            "## Compliance Analysis for [Content Type]\n\n"
            "### Executive Summary\n"
            "[Your detailed analysis here...]\n"
            "</r>\n"
            "<tool_name>attempt_completion</tool_name>\n"
            "<task_detail>Final Compliance Analysis</task_detail>\n"
            "</attempt_completion>\n"
            "```\n\n"
            "**INSTRUCTIONS:**\n"
            "1. Copy the exact XML structure above\n"
            "2. Replace the content inside the `<r>` tags with your compliance analysis\n"
            "3. Keep all the XML tags exactly as shown\n"
            "4. Make sure to include `<tool_name>attempt_completion</tool_name>`\n\n"
            "Please reformat your analysis using this exact XML structure."
        )


def get_iteration_milestone_prompt(model_name: str, iteration_count: int) -> str:
    """
    Get the appropriate iteration milestone prompt for the model.

    Args:
        model_name: The name of the model
        iteration_count: The current iteration count

    Returns:
        A formatted prompt for iteration milestones
    """
    model_type = get_model_type(model_name)

    if model_type == "llama":
        # Llama models need very explicit, structured instructions with visual formatting
        return (
            f"### ITERATION MILESTONE: {iteration_count}\n\n"
            f"You have reached {iteration_count} iterations in this compliance analysis process.\n\n"
            f"**DECISION POINT:**\n\n"
            f"* **IF READY TO CONCLUDE**: Use the attempt_completion tool now to provide your final analysis\n"
            f"* **IF MORE ANALYSIS NEEDED**: Continue with specific tool calls to gather additional information\n\n"
            f"**IMPORTANT COMPLIANCE CONSIDERATIONS:**\n\n"
            f"Have you thoroughly checked ALL of these aspects?\n"
            f"- Visual elements: colors, typography, layout, imagery, logo usage\n"
            f"- Brand consistency across all elements\n"
            f"- Text readability and clarity\n"
            f"- For videos: all frames, transitions, animations, audio elements\n\n"
            f"**REMINDER FOR FINAL SUBMISSION:**\n"
            f"```xml\n"
            f"<attempt_completion>\n"
            f"<r>\n"
            f"## Compliance Analysis for [Content Type]\n\n"
            f"### Executive Summary\n"
            f"[Your detailed analysis here...]\n"
            f"</r>\n"
            f"<tool_name>attempt_completion</tool_name>\n"
            f"<task_detail>Final Compliance Analysis</task_detail>\n"
            f"</attempt_completion>\n"
            f"```\n\n"
            f"Please decide whether to conclude your analysis or continue with specific additional investigations. If continuing, use all available tools to check every aspect of compliance in detail."
        )
    elif model_type == "claude_3_5":
        # Claude 3.5 Sonnet works well with clear, direct instructions and structured format
        return (
            f"### ITERATION MILESTONE: {iteration_count}\n\n"
            f"You have reached {iteration_count} iterations in this compliance analysis process.\n\n"
            f"**DECISION POINT:**\n\n"
            f"* If you have sufficient information: Use the attempt_completion tool to provide your final analysis\n"
            f"* If you need more data: Continue with specific tool calls to gather additional information\n\n"
            f"**COMPLIANCE CHECKLIST:**\n\n"
            f"Have you thoroughly examined these aspects?\n"
            f"- Visual elements: colors, typography, layout, imagery, logo usage\n"
            f"- Brand consistency across all elements\n"
            f"- For videos: key frames, transitions, audio elements\n\n"
            f"**REMINDER FOR FINAL SUBMISSION:**\n"
            f"```xml\n"
            f"<attempt_completion>\n"
            f"<r>\n"
            f"## Compliance Analysis for [Content Type]\n\n"
            f"### Executive Summary\n"
            f"[Your detailed analysis here...]\n"
            f"</r>\n"
            f"<tool_name>attempt_completion</tool_name>\n"
            f"<task_detail>Final Compliance Analysis</task_detail>\n"
            f"</attempt_completion>\n"
            f"```\n\n"
            f"Please decide whether to conclude your analysis or continue with specific additional investigations."
        )
    elif model_type == "claude_3_7":
        # Claude 3.7 Sonnet works best with concise, clear instructions
        return (
            f"### ITERATION MILESTONE: {iteration_count}\n\n"
            f"You've reached {iteration_count} iterations. Please decide:\n\n"
            f"1. Use attempt_completion tool now to provide your final analysis, or\n"
            f"2. Continue with specific tool calls if you need more information\n\n"
            f"Have you thoroughly examined all visual elements, brand consistency, and compliance aspects?\n\n"
            f"Final submission format:\n"
            f"```xml\n"
            f"<attempt_completion>\n"
            f"<r>\n"
            f"## Compliance Analysis for [Content Type]\n\n"
            f"### Executive Summary\n"
            f"[Your detailed analysis here...]\n"
            f"</r>\n"
            f"<tool_name>attempt_completion</tool_name>\n"
            f"<task_detail>Final Compliance Analysis</task_detail>\n"
            f"</attempt_completion>\n"
            f"```"
        )
    else:
        # Default format for other models
        return (
            f"### ITERATION MILESTONE: {iteration_count}\n\n"
            f"You have reached {iteration_count} iterations in this compliance analysis process.\n\n"
            f"**DECISION POINT:**\n\n"
            f"* **IF READY TO CONCLUDE**: Use the attempt_completion tool now to provide your final analysis\n"
            f"* **IF MORE ANALYSIS NEEDED**: Continue with specific tool calls to gather additional information\n\n"
            f"**REMINDER FOR FINAL SUBMISSION:**\n"
            f"```xml\n"
            f"<attempt_completion>\n"
            f"<r>\n"
            f"## Compliance Analysis for [Content Type]\n\n"
            f"### Executive Summary\n"
            f"[Your detailed analysis here...]\n"
            f"</r>\n"
            f"<tool_name>attempt_completion</tool_name>\n"
            f"<task_detail>Final Compliance Analysis</task_detail>\n"
            f"</attempt_completion>\n"
            f"```\n\n"
            f"Please decide whether to conclude your analysis or continue with specific additional investigations."
        )


def get_force_completion_prompt(model_name: str) -> str:
    """
    Get the appropriate force completion prompt for the model.

    Args:
        model_name: The name of the model

    Returns:
        A formatted prompt for forcing completion
    """
    model_type = get_model_type(model_name)

    if model_type == "llama":
        # Llama models need very explicit, structured instructions with visual formatting
        return (
            "### ATTENTION: COMPLETION REQUIRED\n\n"
            "You have been analyzing this content for a while now. It's time to finalize your analysis.\n\n"
            "**CRITICAL INSTRUCTION:**\n"
            "You MUST use the attempt_completion tool now to provide your final comprehensive compliance analysis. "
            "This is required to complete the task. Do not continue with more analysis - summarize what you've found so far.\n\n"
            "**REQUIRED FORMAT:**\n"
            "```xml\n"
            "<attempt_completion>\n"
            "<r>\n"
            "## Compliance Analysis for [Content Type]\n\n"
            "### Executive Summary\n"
            "[Your detailed analysis here...]\n"
            "</r>\n"
            "<tool_name>attempt_completion</tool_name>\n"
            "<task_detail>Final Compliance Analysis</task_detail>\n"
            "</attempt_completion>\n"
            "```\n\n"
            "**STEP-BY-STEP INSTRUCTIONS FOR THOROUGH COMPLIANCE ANALYSIS:**\n"
            "1. Copy the exact XML structure above\n"
            "2. Replace the content inside the `<r>` tags with your comprehensive compliance analysis\n"
            "3. Include an Executive Summary with your key findings\n"
            "4. Cover ALL aspects of the content in your analysis:\n"
            "   - For images: colors, typography, layout, imagery, logo usage, text readability\n"
            "   - For videos: all frames, transitions, animations, audio elements, text overlays\n"
            "5. Provide specific recommendations for any compliance issues found\n"
            "6. Make sure to include all required XML tags\n\n"
            "This is the final step in the compliance analysis process. You must provide your complete and thorough analysis now."
        )
    elif model_type == "claude_3_5":
        # Claude 3.5 Sonnet works well with clear, direct instructions and structured format
        return (
            "### COMPLETION REQUIRED\n\n"
            "You have been analyzing this content for a while now. It's time to finalize your analysis.\n\n"
            "**CRITICAL INSTRUCTION:**\n"
            "You MUST use the attempt_completion tool now to provide your final compliance analysis. "
            "This is required to complete the task. Summarize what you've found so far.\n\n"
            "**REQUIRED FORMAT:**\n"
            "```xml\n"
            "<attempt_completion>\n"
            "<r>\n"
            "## Compliance Analysis for [Content Type]\n\n"
            "### Executive Summary\n"
            "[Your detailed analysis here...]\n"
            "</r>\n"
            "<tool_name>attempt_completion</tool_name>\n"
            "<task_detail>Final Compliance Analysis</task_detail>\n"
            "</attempt_completion>\n"
            "```\n\n"
            "**INSTRUCTIONS:**\n"
            "1. Copy the exact XML structure above\n"
            "2. Replace the content inside the `<r>` tags with your comprehensive analysis\n"
            "3. Include an Executive Summary with your key findings\n"
            "4. Analyze all visual elements systematically (colors, typography, layout, imagery, logo usage)\n"
            "5. For videos, examine key frames, transitions, audio elements, and text overlays\n"
            "6. Provide specific recommendations for any compliance issues\n\n"
            "This is the final step in the compliance analysis process. You must provide your complete analysis now."
        )
    elif model_type == "claude_3_7":
        # Claude 3.7 Sonnet works best with concise, clear instructions
        return (
            "### COMPLETION REQUIRED\n\n"
            "You must now finalize your compliance analysis using the attempt_completion tool.\n\n"
            "Use this exact format:\n"
            "```xml\n"
            "<attempt_completion>\n"
            "<r>\n"
            "## Compliance Analysis for [Content Type]\n\n"
            "### Executive Summary\n"
            "[Your detailed analysis here...]\n"
            "</r>\n"
            "<tool_name>attempt_completion</tool_name>\n"
            "<task_detail>Final Compliance Analysis</task_detail>\n"
            "</attempt_completion>\n"
            "```\n\n"
            "Include a thorough analysis of all visual elements, brand consistency, and compliance issues. Provide specific recommendations for any issues found. This is your final submission."
        )
    else:
        # Default format for other models
        return (
            "### ATTENTION: COMPLETION REQUIRED\n\n"
            "You have been analyzing this content for a while now. It's time to finalize your analysis.\n\n"
            "**CRITICAL INSTRUCTION:**\n"
            "You MUST use the attempt_completion tool now to provide your final comprehensive compliance analysis. "
            "This is required to complete the task. Do not continue with more analysis - summarize what you've found so far.\n\n"
            "**REQUIRED FORMAT:**\n"
            "```xml\n"
            "<attempt_completion>\n"
            "<r>\n"
            "## Compliance Analysis for [Content Type]\n\n"
            "### Executive Summary\n"
            "[Your detailed analysis here...]\n"
            "</r>\n"
            "<tool_name>attempt_completion</tool_name>\n"
            "<task_detail>Final Compliance Analysis</task_detail>\n"
            "</attempt_completion>\n"
            "```\n\n"
            "**STEP-BY-STEP INSTRUCTIONS:**\n"
            "1. Copy the exact XML structure above\n"
            "2. Replace the content inside the `<r>` tags with your compliance analysis\n"
            "3. Include an Executive Summary with your key findings\n"
            "4. Provide a detailed analysis based on the information you've gathered\n"
            "5. Make sure to include all required XML tags\n\n"
            "This is the final step in the compliance analysis process. You must provide your complete analysis now."
        )


# Add more prompt functions as needed for different scenarios
