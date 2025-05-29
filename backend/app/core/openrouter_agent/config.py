# Constants for timeout settings
OPENROUTER_TIMEOUT = 120  # 2 minutes timeout for OpenRouter API calls

# Fallback models to try when the primary model fails
FALLBACK_MODELS = [
    "openai/gpt-4o",
    "openai/o3-mini",
    # "google/gemini-2.5-pro-preview-03-25",
    "cohere/command-r-08-2024",
    "openai/gpt-4o"
]

# Define analysis sections for multi-step report generation
ANALYSIS_SECTIONS = [
    {
        "id": "initial_assessment",
        "title": "Initial Assessment",
        "instruction": "Analyze the overall compliance of the asset with brand guidelines. Focus on identifying any immediate or obvious compliance issues."
    },
    {
        "id": "brand_voice_analysis",
        "title": "Brand Voice Analysis",
        "instruction": "Evaluate the brand voice and messaging. Check for tone, language, and messaging consistency with brand guidelines."
    },
    {
        "id": "visual_identity_verification",
        "title": "Visual Identity Verification",
        "instruction": "Verify visual elements including logos, colors, typography, and imagery. Ensure they match brand standards."
    },
    {
        "id": "legal_regulatory_checks",
        "title": "Legal & Regulatory Checks",
        "instruction": "Check for legal disclaimers, copyright information, and regulatory compliance specific to the industry."
    },
    {
        "id": "technical_validation",
        "title": "Technical Validation",
        "instruction": "Verify technical aspects like image resolution, file formats, and accessibility compliance."
    },
    {
        "id": "content_verification",
        "title": "Content Verification",
        "instruction": "Check content accuracy, grammar, spelling, and alignment with brand messaging."
    },
    {
        "id": "final_synthesis",
        "title": "Final Synthesis",
        "instruction": "Synthesize findings from all sections into a cohesive summary. Provide an overall compliance status and key recommendations."
    }
]
