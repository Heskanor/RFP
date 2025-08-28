from app.config.vector_db import VectorDatabase
from app.config.llm_factory import async_client

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import tiktoken
from langchain.text_splitter import MarkdownHeaderTextSplitter, MarkdownTextSplitter
from .embeddings_service import EmbeddingsService
from tqdm import tqdm
from uuid import uuid4
import re
import os


@dataclass
class PageChunk:
    content: str
    page_numbers: List[int]
    metadata: Dict[str, Any] = None


class VectorizationService:
    def __init__(
        self,
        index_name: str = os.getenv("PINECONE_INDEX_NAME"),
        provider: str = os.getenv("EMBEDDING_PROVIDER", "openai"),
        embed_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        dimensions: int = os.getenv("EMBEDDING_DIMENSIONS", 1024),
    ):
        self.index_name = index_name
        self.embed_model = embed_model
        self.model_max_tokens = 8192
        self.embeddings_service = EmbeddingsService(
            provider=provider, 
            model=embed_model, 
            dimensions=dimensions)

    def count_tokens(self, text: str, model: str = "gpt-4") -> int:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))

    def has_header(self, metadata: Dict) -> bool:
        return any("header" in key.lower() for key in metadata.keys())
    
    def has_image(self, chunk: str) -> bool:
        # Regex to match markdown image syntax: ![alt](src)
        pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
        matches = pattern.findall(chunk)
        return len(matches) > 0
    
    def has_table(self, chunk: str) -> bool:
        table_pattern = re.compile(
        r"""(
            (?:^\|.*\|\s*\n)+
            ^\|(?:\s*:?-+:?\s*\|)+\s*\n
            (?:^\|.*\|\s*\n?)*
        )""",
        re.MULTILINE | re.VERBOSE
        )
        matches = table_pattern.findall(chunk)
        return len(matches) > 0
    
    def hybrid_chunk_markdown_with_headers(
    self,
    pages_markdown: Dict[int, str],
    max_tokens: int = 500,
    chunk_overlap: int = 100,
    model: str = "gpt-4",
    add_image_metadata: bool = False,    
    add_table_metadata: bool = False
) -> List[PageChunk]:
        headers_to_split_on = [("#", "Header 1"), ("##", "Header 2"), ("###", "Header 3")]
        markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on, strip_headers=True
        )

        all_chunks: List[PageChunk] = []

        # Step 1: Split each page into header-aware chunks
        for i in range(len(pages_markdown)):
            page_key = f"page_{i+1}"
            page_content = pages_markdown[page_key]
            split_chunks = markdown_splitter.split_text(page_content)
            for split in split_chunks:
                page_metadata = split.metadata
                if add_image_metadata:
                    page_metadata["has_image"] = self.has_image(split.page_content)
                if add_table_metadata:
                    page_metadata["has_table"] = self.has_table(split.page_content)

                if self.count_tokens(split.page_content) > self.model_max_tokens:
                    print(f"Page {page_key} has {self.count_tokens(split.page_content)} tokens > {self.model_max_tokens}")
                    splitter = MarkdownTextSplitter(chunk_size=2000, chunk_overlap=100)
                    for chunk in splitter.split_text(split.page_content):
                        all_chunks.append(PageChunk(
                            content=chunk,
                            page_numbers=[page_key],
                            metadata=page_metadata
                        ))
                else:
                    all_chunks.append(PageChunk(
                        content=split.page_content,
                        page_numbers=[page_key],
                        metadata=page_metadata
                    ))

        merged_chunks: List[PageChunk] = []
        current_chunk: Optional[PageChunk] = None

        def inject_headers(chunk: PageChunk, metadata: Dict):
            headers = []
            for level in ["Header 1", "Header 2", "Header 3"]:
                value = metadata.get(level)
                if value:
                    prefix = "#" * int(level[-1])  
                    headers.append(f"{prefix} {value}")
            if headers:
                chunk.content = "\n".join(headers) + "\n" + chunk.content
            return chunk


        # Step 2: Merge adjacent chunks when safe
        for chunk in all_chunks:
            if current_chunk is None:
                current_chunk = chunk
                continue

            should_merge = not self.has_header(chunk.metadata)
            combined_content = f"{current_chunk.content}\n{chunk.content}"

            if should_merge and self.count_tokens(combined_content, model=model) <= max_tokens:
                current_chunk.content = combined_content
                current_chunk.page_numbers = sorted(
                    set(current_chunk.page_numbers + chunk.page_numbers)
                )
                if chunk.metadata:
                    if current_chunk.metadata is None:
                        current_chunk.metadata = {}
                    current_chunk.metadata.update(chunk.metadata)
            else:
                merged_chunks.append(current_chunk)
                if not chunk.metadata:
                    chunk.metadata = current_chunk.metadata
                current_chunk = chunk

        if current_chunk is not None:
            merged_chunks.append(current_chunk)

       
        # Step 3: Re-inject headers for each chunk (if missing from content)
        for chunk in merged_chunks:
            chunk = inject_headers(chunk, chunk.metadata)

        return merged_chunks

    def hybrid_chunk_markdown_with_pages(
        self,
        pages_markdown: Dict[int, str],
        max_tokens: int = 1024,
        chunk_overlap: int = 100,
        model: str = "gpt-4",
    ) -> List[PageChunk]:
        headers_to_split_on = [("#", "Header 1"),("##", "Header 2"), ("###", "Header 3")]
        markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on, strip_headers=False
        )
        all_chunks = []

        for i in range(len(pages_markdown)):
            page_num, page_content = f"page_{i+1}", pages_markdown.get(f"page_{i+1}")
            splits = markdown_splitter.split_text(page_content)
            for split in splits:
                chunk = PageChunk(
                    content=split.page_content,
                    page_numbers=[page_num],
                    metadata=split.metadata,
                )
                all_chunks.append(chunk)

        # return all_chunks
        merged_chunks = []

        current_chunk = None

        for chunk in all_chunks:
            if current_chunk is None:
                current_chunk = chunk
                continue

            should_try_merge = (
                not self.has_header(chunk.metadata)
                or chunk.page_numbers[0] == current_chunk.page_numbers[0]
            )

            if should_try_merge:
                combined_content = current_chunk.content + "\n" + chunk.content
                if self.count_tokens(combined_content, model=model) <= max_tokens:
                    current_chunk.content = combined_content
                    current_chunk.page_numbers = sorted(
                        set(current_chunk.page_numbers + chunk.page_numbers)
                    )
                    if chunk.metadata:
                        if current_chunk.metadata is None:
                            current_chunk.metadata = {}
                        current_chunk.metadata.update(chunk.metadata)
                    continue

            merged_chunks.append(current_chunk)
            current_chunk = chunk

        if current_chunk is not None:
            merged_chunks.append(current_chunk)

        return merged_chunks

    async def embed_and_upload(
        self,
        chunks: List[PageChunk],
        metadata: Dict = {},
        namespace: str = os.getenv("PINECONE_NAMESPACE", "pdfs"),
        batch_size: int = 10,
    ):
        self.embeddings_service.provider.batch_size = batch_size
        async with VectorDatabase(self.index_name) as db:
            for i in tqdm(range(0, len(chunks), batch_size), desc="Processing batches"):
                batch = chunks[i : i + batch_size]
                res = await self.embeddings_service.embed_documents(
                    documents=[chunk.content for chunk in batch],
                )
                vectors = []
                for d, e in zip(batch, res):
                    id = str(uuid4())
                    vectors.append({
                        "id": id,
                        "values": e,
                        "metadata": {
                            "id": id,
                            "text": d.content,
                            "page_numbers": d.page_numbers,
                            **d.metadata,
                            **metadata,
                        },
                    })
                await db.upsert_vectors(vectors, namespace)

    async def query_context(
        self,
        query: str,
        filters: Dict,
        aggregation: bool = True,
        top_k: int = 3,
        namespace: str = os.getenv("PINECONE_NAMESPACE", "pdfs"),
    ):

        async with VectorDatabase(self.index_name) as db:
            
            query_embedding = await self.embeddings_service.embed_query(query)
            
            docs = await db.query_vectors(query_embedding, filters, top_k, namespace)
            if not aggregation:
                return docs

            context, files_pages = "", {}
            for doc in docs:
                file_id = doc.metadata["file_id"]
                
                files_pages.setdefault(file_id, []).extend(
                    [
                        p
                        for p in doc.metadata["page_numbers"]
                        if p not in files_pages[file_id]
                    ]
                )
                context += "\n" + doc.metadata["text"]
            return context, files_pages

    async def rerank_context(self, query: str, documents: List, top_n: int):
        async with VectorDatabase(self.index_name) as db:
            reranked_documents = await db.rerank_vectors(query, documents, top_n)
            return reranked_documents

    async def delete_data(
        self,
        ids: List[str] = [],
        namespace: str = os.getenv("PINECONE_NAMESPACE", "pdfs"),
        delete_all: bool = False,
        filters: Dict = {},
    ):
        try:
            async with VectorDatabase(self.index_name) as db:
                await db.delete_vectors(
                    ids=ids, namespace=namespace, delete_all=delete_all, filters=filters
                )
                return True
        except Exception as e:
            print(e)
            return False
