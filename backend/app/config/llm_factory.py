import os
from dotenv import load_dotenv
from openai import OpenAI, AsyncOpenAI


# Load environment variables
load_dotenv(override=True)

OPENAI_ORG_ID = os.getenv("OPENAI_ORG_ID")
OPENAI_PROJECT_ID = os.getenv("OPENAI_PROJECT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# # Initialize OpenAI client
# client = OpenAI(
#     organization=OPENAI_ORG_ID, project=OPENAI_PROJECT_ID, api_key=OPENAI_API_KEY
# )

async_client = AsyncOpenAI(
    organization=OPENAI_ORG_ID, project=OPENAI_PROJECT_ID, api_key=OPENAI_API_KEY
)

# # MongoDB Options
# MONGO_OPTIONS = {"ssl": True, "retryWrites": True, "w": "majority"}

# # Allow invalid certificates for local development
# if os.getenv("ENVIRONMENT", "production").lower() == "local":
#     MONGO_OPTIONS["tlsAllowInvalidCertificates"] = True

# llm_models.py
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models.chat_models import BaseChatModel
from app.config.monitoring import langfuse_handler

from enum import Enum
from typing import Dict, List, Type, Any
import os


class LLMModel(str, Enum):
    GPT_4 = "gpt-4"
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    GEMINI_2_FLASH = "gemini-2.0-flash"
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GEMINI_2_5_PRO = "gemini-2.5-pro"   
    # You can add more later: CLAUDE = "claude", MISTRAL = "mistral", etc.


def force_tool_choice(model: LLMModel):
    if model in [LLMModel.GPT_4, LLMModel.GPT_4O, LLMModel.GPT_4O_MINI]:
        return "required"
    else:
        return "any"


class LLMFactory:
    use_handler = os.getenv("USE_HANDLER", "false").lower() == "true"
    
    @staticmethod
    def get_llm(model: LLMModel = LLMModel.GPT_4O_MINI, json_output=False, temperature=0,**kwargs) -> BaseChatModel:

        if model not in LLMModel:
            raise ValueError(f"Model '{model}' is not supported.")
        
        if json_output:
            kwargs["response_format"] = {"type": "json_object"}

        if model in  [LLMModel.GPT_4, LLMModel.GPT_4O, LLMModel.GPT_4O_MINI]:
            return ChatOpenAI(
                model=model,
                temperature=temperature,
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                organization=os.getenv("OPENAI_ORG_ID"),
                # project=os.getenv("OPENAI_PROJECT_ID"),
                callbacks=[langfuse_handler] if LLMFactory.use_handler else None,
                **kwargs
            )
        elif model in [LLMModel.GEMINI_2_FLASH, LLMModel.GEMINI_2_5_FLASH, LLMModel.GEMINI_2_5_PRO]: 
            return ChatGoogleGenerativeAI(
                model=model,
                temperature=temperature,
                google_api_key=os.getenv("GOOGLE_API_KEY"),
                callbacks=[langfuse_handler] if LLMFactory.use_handler else None,
                **kwargs
            )
        else:
            raise ValueError(f"Unsupported model: {model}")
    
    @staticmethod
    def get_llm_with_structured_output(model: LLMModel, output_schema: Type[Any], **kwargs):
        """
        Get LLM with structured output, using appropriate method based on provider.
        For Gemini/Google models: uses method="json_mode"
        For OpenAI models: uses default method
        """
        llm = LLMFactory.get_llm(model, **kwargs)
        
        # Check if it's a Google/Gemini model
        if model in [LLMModel.GEMINI_2_FLASH, LLMModel.GEMINI_2_5_FLASH, LLMModel.GEMINI_2_5_PRO]:
            return llm.with_structured_output(output_schema, method="json_mode")
        else:
            # For OpenAI models, don't specify method parameter
            return llm.with_structured_output(output_schema)