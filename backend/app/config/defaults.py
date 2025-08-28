"""
Default configuration for RFP Buyer API
"""
import os
from app.config.llm_factory import LLMModel

# Default LLM Configuration - Using Gemini as primary
DEFAULT_LLM_MODEL = LLMModel.GEMINI_2_5_FLASH  # Fast and cost-effective
DEFAULT_LLM_TEMPERATURE = 0.1  # Slightly creative but mostly deterministic

# Alternative models for different use cases
MODELS_CONFIG = {
    "default": LLMModel.GEMINI_2_5_FLASH,      # General use
    "analysis": LLMModel.GEMINI_2_5_PRO,       # Complex analysis tasks
    "chat": LLMModel.GEMINI_2_5_FLASH,         # User interactions
    "extraction": LLMModel.GEMINI_2_5_FLASH,   # Document processing
    "scoring": LLMModel.GEMINI_2_5_PRO,        # Vendor evaluation
    "summarization": LLMModel.GEMINI_2_5_FLASH, # RFP summaries
}

# Fallback to OpenAI if Gemini is not available
FALLBACK_MODEL = LLMModel.GPT_4O_MINI

def get_model_for_task(task: str = "default") -> LLMModel:
    """Get the appropriate model for a specific task."""
    return MODELS_CONFIG.get(task, DEFAULT_LLM_MODEL)

def is_gemini_available() -> bool:
    """Check if Gemini API key is configured."""
    return bool(os.getenv("GOOGLE_API_KEY"))

def is_openai_available() -> bool:
    """Check if OpenAI API key is configured."""
    return bool(os.getenv("OPENAI_API_KEY"))

def get_available_model(preferred_task: str = "default") -> LLMModel:
    """Get an available model, falling back if needed."""
    preferred_model = get_model_for_task(preferred_task)
    
    # Check if preferred model's provider is available
    if preferred_model.value.startswith("gemini") and is_gemini_available():
        return preferred_model
    elif preferred_model.value.startswith("gpt") and is_openai_available():
        return preferred_model
    
    # Fallback logic
    if is_gemini_available():
        return DEFAULT_LLM_MODEL
    elif is_openai_available():
        return FALLBACK_MODEL
    else:
        raise ValueError("No AI API keys configured. Please set GOOGLE_API_KEY or OPENAI_API_KEY")
