"""
Vector store factory for creating appropriate implementation
"""
import os
import logging
from typing import Optional
from .base import BaseVectorStore
from .pgvector_store import PgVectorStore
from .pinecone_store import PineconeStore

logger = logging.getLogger(__name__)

# Global vector store instance
_vector_store: Optional[BaseVectorStore] = None

def get_vector_store() -> BaseVectorStore:
    """Get or create vector store based on environment configuration"""
    global _vector_store
    
    if _vector_store is None:
        _vector_store = create_vector_store()
    
    return _vector_store

def create_vector_store() -> BaseVectorStore:
    """Create vector store based on VECTOR_BACKEND environment variable"""
    backend = os.getenv("VECTOR_BACKEND", "pgvector").lower()
    
    if backend == "pgvector":
        db_url = os.getenv("SUPABASE_DB_URL")
        if not db_url:
            raise ValueError("SUPABASE_DB_URL environment variable is required for pgvector")
        
        logger.info("Creating PgVector store")
        return PgVectorStore(db_url)
    
    elif backend == "pinecone":
        api_key = os.getenv("PINECONE_API_KEY")
        environment = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
        
        if not api_key:
            raise ValueError("PINECONE_API_KEY environment variable is required for Pinecone")
        
        logger.info("Creating Pinecone store")
        return PineconeStore(api_key, environment)
    
    else:
        raise ValueError(f"Unsupported vector backend: {backend}")

async def initialize_vector_store() -> None:
    """Initialize the vector store connection"""
    store = get_vector_store()
    await store.connect()
    logger.info(f"Vector store initialized: {type(store).__name__}")

async def cleanup_vector_store() -> None:
    """Cleanup vector store connections"""
    global _vector_store
    if _vector_store:
        await _vector_store.disconnect()
        _vector_store = None
        logger.info("Vector store cleaned up")

def get_vector_backend_info() -> dict:
    """Get information about current vector backend"""
    backend = os.getenv("VECTOR_BACKEND", "pgvector")
    store = get_vector_store()
    
    return {
        "backend": backend,
        "implementation": type(store).__name__,
        "connected": hasattr(store, 'pool') and store.pool is not None if hasattr(store, 'pool') else False
    }

# Convenience functions for common operations
async def search_documents(
    collection: str,
    query_vector: List[float],
    limit: int = 10,
    filter_metadata: Optional[Dict[str, Any]] = None
) -> List[SearchResult]:
    """Search documents across any vector backend"""
    store = get_vector_store()
    return await store.search(collection, query_vector, limit, filter_metadata)

async def store_documents(
    collection: str, 
    documents: List[VectorDocument]
) -> None:
    """Store documents in any vector backend"""
    store = get_vector_store()
    await store.upsert_documents(collection, documents)

async def ensure_collection_exists(collection: str, dimension: int = 1536) -> None:
    """Ensure collection exists in vector store"""
    store = get_vector_store()
    collections = await store.list_collections()
    
    if collection not in collections:
        await store.create_collection(collection, dimension)
        logger.info(f"Created collection: {collection}")

# Import here to avoid circular imports
from typing import List, Dict, Any
from .base import VectorDocument, SearchResult

