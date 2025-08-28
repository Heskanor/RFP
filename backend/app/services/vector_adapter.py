"""
Pluggable Vector Search Adapter - Default pgvector, optional Pinecone
"""
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import uuid
import asyncio

# Vector database imports
try:
    import psycopg2
    from pgvector.psycopg2 import register_vector
except ImportError:
    psycopg2 = None
    register_vector = None

try:
    from pinecone import Pinecone, Index
except ImportError:
    Pinecone = None
    Index = None

logger = logging.getLogger(__name__)


class VectorBackend(Enum):
    PGVECTOR = "pgvector"
    PINECONE = "pinecone"


@dataclass
class VectorDocument:
    """Unified document format for vector operations"""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None


@dataclass
class VectorSearchResult:
    """Unified search result format"""
    id: str
    content: str
    metadata: Dict[str, Any]
    score: float


class BaseVectorStore(ABC):
    """Base class for vector store implementations"""
    
    def __init__(self, **kwargs):
        self.embedding_dimension = kwargs.get("embedding_dimension", 1536)  # Default OpenAI embedding size
    
    @abstractmethod
    async def connect(self) -> None:
        """Connect to the vector store"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the vector store"""
        pass
    
    @abstractmethod
    async def create_collection(self, collection_name: str, **kwargs) -> None:
        """Create a new collection/index"""
        pass
    
    @abstractmethod
    async def upsert_documents(self, collection_name: str, documents: List[VectorDocument]) -> None:
        """Insert or update documents in the collection"""
        pass
    
    @abstractmethod
    async def search(
        self, 
        collection_name: str, 
        query_embedding: List[float], 
        top_k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        """Search for similar vectors"""
        pass
    
    @abstractmethod
    async def delete_documents(self, collection_name: str, document_ids: List[str]) -> None:
        """Delete documents by ID"""
        pass


class PgVectorStore(BaseVectorStore):
    """PostgreSQL with pgvector extension implementation"""
    
    def __init__(self, connection_string: str, **kwargs):
        super().__init__(**kwargs)
        if psycopg2 is None:
            raise ImportError("psycopg2-binary and pgvector packages are required for pgvector")
        
        self.connection_string = connection_string
        self.connection = None
    
    async def connect(self) -> None:
        """Connect to PostgreSQL database"""
        try:
            # For async operations, we'll use a connection pool in production
            # For now, using sync psycopg2 in thread executor
            loop = asyncio.get_event_loop()
            self.connection = await loop.run_in_executor(
                None, 
                psycopg2.connect, 
                self.connection_string
            )
            
            # Register pgvector extension
            register_vector(self.connection)
            
            # Create extension if not exists
            cursor = self.connection.cursor()
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            self.connection.commit()
            cursor.close()
            
            logger.info("Connected to PostgreSQL with pgvector")
            
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from PostgreSQL"""
        if self.connection:
            self.connection.close()
            logger.info("Disconnected from PostgreSQL")
    
    async def create_collection(self, collection_name: str, **kwargs) -> None:
        """Create a new table for storing vectors"""
        try:
            cursor = self.connection.cursor()
            
            # Create table with vector column
            create_table_query = f"""
            CREATE TABLE IF NOT EXISTS {collection_name} (
                id TEXT PRIMARY KEY,
                content TEXT,
                metadata JSONB,
                embedding VECTOR({self.embedding_dimension})
            );
            """
            
            cursor.execute(create_table_query)
            
            # Create index for better search performance
            create_index_query = f"""
            CREATE INDEX IF NOT EXISTS {collection_name}_embedding_idx 
            ON {collection_name} USING ivfflat (embedding vector_cosine_ops) 
            WITH (lists = 100);
            """
            
            cursor.execute(create_index_query)
            self.connection.commit()
            cursor.close()
            
            logger.info(f"Created collection: {collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            raise
    
    async def upsert_documents(self, collection_name: str, documents: List[VectorDocument]) -> None:
        """Insert or update documents"""
        try:
            cursor = self.connection.cursor()
            
            for doc in documents:
                if not doc.embedding:
                    raise ValueError(f"Document {doc.id} missing embedding")
                
                upsert_query = f"""
                INSERT INTO {collection_name} (id, content, metadata, embedding)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    content = EXCLUDED.content,
                    metadata = EXCLUDED.metadata,
                    embedding = EXCLUDED.embedding;
                """
                
                cursor.execute(upsert_query, (
                    doc.id,
                    doc.content,
                    psycopg2.extras.Json(doc.metadata),
                    doc.embedding
                ))
            
            self.connection.commit()
            cursor.close()
            
            logger.info(f"Upserted {len(documents)} documents to {collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to upsert documents: {e}")
            raise
    
    async def search(
        self, 
        collection_name: str, 
        query_embedding: List[float], 
        top_k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        """Search for similar vectors using cosine similarity"""
        try:
            cursor = self.connection.cursor()
            
            # Build query with optional metadata filtering
            where_clause = ""
            params = [query_embedding, top_k]
            
            if filter_metadata:
                where_conditions = []
                for key, value in filter_metadata.items():
                    where_conditions.append(f"metadata->>{%s} = %s")
                    params.extend([key, str(value)])
                
                where_clause = "WHERE " + " AND ".join(where_conditions)
            
            search_query = f"""
            SELECT id, content, metadata, 1 - (embedding <=> %s) as score
            FROM {collection_name}
            {where_clause}
            ORDER BY embedding <=> %s
            LIMIT %s;
            """
            
            # Adjust params order for the query
            query_params = [query_embedding] + params[2:] + [query_embedding, top_k]
            
            cursor.execute(search_query, query_params)
            results = cursor.fetchall()
            cursor.close()
            
            return [
                VectorSearchResult(
                    id=row[0],
                    content=row[1],
                    metadata=row[2],
                    score=row[3]
                )
                for row in results
            ]
            
        except Exception as e:
            logger.error(f"Failed to search vectors: {e}")
            raise
    
    async def delete_documents(self, collection_name: str, document_ids: List[str]) -> None:
        """Delete documents by ID"""
        try:
            cursor = self.connection.cursor()
            
            delete_query = f"DELETE FROM {collection_name} WHERE id = ANY(%s);"
            cursor.execute(delete_query, (document_ids,))
            
            self.connection.commit()
            cursor.close()
            
            logger.info(f"Deleted {len(document_ids)} documents from {collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            raise


class PineconeVectorStore(BaseVectorStore):
    """Pinecone vector database implementation"""
    
    def __init__(self, api_key: str, index_name: str, **kwargs):
        super().__init__(**kwargs)
        if Pinecone is None:
            raise ImportError("pinecone-client package is required for Pinecone")
        
        self.api_key = api_key
        self.index_name = index_name
        self.pinecone_client = None
        self.index = None
    
    async def connect(self) -> None:
        """Connect to Pinecone"""
        try:
            self.pinecone_client = Pinecone(api_key=self.api_key)
            
            # Check if index exists, create if not
            if self.index_name not in self.pinecone_client.list_indexes().names():
                logger.warning(f"Index {self.index_name} does not exist. Creating it...")
                await self.create_collection(self.index_name)
            
            self.index = self.pinecone_client.Index(self.index_name)
            logger.info(f"Connected to Pinecone index: {self.index_name}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Pinecone: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from Pinecone (no explicit disconnect needed)"""
        logger.info("Disconnected from Pinecone")
    
    async def create_collection(self, collection_name: str, **kwargs) -> None:
        """Create a new Pinecone index"""
        try:
            self.pinecone_client.create_index(
                name=collection_name,
                dimension=self.embedding_dimension,
                metric="cosine",
                spec={
                    "serverless": {
                        "cloud": "aws",
                        "region": "us-east-1"
                    }
                }
            )
            logger.info(f"Created Pinecone index: {collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to create Pinecone index {collection_name}: {e}")
            raise
    
    async def upsert_documents(self, collection_name: str, documents: List[VectorDocument]) -> None:
        """Insert or update documents in Pinecone"""
        try:
            vectors = []
            for doc in documents:
                if not doc.embedding:
                    raise ValueError(f"Document {doc.id} missing embedding")
                
                vectors.append({
                    "id": doc.id,
                    "values": doc.embedding,
                    "metadata": {
                        **doc.metadata,
                        "content": doc.content  # Store content in metadata
                    }
                })
            
            # Upsert in batches of 100 (Pinecone limit)
            batch_size = 100
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                self.index.upsert(vectors=batch)
            
            logger.info(f"Upserted {len(documents)} documents to Pinecone")
            
        except Exception as e:
            logger.error(f"Failed to upsert documents to Pinecone: {e}")
            raise
    
    async def search(
        self, 
        collection_name: str, 
        query_embedding: List[float], 
        top_k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        """Search for similar vectors in Pinecone"""
        try:
            # Build filter for Pinecone
            pinecone_filter = None
            if filter_metadata:
                pinecone_filter = {}
                for key, value in filter_metadata.items():
                    pinecone_filter[key] = {"$eq": value}
            
            response = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                filter=pinecone_filter,
                include_metadata=True
            )
            
            results = []
            for match in response.matches:
                metadata = match.metadata or {}
                content = metadata.pop("content", "")  # Extract content from metadata
                
                results.append(VectorSearchResult(
                    id=match.id,
                    content=content,
                    metadata=metadata,
                    score=match.score
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to search Pinecone: {e}")
            raise
    
    async def delete_documents(self, collection_name: str, document_ids: List[str]) -> None:
        """Delete documents from Pinecone"""
        try:
            self.index.delete(ids=document_ids)
            logger.info(f"Deleted {len(document_ids)} documents from Pinecone")
            
        except Exception as e:
            logger.error(f"Failed to delete documents from Pinecone: {e}")
            raise


class VectorAdapter:
    """Main adapter class for vector operations"""
    
    def __init__(self):
        self.backend = os.getenv("VECTOR_BACKEND", "pgvector").lower()
        self.store = self._create_vector_store()
        self._connected = False
    
    def _create_vector_store(self) -> BaseVectorStore:
        """Create appropriate vector store based on configuration"""
        if self.backend == "pgvector":
            db_url = os.getenv("SUPABASE_DB_URL")
            if not db_url:
                raise ValueError("SUPABASE_DB_URL environment variable is required for pgvector")
            return PgVectorStore(db_url)
        
        elif self.backend == "pinecone":
            api_key = os.getenv("PINECONE_API_KEY")
            index_name = os.getenv("PINECONE_INDEX", "rfp-buyer")
            if not api_key:
                raise ValueError("PINECONE_API_KEY environment variable is required for Pinecone")
            return PineconeVectorStore(api_key, index_name)
        
        else:
            raise ValueError(f"Unsupported vector backend: {self.backend}")
    
    async def connect(self) -> None:
        """Connect to the vector store"""
        if not self._connected:
            await self.store.connect()
            self._connected = True
    
    async def disconnect(self) -> None:
        """Disconnect from the vector store"""
        if self._connected:
            await self.store.disconnect()
            self._connected = False
    
    async def ensure_connected(self) -> None:
        """Ensure connection is established"""
        if not self._connected:
            await self.connect()
    
    async def create_collection(self, collection_name: str, **kwargs) -> None:
        """Create a new collection"""
        await self.ensure_connected()
        await self.store.create_collection(collection_name, **kwargs)
    
    async def upsert_documents(self, collection_name: str, documents: List[VectorDocument]) -> None:
        """Insert or update documents"""
        await self.ensure_connected()
        await self.store.upsert_documents(collection_name, documents)
    
    async def search(
        self, 
        collection_name: str, 
        query_embedding: List[float], 
        top_k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        """Search for similar vectors"""
        await self.ensure_connected()
        return await self.store.search(collection_name, query_embedding, top_k, filter_metadata)
    
    async def delete_documents(self, collection_name: str, document_ids: List[str]) -> None:
        """Delete documents"""
        await self.ensure_connected()
        await self.store.delete_documents(collection_name, document_ids)
    
    def get_backend_info(self) -> Dict[str, str]:
        """Get information about the current backend"""
        return {
            "backend": self.backend,
            "store_type": type(self.store).__name__,
            "connected": self._connected
        }


# Global adapter instance
_vector_adapter = None

def get_vector_adapter() -> VectorAdapter:
    """Get or create the global vector adapter instance"""
    global _vector_adapter
    if _vector_adapter is None:
        _vector_adapter = VectorAdapter()
    return _vector_adapter


# Convenience functions
async def search_documents(
    collection_name: str,
    query_embedding: List[float],
    top_k: int = 10,
    filter_metadata: Optional[Dict[str, Any]] = None
) -> List[VectorSearchResult]:
    """Simple document search"""
    adapter = get_vector_adapter()
    return await adapter.search(collection_name, query_embedding, top_k, filter_metadata)


async def store_documents(collection_name: str, documents: List[VectorDocument]) -> None:
    """Simple document storage"""
    adapter = get_vector_adapter()
    await adapter.upsert_documents(collection_name, documents)

