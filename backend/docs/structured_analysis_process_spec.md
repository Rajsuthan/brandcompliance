# Structured Analysis Process for Brand Compliance AI

## Overview

This document outlines a structured step-by-step analysis process for the Brand Compliance AI system. The goal is to improve consistency in analysis by enforcing a specific sequence of steps that the model must follow when analyzing compliance, rather than leaving it to the model's discretion.

## Implementation Strategy

We will modify the system prompt in the `prompt_manager.py` file to include a clear, sequential process that the model must follow. This will ensure that all analysis follows the same pattern, leading to more consistent and predictable results.

## Current Issues

- The existing implementation allows the model too much flexibility in deciding how to approach compliance analysis
- This can lead to inconsistent results, as the model might prioritize different elements in different analyses
- The sequence of checks can vary, making it difficult to predict and validate the model's behavior
- Different models may approach the analysis in significantly different ways

## Proposed Solution: Structured Analysis Framework

### Key Components

1. **Mandatory Sequential Process**: Define a specific sequence of steps that must be followed in order
2. **Strict Pattern Enforcement**: Require the model to complete each step before moving to the next
3. **Standardized Output Format**: Ensure results are presented in a consistent format
4. **Clear Decision Points**: Define explicit criteria for compliance decisions

## Technical Implementation

### Changes to `prompt_manager.py`

We will add a new `<structured_analysis_protocol>` section to the system prompt for all model types. This section will define the specific sequence of steps that the model must follow.

```python
def get_system_prompt(model_name: str) -> str:
    # Existing code...
    
    # Add structured analysis protocol to all model types
    structured_analysis_protocol = """
<structured_analysis_protocol>
# MANDATORY SEQUENCE OF STEPS FOR BRAND COMPLIANCE ANALYSIS

You MUST follow these exact steps in this precise order. Do not skip steps or change their order under any circumstances.

## STEP 1: BRAND GUIDELINES RESEARCH (MANDATORY FIRST STEP)
1. Identify which brand is being analyzed
2. Use search_brand_guidelines to locate relevant guideline sections
3. Read and document ALL relevant guideline pages for:
   - Logo usage rules (placement, size, clear space, color versions)
   - Typography requirements (fonts, sizes, weights)
   - Color palette specifications (primary/secondary colors, color codes)
   - Brand voice guidelines (tone, language style, terminology)
   - Do NOT proceed to Step 2 until you've thoroughly researched ALL relevant guidelines

## STEP 2: VISUAL ELEMENTS ANALYSIS (MANDATORY SECOND STEP)
1. Analyze logo usage:
   - Check logo placement against guidelines (use check_element_placement)
   - Verify logo size meets minimum requirements
   - Confirm proper clear space around logo
   - Verify correct logo version is used (color, orientation)
   - Check for ANY blurring, distortion, or manipulation (use check_image_clarity)
2. Analyze color usage:
   - Identify all colors used in the asset (use get_video_color_scheme or get_image_color_scheme)
   - Compare each color to the official brand color palette
   - Check for unauthorized colors or incorrect color codes
3. Analyze typography:
   - Identify all fonts used (use get_video_fonts or get_image_fonts)
   - Compare to required brand fonts
   - Check font weights, sizes, and styles against guidelines
   - Do NOT proceed to Step 3 until ALL visual elements have been analyzed

## STEP 3: TEXT CONTENT ANALYSIS (MANDATORY THIRD STEP)
1. Extract all text content from the asset (dialogue, captions, on-screen text)
   - For images: use extract_text_from_image
   - For videos: analyze text at multiple timestamps
2. Check for spelling and grammatical errors (use check_text_grammar)
   - Flag ANY errors, no matter how minor
3. Analyze brand voice compliance:
   - Compare text content to brand voice guidelines
   - Check terminology usage against approved brand language
   - Analyze tone consistency with brand personality
   - Do NOT proceed to Step 4 until ALL text has been analyzed

## STEP 4: COMPREHENSIVE DOCUMENTATION (MANDATORY FOURTH STEP)
1. Document ALL findings from Steps 1-3 in detail
2. For each element checked, include:
   - Exact guideline reference (page number and quoted text)
   - Specific evidence of compliance or non-compliance
   - Severity assessment (High/Medium/Low)
3. Organize findings by category (Logo, Typography, Color, Text, etc.)
4. Include specific timestamps or coordinates for each issue
   - Do NOT proceed to Step 5 until ALL findings are documented

## STEP 5: FINAL VERDICT FORMULATION (MANDATORY FIFTH STEP)
1. Review ALL documented findings
2. Assess overall compliance status based on severity and number of issues:
   - ✅ Compliant: No issues found
   - ⚠️ Minor Issues: Only low-severity issues found
   - ❌ Major Issues: One or more medium/high-severity issues found
   - ❌ Non-Compliant: Multiple high-severity issues found
3. Provide comprehensive reasoning for the verdict
4. Rank issues by priority for remediation
5. Suggest specific corrections for each issue

YOU MUST COMPLETE ALL STEPS IN THIS EXACT ORDER. DO NOT SKIP ANY STEPS OR CHANGE THEIR SEQUENCE.
</structured_analysis_protocol>
    """
    
    # Add structured protocol to each model's prompt
    if model_type == "llama":
        llama_prompt = """..."""
        return llama_prompt + structured_analysis_protocol
    elif model_type == "claude_3_5" or model_type == "claude_3_7":
        claude_prompt = """..."""
        return claude_prompt + structured_analysis_protocol
    else:  # default
        default_prompt = """..."""
        return default_prompt + structured_analysis_protocol
```

