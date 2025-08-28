from typing import List, Dict, Any
from pinecone import PineconeAsyncio
from pinecone.db_data import _IndexAsyncio
import os


class VectorDatabase:
    def __init__(self, index_name: str):
        self.pc = None
        self.index_name = index_name
        self.index: _IndexAsyncio = None

    async def __aenter__(self):
        self.pc = PineconeAsyncio(api_key=os.getenv("PINECONE_API_KEY"))
        index_description = await self.pc.describe_index(self.index_name)
        self.index = self.pc.IndexAsyncio(host=index_description.host)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.pc.close()

    async def upsert_vectors(self, vectors: List[Dict[str, Any]], namespace: str):
        await self.index.upsert(vectors=vectors, namespace=namespace)

    async def query_vectors(
        self, query_embedding: List[float], filters: Dict, top_k: int, namespace: str
    ):
        if not filters:
            results = (await self.index.query(
                namespace=namespace,
                vector=query_embedding,
                top_k=top_k,
                include_values=False,
                include_metadata=True,
            )).matches
            return results
        
        # Build combined filter from all filter conditions
        combined_filter = {}
        for key, value in filters.items():
            if isinstance(value, dict) and any(op in value for op in ["$eq", "$in", "$gt", "$lt", "$gte", "$lte"]):
                # Filter already has operator format, use as is
                combined_filter[key] = value
            elif isinstance(value, list):
                # Convert list to $in operator
                combined_filter[key] = {"$in": value}
            else:
                # Convert single value to $eq operator
                combined_filter[key] = {"$eq": value}

        # Execute single query with all filters combined
        results = (await self.index.query(
            namespace=namespace,
            vector=query_embedding,
            top_k=top_k,
            include_values=False,
            filter=combined_filter,
            include_metadata=True,
        )).matches
        
        return results

    async def rerank_vectors(self,query : str, documents: List, top_n: int):
        try:
            reranked_documents = await self.pc.inference.rerank(
                model="bge-reranker-v2-m3",
                query=query,
                documents=documents,
                top_n=top_n,
                return_documents=True,
            )
            return reranked_documents
        except Exception as e:
            print(e)
            return documents

    async def delete_vectors(
        self,
        ids: List[str],
        namespace: str = "pdfs",
        delete_all: bool = False,
        filters: Dict = {},
    ):
        if filters:
            # Build the filter conditions
            filter_conditions = []
            for key, values in filters.items():
                if isinstance(values, bool):
                    filter_conditions.append({key: values})
                else:
                    filter_conditions.append({key: {"$in": values}})

            # Combine filters with $and if there are multiple conditions
            final_filter = (
                {"$and": filter_conditions} if len(filter_conditions) > 1 else filter_conditions[0]
            )
            vector_ids = []
            pagination_token = None
            while True:
                query_response = await self.index.query(
                    vector=[0] * int(os.getenv("EMBEDDING_DIMENSIONS", 1536)),
                    filter=final_filter,
                    namespace=namespace,
                    top_k=10000,
                    include_metadata=False,
                    include_values=False,
                    pagination_token=pagination_token,
                )
                vector_ids.extend([match.id for match in query_response.matches])
                pagination_token = query_response.pagination_token
                if not pagination_token:
                    break

            if vector_ids:
                await self.index.delete(ids=vector_ids, namespace=namespace)
        else:
            await self.index.delete(
                ids=ids if not delete_all else None,
                delete_all=delete_all,
                namespace=namespace,
            )
