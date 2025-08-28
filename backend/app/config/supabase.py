"""
Supabase Configuration - Postgres Database + Storage (no Supabase Auth)
"""
import os
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import asyncio

# Supabase imports
try:
    from supabase import create_client, Client
    from supabase.client import ClientOptions
except ImportError:
    create_client = None
    Client = None
    ClientOptions = None

# Direct PostgreSQL imports for advanced usage
try:
    import asyncpg
except ImportError:
    asyncpg = None

logger = logging.getLogger(__name__)


@dataclass
class SupabaseConfig:
    """Supabase configuration settings"""
    url: str
    anon_key: str
    service_role_key: Optional[str] = None
    db_url: str = ""
    storage_bucket: str = "rfp-files"


class SupabaseManager:
    """Supabase client manager for database and storage operations"""
    
    def __init__(self):
        self.config = self._load_config()
        self.client: Optional[Client] = None
        self.db_pool: Optional[asyncpg.Pool] = None
        self._initialized = False
    
    def _load_config(self) -> SupabaseConfig:
        """Load Supabase configuration from environment variables"""
        # Extract URL and key from database URL for Supabase client
        db_url = os.getenv("SUPABASE_DB_URL")
        if not db_url:
            raise ValueError("SUPABASE_DB_URL environment variable is required")
        
        # Parse Supabase URL from database URL
        # Format: postgresql://postgres.project_ref:password@aws-0-region.pooler.supabase.com:port/postgres
        if "supabase.com" in db_url:
            # Extract project reference from URL
            url_parts = db_url.split("@")[1].split(".")
            project_ref = url_parts[0].split("-")[-1] if len(url_parts) > 1 else "unknown"
            supabase_url = f"https://{project_ref}.supabase.co"
        else:
            # Use default or custom Supabase URL
            supabase_url = os.getenv("SUPABASE_URL", "https://your-project.supabase.co")
        
        return SupabaseConfig(
            url=supabase_url,
            anon_key=os.getenv("SUPABASE_ANON_KEY", ""),
            service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
            db_url=db_url,
            storage_bucket=os.getenv("SUPABASE_STORAGE_BUCKET", "rfp-files")
        )
    
    async def initialize(self) -> None:
        """Initialize Supabase client and database connection pool"""
        if self._initialized:
            return
        
        try:
            # Initialize Supabase client for storage operations
            if create_client and self.config.anon_key:
                self.client = create_client(
                    self.config.url,
                    self.config.anon_key,
                    options=ClientOptions(
                        postgrest_client_timeout=10,
                        storage_client_timeout=10
                    )
                )
                logger.info("Supabase client initialized")
            
            # Initialize direct PostgreSQL connection pool for advanced queries
            if asyncpg and self.config.db_url:
                self.db_pool = await asyncpg.create_pool(
                    self.config.db_url,
                    min_size=1,
                    max_size=10,
                    command_timeout=60
                )
                logger.info("PostgreSQL connection pool initialized")
            
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize Supabase: {e}")
            raise
    
    async def close(self) -> None:
        """Close connections"""
        if self.db_pool:
            await self.db_pool.close()
            logger.info("PostgreSQL connection pool closed")
        
        self._initialized = False
    
    def get_client(self) -> Client:
        """Get Supabase client (for storage operations)"""
        if not self._initialized:
            raise RuntimeError("Supabase manager not initialized. Call initialize() first.")
        
        if not self.client:
            raise RuntimeError("Supabase client not available. Check SUPABASE_ANON_KEY configuration.")
        
        return self.client
    
    async def get_db_connection(self):
        """Get database connection from pool"""
        if not self._initialized:
            raise RuntimeError("Supabase manager not initialized. Call initialize() first.")
        
        if not self.db_pool:
            raise RuntimeError("Database pool not available. Check SUPABASE_DB_URL configuration.")
        
        return await self.db_pool.acquire()
    
    async def execute_query(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute a database query and return results"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]
    
    async def execute_command(self, command: str, *args) -> str:
        """Execute a database command and return status"""
        async with self.db_pool.acquire() as conn:
            result = await conn.execute(command, *args)
            return result


class SupabaseStorage:
    """Supabase Storage operations"""
    
    def __init__(self, manager: SupabaseManager):
        self.manager = manager
    
    async def upload_file(
        self, 
        file_path: str, 
        file_data: bytes, 
        content_type: str = "application/octet-stream",
        bucket: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upload file to Supabase Storage"""
        client = self.manager.get_client()
        bucket_name = bucket or self.manager.config.storage_bucket
        
        try:
            result = client.storage.from_(bucket_name).upload(
                path=file_path,
                file=file_data,
                file_options={
                    "content-type": content_type,
                    "upsert": True  # Allow overwriting
                }
            )
            
            logger.info(f"File uploaded successfully: {file_path}")
            return {
                "success": True,
                "path": file_path,
                "bucket": bucket_name,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Failed to upload file {file_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "path": file_path
            }
    
    async def download_file(self, file_path: str, bucket: Optional[str] = None) -> Optional[bytes]:
        """Download file from Supabase Storage"""
        client = self.manager.get_client()
        bucket_name = bucket or self.manager.config.storage_bucket
        
        try:
            result = client.storage.from_(bucket_name).download(file_path)
            logger.info(f"File downloaded successfully: {file_path}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to download file {file_path}: {e}")
            return None
    
    async def delete_file(self, file_path: str, bucket: Optional[str] = None) -> bool:
        """Delete file from Supabase Storage"""
        client = self.manager.get_client()
        bucket_name = bucket or self.manager.config.storage_bucket
        
        try:
            client.storage.from_(bucket_name).remove([file_path])
            logger.info(f"File deleted successfully: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
            return False
    
    async def list_files(
        self, 
        folder_path: str = "", 
        bucket: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List files in a folder"""
        client = self.manager.get_client()
        bucket_name = bucket or self.manager.config.storage_bucket
        
        try:
            result = client.storage.from_(bucket_name).list(
                path=folder_path,
                search_options={"limit": 100}
            )
            
            return result or []
            
        except Exception as e:
            logger.error(f"Failed to list files in {folder_path}: {e}")
            return []
    
    def get_public_url(self, file_path: str, bucket: Optional[str] = None) -> str:
        """Get public URL for a file"""
        client = self.manager.get_client()
        bucket_name = bucket or self.manager.config.storage_bucket
        
        try:
            result = client.storage.from_(bucket_name).get_public_url(file_path)
            return result
            
        except Exception as e:
            logger.error(f"Failed to get public URL for {file_path}: {e}")
            return ""


class SupabaseDatabase:
    """Supabase Database operations (direct PostgreSQL)"""
    
    def __init__(self, manager: SupabaseManager):
        self.manager = manager
    
    async def create_table_if_not_exists(self, table_name: str, schema: str) -> bool:
        """Create table with given schema if it doesn't exist"""
        try:
            create_query = f"CREATE TABLE IF NOT EXISTS {table_name} ({schema});"
            await self.manager.execute_command(create_query)
            logger.info(f"Table {table_name} created or already exists")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create table {table_name}: {e}")
            return False
    
    async def insert_record(
        self, 
        table_name: str, 
        data: Dict[str, Any], 
        on_conflict: str = ""
    ) -> Optional[Dict[str, Any]]:
        """Insert a record into the table"""
        try:
            columns = list(data.keys())
            placeholders = [f"${i+1}" for i in range(len(columns))]
            values = list(data.values())
            
            query = f"""
            INSERT INTO {table_name} ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            {on_conflict}
            RETURNING *;
            """
            
            result = await self.manager.execute_query(query, *values)
            return result[0] if result else None
            
        except Exception as e:
            logger.error(f"Failed to insert record into {table_name}: {e}")
            return None
    
    async def update_record(
        self, 
        table_name: str, 
        data: Dict[str, Any], 
        where_clause: str, 
        where_params: List[Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a record in the table"""
        try:
            set_clauses = [f"{col} = ${i+1}" for i, col in enumerate(data.keys())]
            where_param_placeholders = [f"${i+len(data)+1}" for i in range(len(where_params))]
            
            query = f"""
            UPDATE {table_name}
            SET {', '.join(set_clauses)}
            WHERE {where_clause}
            RETURNING *;
            """
            
            params = list(data.values()) + where_params
            result = await self.manager.execute_query(query, *params)
            return result[0] if result else None
            
        except Exception as e:
            logger.error(f"Failed to update record in {table_name}: {e}")
            return None
    
    async def delete_record(
        self, 
        table_name: str, 
        where_clause: str, 
        where_params: List[Any]
    ) -> bool:
        """Delete records from the table"""
        try:
            placeholders = [f"${i+1}" for i in range(len(where_params))]
            query = f"DELETE FROM {table_name} WHERE {where_clause};"
            
            await self.manager.execute_command(query, *where_params)
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete record from {table_name}: {e}")
            return False
    
    async def select_records(
        self, 
        table_name: str, 
        columns: str = "*",
        where_clause: str = "",
        where_params: List[Any] = None,
        order_by: str = "",
        limit: int = None
    ) -> List[Dict[str, Any]]:
        """Select records from the table"""
        try:
            query_parts = [f"SELECT {columns} FROM {table_name}"]
            params = where_params or []
            
            if where_clause:
                query_parts.append(f"WHERE {where_clause}")
            
            if order_by:
                query_parts.append(f"ORDER BY {order_by}")
            
            if limit:
                query_parts.append(f"LIMIT {limit}")
            
            query = " ".join(query_parts) + ";"
            return await self.manager.execute_query(query, *params)
            
        except Exception as e:
            logger.error(f"Failed to select records from {table_name}: {e}")
            return []


# Global Supabase manager instance
_supabase_manager = None

def get_supabase_manager() -> SupabaseManager:
    """Get or create the global Supabase manager instance"""
    global _supabase_manager
    if _supabase_manager is None:
        _supabase_manager = SupabaseManager()
    return _supabase_manager


def get_supabase_storage() -> SupabaseStorage:
    """Get Supabase Storage instance"""
    manager = get_supabase_manager()
    return SupabaseStorage(manager)


def get_supabase_database() -> SupabaseDatabase:
    """Get Supabase Database instance"""
    manager = get_supabase_manager()
    return SupabaseDatabase(manager)


# Initialize on import (optional)
async def initialize_supabase():
    """Initialize Supabase connections"""
    try:
        manager = get_supabase_manager()
        await manager.initialize()
        logger.info("Supabase initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize Supabase on import: {e}")
        logger.info("Supabase will be initialized on first use")

