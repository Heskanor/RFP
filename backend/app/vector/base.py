"""
Base vector store interface
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class VectorDocument:
    """Document with vector embedding"""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None

@dataclass
class SearchResult:
    """Vector search result"""
    id: str
    content: str
    metadata: Dict[str, Any]
    score: float

class BaseVectorStore(ABC):
    """Abstract base class for vector stores"""
    
    @abstractmethod
    async def connect(self) -> None:
        """Connect to vector store"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from vector store"""
        pass
    
    @abstractmethod
    async def create_collection(self, name: str, dimension: int = 1536) -> None:
        """Create a new collection/index"""
        pass
    
    @abstractmethod
    async def delete_collection(self, name: str) -> None:
        """Delete a collection/index"""
        pass
    
    @abstractmethod
    async def upsert_documents(
        self, 
        collection: str, 
        documents: List[VectorDocument]
    ) -> None:
        """Insert or update documents"""
        pass
    
    @abstractmethod
    async def search(
        self,
        collection: str,
        query_vector: List[float],
        limit: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Search for similar vectors"""
        pass
    
    @abstractmethod
    async def delete_documents(
        self,
        collection: str,
        document_ids: List[str]
    ) -> None:
        """Delete documents by ID"""
        pass
    
    @abstractmethod
    async def get_document(
        self,
        collection: str,
        document_id: str
    ) -> Optional[VectorDocument]:
        """Get a specific document"""
        pass
    
    @abstractmethod
    async def list_collections(self) -> List[str]:
        """List all collections"""
        pass
    
    @abstractmethod
    async def get_collection_stats(self, collection: str) -> Dict[str, Any]:
        """Get collection statistics"""
        pass

