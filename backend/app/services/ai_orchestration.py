"""
AI Orchestration Layer - Light wrapper around LLM providers with modular architecture
"""
import os
from typing import Optional, Dict, Any, List, Union, AsyncGenerator
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import logging

# Provider-specific imports
try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    GEMINI = "gemini"
    OPENAI = "openai"


@dataclass
class ChatMessage:
    """Unified message format across providers"""
    role: str  # "user", "assistant", "system"
    content: str


@dataclass
class ChatResponse:
    """Unified response format across providers"""
    content: str
    provider: str
    model: str
    usage: Optional[Dict[str, Any]] = None


class BaseLLMClient(ABC):
    """Base class for LLM provider clients"""
    
    def __init__(self, api_key: str, model: str = None):
        self.api_key = api_key
        self.model = model
        
    @abstractmethod
    async def chat_completion(
        self, 
        messages: List[ChatMessage], 
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ChatResponse:
        """Generate a chat completion"""
        pass
    
    @abstractmethod
    async def stream_chat_completion(
        self, 
        messages: List[ChatMessage], 
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream a chat completion"""
        pass


class GeminiClient(BaseLLMClient):
    """Google Gemini client implementation"""
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        super().__init__(api_key, model)
        if genai is None:
            raise ImportError("google-generativeai package is required for Gemini")
        
        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel(model)
        
    def _convert_messages_to_gemini_format(self, messages: List[ChatMessage]) -> List[Dict[str, str]]:
        """Convert unified messages to Gemini format"""
        gemini_messages = []
        for msg in messages:
            # Gemini uses "user" and "model" roles
            role = "model" if msg.role == "assistant" else "user"
            gemini_messages.append({
                "role": role,
                "parts": [{"text": msg.content}]
            })
        return gemini_messages
    
    async def chat_completion(
        self, 
        messages: List[ChatMessage], 
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ChatResponse:
        """Generate a chat completion using Gemini"""
        try:
            # Configure generation
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            
            # For single prompt, use the content directly
            if len(messages) == 1:
                response = await self.client.generate_content_async(
                    messages[0].content,
                    generation_config=generation_config
                )
            else:
                # For chat, we need to format properly
                chat_messages = self._convert_messages_to_gemini_format(messages)
                response = await self.client.generate_content_async(
                    chat_messages,
                    generation_config=generation_config
                )
            
            return ChatResponse(
                content=response.text,
                provider="gemini",
                model=self.model,
                usage={
                    "prompt_tokens": response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
                    "completion_tokens": response.usage_metadata.candidates_token_count if response.usage_metadata else 0,
                    "total_tokens": response.usage_metadata.total_token_count if response.usage_metadata else 0,
                }
            )
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise
    
    async def stream_chat_completion(
        self, 
        messages: List[ChatMessage], 
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream a chat completion using Gemini"""
        try:
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            
            if len(messages) == 1:
                response = await self.client.generate_content_async(
                    messages[0].content,
                    generation_config=generation_config,
                    stream=True
                )
            else:
                chat_messages = self._convert_messages_to_gemini_format(messages)
                response = await self.client.generate_content_async(
                    chat_messages,
                    generation_config=generation_config,
                    stream=True
                )
            
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            logger.error(f"Gemini streaming error: {e}")
            raise


class OpenAIClient(BaseLLMClient):
    """OpenAI client implementation"""
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        super().__init__(api_key, model)
        if AsyncOpenAI is None:
            raise ImportError("openai package is required for OpenAI")
        
        self.client = AsyncOpenAI(api_key=api_key)
    
    def _convert_messages_to_openai_format(self, messages: List[ChatMessage]) -> List[Dict[str, str]]:
        """Convert unified messages to OpenAI format"""
        return [{"role": msg.role, "content": msg.content} for msg in messages]
    
    async def chat_completion(
        self, 
        messages: List[ChatMessage], 
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ChatResponse:
        """Generate a chat completion using OpenAI"""
        try:
            openai_messages = self._convert_messages_to_openai_format(messages)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            return ChatResponse(
                content=response.choices[0].message.content,
                provider="openai",
                model=self.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
            )
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    async def stream_chat_completion(
        self, 
        messages: List[ChatMessage], 
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream a chat completion using OpenAI"""
        try:
            openai_messages = self._convert_messages_to_openai_format(messages)
            
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            raise


class AIOrchestrator:
    """Main orchestration class for LLM operations"""
    
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "gemini").lower()
        self.client = self._create_client()
    
    def _create_client(self) -> BaseLLMClient:
        """Create appropriate LLM client based on configuration"""
        if self.provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable is required")
            return GeminiClient(api_key)
        
        elif self.provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required")
            return OpenAIClient(api_key)
        
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
    
    async def chat_completion(
        self, 
        messages: Union[List[ChatMessage], str], 
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ChatResponse:
        """Generate a chat completion"""
        if isinstance(messages, str):
            messages = [ChatMessage(role="user", content=messages)]
        
        return await self.client.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    
    async def stream_chat_completion(
        self, 
        messages: Union[List[ChatMessage], str], 
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream a chat completion"""
        if isinstance(messages, str):
            messages = [ChatMessage(role="user", content=messages)]
        
        async for chunk in self.client.stream_chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        ):
            yield chunk
    
    def switch_provider(self, provider: str, api_key: str = None) -> None:
        """Switch to a different LLM provider at runtime"""
        if api_key:
            os.environ[f"{provider.upper()}_API_KEY"] = api_key
        
        self.provider = provider.lower()
        self.client = self._create_client()


# Global orchestrator instance
_orchestrator = None

def get_ai_orchestrator() -> AIOrchestrator:
    """Get or create the global AI orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AIOrchestrator()
    return _orchestrator


# Convenience functions for common operations
async def chat_completion(prompt: str, **kwargs) -> str:
    """Simple chat completion with string prompt"""
    orchestrator = get_ai_orchestrator()
    response = await orchestrator.chat_completion(prompt, **kwargs)
    return response.content


async def stream_chat(prompt: str, **kwargs) -> AsyncGenerator[str, None]:
    """Simple streaming chat with string prompt"""
    orchestrator = get_ai_orchestrator()
    async for chunk in orchestrator.stream_chat_completion(prompt, **kwargs):
        yield chunk

