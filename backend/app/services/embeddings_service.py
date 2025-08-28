from google import genai
from google.genai.types import EmbedContentConfig
from google.oauth2 import service_account

from langchain_openai import OpenAIEmbeddings
from typing import List, Dict, Any, Union
from abc import ABC, abstractmethod
import os
import json
import asyncio

class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers"""
    
    @abstractmethod
    async def embed_documents(self, documents: List[str], **kwargs) -> List[List[float]]:
        pass
    
    @abstractmethod
    async def embed_query(self, query: str, **kwargs) -> List[float]:
        pass

class OpenAIProvider(EmbeddingProvider):
    """OpenAI embedding provider implementation"""
    
    def __init__(self, model: str = "text-embedding-3-small", dimensions: int = 1024, batch_size: int = 10, **kwargs):
        self.model = model
        self.dimensions = dimensions
        self.batch_size = batch_size
        self.embeddings = OpenAIEmbeddings(model=model, dimensions=dimensions, **kwargs)
    
    async def embed_documents(self, documents: List[str], **kwargs) -> List[List[float]]:
        return await self.embeddings.aembed_documents(documents)
    
    async def embed_query(self, query: str, **kwargs) -> List[float]:
        return await self.embeddings.aembed_query(query)

class GoogleProvider(EmbeddingProvider):
    """Google embedding provider implementation"""

    def __init__(self, model: str = "gemini-embedding-001", dimensions: int = 1024, batch_size: int = 10, **kwargs):
        self.model = model
        self.dimensions = dimensions
        self.batch_size = batch_size
        vertex_service_account = json.loads(os.getenv("VERTEX_SERVICE_ACCOUNT",{}))
        # print(vertex_service_account)
        self.credentials = service_account.Credentials.from_service_account_info(
            vertex_service_account,  
            scopes = ["https://www.googleapis.com/auth/cloud-platform"]
        )
        self.api_key = os.getenv("GOOGLE_API_KEY")

        self.client = genai.Client( api_key=os.getenv("GOOGLE_API_KEY"))
        if self.model == "gemini-embedding-001":
            self.client = genai.Client( 
                vertexai=True,
                project="magic-rfp-app-dev",
                location="global",
                credentials=self.credentials
            )


    async def embed_documents(
            self, 
            documents: List[str], 
            **kwargs) -> List[List[float]]:  
           
        embeddings = []
        
        if self.model == "gemini-embedding-001":
            for i in range(0, len(documents), self.batch_size):
                tasks = [self.client.aio.models.embed_content(
                    model=self.model,
                    contents=doc,
                    config=EmbedContentConfig(
                        task_type="RETRIEVAL_DOCUMENT",  
                        output_dimensionality=self.dimensions,  
                    )
                ) for doc in documents[i:i+self.batch_size]]
                responses = await asyncio.gather(*tasks)
                embeddings.extend([response.embeddings[0].values for response in responses])
        else:
            response = await self.client.aio.models.embed_content(
                model=self.model,
                contents=documents,
                config=EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT",  
                    output_dimensionality=self.dimensions,  
                )
            )
            for emd in response.embeddings:
                embeddings.append(emd.values)
        return embeddings
    
    async def embed_query(
            self, 
            query: str, 
            **kwargs) -> List[float]:
        response = await self.client.aio.models.embed_content(
            model=self.model,
            contents=query,
            config=EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",  
                output_dimensionality=self.dimensions,    
            )
        )
        return response.embeddings[0].values


class EmbeddingsService:
    """Service for generating embeddings using different providers"""
    
    # Provider mapping for easy extension
    PROVIDERS = {
        "openai": OpenAIProvider,
        "google": GoogleProvider
    }
    
    def __init__(self, provider: str = "openai", model: str = None, dimensions: int = 1024, batch_size: int = 10, **kwargs):
        self.provider_name = provider
        self.dimensions = dimensions
        
        # Set default models if not provided
        if not model:
            model = "text-embedding-3-small" if provider == "openai" else "gemini-embedding-001"
        
        # Initialize the appropriate provider
        provider_class = self.PROVIDERS.get(provider)
        if not provider_class:
            raise ValueError(f"Provider '{provider}' not supported. Available: {list(self.PROVIDERS.keys())}")
        
        self.provider = provider_class(model=model, dimensions=dimensions, batch_size=batch_size, **kwargs)
    
    async def embed_documents(self, documents: List[str], **kwargs) -> List[List[float]]:
        """Generate embeddings for a list of documents"""
        if not documents:
            return []
        return await self.provider.embed_documents(documents, **kwargs)
    
    async def embed_query(self, query: str, **kwargs) -> List[float]:

        """Generate embedding for a single query"""
        if not query:
            raise ValueError("Query cannot be empty")
        return await self.provider.embed_query(query, **kwargs)
    
    @classmethod
    def get_supported_providers(cls) -> List[str]:
        """Get list of supported embedding providers"""
        return list(cls.PROVIDERS.keys())
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the current provider configuration"""
        return {
            "provider": self.provider_name,
            "dimensions": self.dimensions,
            "provider_class": type(self.provider).__name__
        }
    