### Changes to Output Format

We will also enforce a standard output format that aligns with the step-by-step process.

```markdown
# Brand Compliance Analysis for [Asset Name/Description]

## Executive Summary
Overall Compliance Status: [✅ Compliant / ⚠️ Minor Issues / ❌ Major Issues / ❌ Non-Compliant]
[Brief summary of most critical findings]

## Step 1: Brand Guidelines Research Summary
- Guidelines Version: [Version/Date of brand guidelines]
- Pages Reviewed: [List of specific page numbers reviewed]
- Key Requirements Identified:
  - Logo: [Summary of logo requirements]
  - Typography: [Summary of typography requirements]
  - Color: [Summary of color requirements]
  - Brand Voice: [Summary of voice requirements]

## Step 2: Visual Elements Analysis
### Logo Usage
- Status: [✅ / ⚠️ / ❌]
- Issues Found: [List specific issues]
- Guideline Reference: [Page numbers and quoted text]
- Evidence: [Specific details with timestamps/coordinates]

### Color Usage
- Status: [✅ / ⚠️ / ❌]
- Colors Identified: [List colors with codes]
- Issues Found: [List specific issues]
- Guideline Reference: [Page numbers and quoted text]

### Typography
- Status: [✅ / ⚠️ / ❌]
- Fonts Identified: [List fonts used]
- Issues Found: [List specific issues]
- Guideline Reference: [Page numbers and quoted text]

## Step 3: Text Content Analysis
### Spelling and Grammar
- Status: [✅ / ⚠️ / ❌]
- Issues Found: [List specific errors]
- Location: [Timestamps/coordinates]

### Brand Voice
- Status: [✅ / ⚠️ / ❌]
- Voice Guidelines Reviewed: [List sections]
- Issues Found: [List specific voice issues]
- Guideline Reference: [Page numbers and quoted text]
- Evidence: [Direct quotes with analysis]

## Step 4: Comprehensive Documentation
[Complete documentation of all findings organized by category]

## Step 5: Final Verdict and Recommendations
### Overall Compliance Verdict
[Detailed reasoning for final compliance status]

### Prioritized Remediation Plan
1. [High Priority] [Specific correction needed]
2. [Medium Priority] [Specific correction needed]
3. [Low Priority] [Specific correction needed]

### Implementation Guidance
[Specific suggestions for implementing corrections]
```

## Implementation Plan

### Phase 1: System Prompt Update

1. Modify `prompt_manager.py` to include the structured analysis protocol
2. Test the updated prompt with various model types to ensure compatibility
3. Refine the protocol based on initial testing results

### Phase 2: Tool Integration

1. Ensure all tools referenced in the structured process are properly implemented
2. Update tool documentation to align with the structured process
3. Add any missing tools required for the structured analysis

### Phase 3: Testing and Validation

1. Create test cases for different brands and asset types
2. Validate that the model follows the exact sequence for all test cases
3. Compare results before and after implementation to measure consistency improvement
4. Analyze any deviations from the expected process

### Phase 4: Refinement and Optimization

1. Identify any bottlenecks or inefficiencies in the structured process
2. Optimize the sequence without compromising consistency
3. Add additional model-specific adjustments if needed

## Success Metrics

1. **Process Adherence**: 100% of analyses follow the exact structured sequence
2. **Result Consistency**: >95% consistency in compliance verdicts for identical assets
3. **Comprehensive Coverage**: All required elements are analyzed in every assessment
4. **Documentation Quality**: Detailed documentation for every element with specific references
5. **Temporal Stability**: Consistent results over time and across different sessions

## Potential Challenges and Mitigations

1. **Challenge**: Increased token usage due to more verbose instructions
   - **Mitigation**: Optimize prompt wording for clarity while minimizing length

2. **Challenge**: Reduced flexibility for edge cases
   - **Mitigation**: Include escape hatches for truly exceptional scenarios while maintaining the core structure

3. **Challenge**: Model resistance to following exact sequence
   - **Mitigation**: Reinforce sequence importance through prompt design and potentially add sequence verification tools

## Timeline

- Phase 1 (System Prompt Update): 3 days
- Phase 2 (Tool Integration): 2 days
- Phase 3 (Testing and Validation): 5 days
- Phase 4 (Refinement and Optimization): 5 days

Total Implementation Time: 15 days

## Conclusion

Implementing a structured analysis process will significantly improve the consistency and predictability of the Brand Compliance AI system. By enforcing a specific sequence of steps and standardized output format, we can ensure that all analyses follow the same thorough approach, leading to more reliable results across different brands, assets, and model types.
