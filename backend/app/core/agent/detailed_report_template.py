"""
Improved detailed report template for brand compliance analysis.

This module provides an enhanced template for generating detailed, fact-based
compliance reports with specific examples and guidance.
"""

detailed_report_template = """
# Brand Compliance Analysis for {brand_name}

## Executive Summary
After thorough analysis of {asset_type} against {brand_name}'s official brand guidelines, this {asset_type} demonstrates **{compliance_status}** with several key brand standards. {summary_statement}

## Step 1: Brand Guidelines Research Summary
- Guidelines Version: {guidelines_version}
- Pages Reviewed: {pages_reviewed}
- Key Requirements Identified:
  - Logo: {logo_requirements}
  - Typography: {typography_requirements}
  - Color: {color_requirements}
  - Brand Voice: {voice_requirements}

## Step 2: Visual Elements Analysis
### Logo Usage
- Status: {logo_status}
- Issues Found: {logo_issues}
- Guideline Reference: {brand_name} Brand Guidelines pages {logo_pages}
- Evidence: {logo_evidence}

### Color Usage
- Status: {color_status}
- Colors Identified: {colors_identified}
- Issues Found: {color_issues}
- Guideline Reference: {brand_name} Brand Guidelines page {color_pages}

### Typography
- Status: {typography_status}
- Fonts Identified: {fonts_identified}
- Issues Found: {typography_issues}
- Guideline Reference: {brand_name} Brand Guidelines page {typography_pages}

## Step 3: Text Content Analysis
### Spelling and Grammar
- Status: {spelling_status}
- Issues Found: {spelling_issues}

### Brand Voice
- Status: {voice_status}
- Voice Guidelines Reviewed: Page {voice_pages}
- Issues Found: {voice_issues}
- Evidence: {voice_evidence}

## Step 4: Comprehensive Documentation
{comprehensive_documentation}

## Step 5: Final Verdict and Recommendations
### Overall Compliance Verdict
The {brand_name} {asset_type} demonstrates **{compliance_status}** with brand guidelines. {verdict_justification}

### Prioritized Remediation Plan
1. [{priority_1}] {issue_1}: {correction_1}
2. [{priority_2}] {issue_2}: {correction_2}
3. [{priority_3}] {issue_3}: {correction_3}

### Implementation Guidance
{implementation_guidance}
"""

# Example values for the template
example_values = {
    "brand_name": "Burger King",
    "asset_type": "TikTok video",
    "compliance_status": "⚠️ Partial Compliance",
    "summary_statement": "While the video showcases authentic product experiences that align with brand values, there are issues with typography, color application, and logo presentation that deviate from official guidelines.",
    
    "guidelines_version": "Burger King 2020 Brand Guidelines",
    "pages_reviewed": "15, 18, 31, 40, 54",
    "logo_requirements": "The Burger King logo must be presented clearly with proper spacing and in approved color formats",
    "typography_requirements": "Specific font families are required for all brand communications",
    "color_requirements": "Specific brand colors must be used consistently across all materials",
    "voice_requirements": "Authentic, conversational tone that showcases the product experience",
    
    "logo_status": "⚠️ Partially Compliant",
    "logo_issues": "The Burger King logo appears on packaging (fry container and drink cup) but is displayed in reverse/mirror image in some frames due to the selfie-style video format",
    "logo_pages": "15, 31",
    "logo_evidence": "The logo on packaging appears in frames 1, 2, 3, 5 with the \"BURGER KING\" text appearing in reverse in the selfie view",
    
    "color_status": "⚠️ Partially Compliant",
    "colors_identified": "Brand colors (red, orange, white) appear on packaging, but on-screen text uses non-standard orange (#9b5452) that doesn't match official brand palette",
    "color_issues": "Text overlay colors don't consistently match Burger King's official color palette",
    "color_pages": "40",
    
    "typography_status": "❌ Non-Compliant",
    "fonts_identified": "Morl Rounded Black, Kinesthesia Heavy",
    "typography_issues": "On-screen text uses non-approved fonts rather than the required brand typography",
    "typography_pages": "54",
    
    "spelling_status": "✅ Compliant",
    "spelling_issues": "No spelling or grammatical errors were identified in the on-screen text",
    
    "voice_status": "✅ Compliant",
    "voice_pages": "18",
    "voice_issues": "None identified",
    "voice_evidence": "Phrases like \"I love how these fries are fresh and salted\" and \"what should I try next from Burger King?\" demonstrate authentic product enthusiasm",
    
    "comprehensive_documentation": "The TikTok video features a user showcasing and reviewing Burger King products (fries and a burger) in a car setting. The video includes on-screen text narrating the experience with phrases like \"I asked the lady working there,\" \"and she said it was the fries,\" \"I love how these fries are fresh and salted,\" \"and it's got mayonnaise and yellow mustard,\" and concludes with \"what should I try next from Burger King?\"\n\nThe Burger King logo appears on the fry container and drink cup throughout the video. The packaging design is consistent with official Burger King products, featuring the correct logo and brand colors (red, orange, white). However, due to the selfie-style recording, the logo appears in reverse in some frames.\n\nThe on-screen text uses non-standard fonts (Morl Rounded Black and Kinesthesia Heavy) rather than Burger King's official typography. The text color is an orange-red shade (#9b5452) that doesn't precisely match Burger King's official color palette.\n\nThe content and tone of the video align with Burger King's brand voice guidelines, presenting an authentic user experience with the products. The positive product commentary (\"fresh and salted,\" \"it was really good I liked it\") supports the brand's focus on quality and taste.",
    
    "verdict_justification": "While the product presentation and brand voice are generally compliant, the typography and color usage deviate from official standards. The reversed logo presentation is a consequence of the user-generated content format rather than an intentional brand violation.",
    
    "priority_1": "Medium Priority",
    "issue_1": "Typography",
    "correction_1": "If this were an official Burger King-produced video, the on-screen text should use the approved brand fonts",
    
    "priority_2": "Medium Priority",
    "issue_2": "Color Usage",
    "correction_2": "Text overlay colors should match the official Burger King color palette",
    
    "priority_3": "Low Priority",
    "issue_3": "Logo Presentation",
    "correction_3": "Ensure logo is presented in the correct orientation in future official content",
    
    "implementation_guidance": "For user-generated content like this TikTok video, Burger King may choose to accept certain deviations from brand guidelines while ensuring that any official resharing or repurposing of the content includes proper disclaimers or modifications to align with brand standards.\n\nFor official content creation, Burger King should provide content creators with access to approved font files, color codes, and logo assets to ensure consistent brand presentation across all platforms, including social media.\n\nThe authentic product experience showcased in this video aligns well with Burger King's brand values and could be leveraged as part of a broader user-generated content strategy, with appropriate brand guideline accommodations for this content category."
}

def get_detailed_report_example():
    """
    Get an example of a detailed report using the template.
    
    Returns:
        A formatted detailed report example
    """
    return detailed_report_template.format(**example_values)

def get_detailed_report_template():
    """
    Get the detailed report template.
    
    Returns:
        The detailed report template as a string
    """
    return detailed_report_template
