from typing import Dict, Type
from .base import OCRProvider
from .mistral import MistralOCRProvider

class OCRProviderFactory:
    """Factory class for creating OCR providers"""
    
    _providers: Dict[str, Type[OCRProvider]] = {
        "mistral": MistralOCRProvider,
        # Add more providers here as they are implemented
    }
    
    @classmethod
    def get_provider(cls, provider_name: str, **kwargs) -> OCRProvider:
        """
        Get an OCR provider instance
        
        Args:
            provider_name: Name of the provider to get
            **kwargs: Additional arguments to pass to the provider constructor
            
        Returns:
            An instance of the requested OCR provider
            
        Raises:
            ValueError: If the provider is not supported
        """
        provider_class = cls._providers.get(provider_name.lower())
        if not provider_class:
            raise ValueError(f"Unsupported OCR provider: {provider_name}")
        
        return provider_class(**kwargs)
    
    @classmethod
    def register_provider(cls, name: str, provider_class: Type[OCRProvider]):
        """
        Register a new OCR provider
        
        Args:
            name: Name of the provider
            provider_class: Provider class that implements OCRProvider
        """
        cls._providers[name.lower()] = provider_class 