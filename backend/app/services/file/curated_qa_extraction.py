from app.config.firebase import firebase_manager
from .file_processing import process_single_file, enrich_files_with_markdown, process_files
from app.config.llm_factory import LLMFactory, LLMModel
from app.models.models import Collections, FileStatus, KnowledgeItem, CuratedQAContent, UploadedFileContent
from app.models.curated_qa_models import LLMCuratedQAs
from typing import List, Dict, Optional, Tuple
from app.services.prompts import CURATED_QA_PROMPT
from app.services.vectorization_service import VectorizationService, PageChunk
from app.services.websocket_manager import ws_manager
import asyncio
from uuid import uuid4
import traceback
import time

files_collection = Collections.FILE.value

class CuratedQAExtractor:
    """Handles extraction of curated Q&As from RFP documents with progress tracking."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.vectorization_service = VectorizationService()
        self.stats = {
            "total_files": 0,
            "processed_files": 0,
            "failed_files": 0,
            "total_qas": 0,
            "start_time": None,
            "end_time": None
        }
        self.progress_data = {}
        
    async def _update_progress(self, file_id: str, progress: float, status: str, 
                              qa_progress: Optional[float] = None, qa_count: Optional[int] = None):
        """Update progress for file processing and Q&A extraction."""
        self.progress_data[file_id] = {
            "status": status,
            "progress": progress,
            "qa_extraction_progress": qa_progress or 0,
            "qa_count": qa_count or 0,
            "timestamp": int(time.time())
        }
        
        if self.user_id:
            await ws_manager.send(
                channel_id=self.user_id,
                event="curated_qa_extraction_progress",
                data=self.progress_data
            )
    
    async def _extract_curated_qa_from_section(self, pages: List[int], content: str, 
                                             file_id: str, file_name: str, model: LLMModel, retry_count: int = 0) -> List[Dict]:
        """Extract curated Q&As from a single document section with retry logic."""
        max_retries = 2
        try:
            messages = [
                {"role": "system", "content": CURATED_QA_PROMPT},
                {"role": "user", "content": f"RFP document chunk:\n {content}"},
            ]
            
            curated_qas = await LLMFactory.get_llm_with_structured_output(model, LLMCuratedQAs).ainvoke(messages)
            curated_qas = curated_qas.model_dump()
            curated_qas = curated_qas.get("curated_qas", [])
            
            # Add metadata to each QA
            for qa in curated_qas:
                qa["page_number"] = pages
                qa["file_id"] = file_id
                qa["file_name"] = file_name
                # qa["extracted_at"] = int(time.time())
                
            return curated_qas
        except Exception as e:
            print(f"Error extracting Q&As from section for file {file_id} (attempt {retry_count + 1}): {str(e)}")
            if retry_count < max_retries:
                print(f"Retrying extraction for file {file_id}...")
                await asyncio.sleep(1 * (retry_count + 1))  # Exponential backoff
                return await self._extract_curated_qa_from_section(pages, content, file_id, file_name, model, retry_count + 1)
            else:
                traceback.print_exc()
                return []
    
    async def _extract_curated_qa_from_file(self, file: Dict, model: LLMModel, 
                                          file_id: str) -> Tuple[List[Dict], int]:
        """Extract curated Q&As from a single file with progress tracking."""
        try:
            await self._update_progress(file_id, 0, FileStatus.PROCESSING.value, 0, 0)
            
            if not file or not file.get("markdown"):
                await self._update_progress(file_id, 100, FileStatus.FAILED.value, 0, 0)
                return [], 0
            
            # Chunk the document for processing
            chunks = self.vectorization_service.hybrid_chunk_markdown_with_pages(file.get("markdown", {}))
            total_chunks = len(chunks)
            
            if total_chunks == 0:
                await self._update_progress(file_id, 100, FileStatus.FAILED.value, 0, 0)
                return [], 0
            
            # Process chunks with progress tracking
            all_curated_qas = []
            _BATCH_SIZE = 10
            for i in range(0, total_chunks, _BATCH_SIZE):
                try:
                    batch_chunks = chunks[i:i + _BATCH_SIZE]
                    # Extract Q&As from chunk
                    chunk_qas = await asyncio.gather(*[self._extract_curated_qa_from_section(
                        chunk.page_numbers, chunk.content, file.get("id"), file.get("name"), model
                    ) for chunk in batch_chunks])
                    result_qas = [qa for sublist in chunk_qas for qa in sublist]
                    all_curated_qas.extend(result_qas)   
                    
                    # Update Q&A extraction progress
                    qa_progress = min(((i + _BATCH_SIZE) / total_chunks) * 100, 100)
                    await self._update_progress(file_id, 100, FileStatus.PROCESSING.value, qa_progress, len(all_curated_qas))
                    
                except Exception as e:
                    print(f"Error processing chunk {i} for file {file_id}: {str(e)}")
                    continue
            
            await self._update_progress(file_id, 100, FileStatus.PARSED.value, 100, len(all_curated_qas))
            return all_curated_qas, len(all_curated_qas)
            
        except Exception as e:
            print(f"Error extracting Q&As from file {file_id}: {str(e)}")
            traceback.print_exc()
            await self._update_progress(file_id, 100, FileStatus.FAILED.value, 0, 0)
            return [], 0
    
    async def _save_curated_qa(self, curated_qas: List[Dict], label_ids: List[str] = []) -> List[str]:
        """Save curated Q&As to the knowledge hub."""
        if not curated_qas:
            return []
            
        try:
            created_docs = []
            operations = []
            
            for curated_qa in curated_qas:
                document_id = str(uuid4())
                knowledge_item = KnowledgeItem(
                    id=document_id,
                    user_id=self.user_id,
                    type="curated_qa",
                    labelIds=label_ids,
                    content=CuratedQAContent(
                        file_id=curated_qa.get("file_id"),
                        file_name=curated_qa.get("file_name"),
                        page_number=curated_qa.get("page_number"),
                        question=curated_qa.get("question"),
                        answer=curated_qa.get("answer"),
                        source_type=curated_qa.get("source_type"),
                        reference=curated_qa.get("reference")
                    )
                ).to_dict()
                
                operations.append({
                    "type": "create",
                    "collection": Collections.KNOWLEDGE_HUB.value,
                    "document_id": document_id,
                    "data": knowledge_item
                })
                created_docs.append(knowledge_item)
            
            await firebase_manager.batch_operation(operations)
            return created_docs
            
        except Exception as e:
            print(f"Error saving curated Q&As: {str(e)}")
            traceback.print_exc()
            return []
    
    async def _create_kh_rfp_item(self, file: Dict,  label_ids: List[str] = []):
        """Create a RFP item in the knowledge hub."""
        try:
            document_id = str(uuid4())
            knowledge_item = KnowledgeItem(
                id=document_id,
                user_id=self.user_id,
                type="uploaded_documents",
                subtype="rfp",
                labelIds=label_ids,
                content=UploadedFileContent(
                    id=file.get("id"),
                    name=file.get("name"),
                    type=file.get("type"),
                    size=file.get("size"),
                    url=file.get("url")
                ))
            await firebase_manager.create_document(
                collection=Collections.KNOWLEDGE_HUB.value,
                data=knowledge_item.to_dict(), 
                document_id=document_id)
            return document_id
        except Exception as e:
            print(f"Error creating RFP item: {str(e)}")
            traceback.print_exc()
    
    async def _vectorize_curated_qas(self, curated_qas: List[Dict], user_id: str = None):
        """Vectorize curated Q&As."""
        try:
            chunks = [PageChunk(
                content=f"Q: {curated_qa.get('content', {}).get('question')}\nA: {curated_qa.get('content', {}).get('answer')}",
                page_numbers=curated_qa.get("content", {}).get("page_number") or [],
                metadata={
                    "kh_item_id": curated_qa.get("id") or "",            
                    "user_id": user_id or curated_qa.get("user_id") or "",
                    "file_id": curated_qa.get("content", {}).get("file_id") or "",
                    "question": curated_qa.get("content", {}).get("question") or "",
                    "answer": curated_qa.get("content", {}).get("answer") or "",
                    "type": "curated_qa",
                    "reference": curated_qa.get("content", {}).get("reference", {}).get("section") or "",
                    "created_at": curated_qa.get("created_at") or "",
                }
            ) for curated_qa in curated_qas]
            
            await self.vectorization_service.embed_and_upload(chunks, batch_size=50)
        except Exception as e:
            print(f"Error vectorizing curated Q&As: {str(e)}")
            traceback.print_exc()


    async def process_single_file(self, file_id: str, llm_model: LLMModel, 
                                label_ids: List[str] = []) -> List[str]:
        """Process a single file for curated Q&A extraction."""
        try:
            # Enrich file with markdown content
            files = await enrich_files_with_markdown(files_ids=[file_id])
            if not files:
                await self._update_progress(file_id, 100, FileStatus.FAILED.value, 0, 0)
                return []
            
            file = files[0]
            
            # Check if file needs processing first
            if file.get("status") != FileStatus.PARSED.value:
                print(f"File {file_id} is not parsed, processing...")
                # data = {file.get("id"): {"status": FileStatus.PROCESSING.value, "progress": 0}}
                await process_files(
                    file_ids=[file_id], 
                    llm_model=llm_model, 
                    files_batch_size=1, 
                    pages_batch=10, 
                    analyze_image=True,
                    channel_id=self.user_id,
                    data=self.progress_data,
                    vectorize=False
                    )
                # await process_single_file(
                #     file.get("id"),
                #     file.get("url"),
                #     batch_size=10,
                #     analyze_image=True,
                #     llm_model_for_images=llm_model,
                #     channel_id=self.user_id,
                #     data=data
                # )
                
                # Re-fetch the file after processing
                files = await enrich_files_with_markdown(files_ids=[file_id])
                if not files:
                    await self._update_progress(file_id, 100, FileStatus.FAILED.value, 0, 0)
                    return []
                file = files[0]
                await self._create_kh_rfp_item(file, label_ids)
            
            # Extract Q&As from file
            curated_qas, qa_count = await self._extract_curated_qa_from_file(file, llm_model, file_id)
            
            if not curated_qas:
                return []
            
            # Save Q&As to knowledge hub
            created_docs = await self._save_curated_qa(curated_qas, label_ids)

            #Vectorize Curated QAs
            await self._vectorize_curated_qas(created_docs, self.user_id)
            
            # Update statistics
            self.stats["processed_files"] += 1
            self.stats["total_qas"] += qa_count
            
            return created_docs
            
        except Exception as e:
            print(f"Error processing file {file_id}: {str(e)}")
            traceback.print_exc()
            await self._update_progress(file_id, 100, FileStatus.FAILED.value, 0, 0)
            self.stats["failed_files"] += 1
            return []

async def extract_curated_qa(
    file_ids: List[str],
    llm_model: LLMModel = LLMModel.GEMINI_2_FLASH,
    user_id: str = None,
    files_batch_size: int = 3,
    label_ids: List[str] = [],
    max_concurrent_files: int = 2
) -> Dict[str, List[str]]:
    """
    Extract curated Q&As from multiple files with comprehensive progress tracking.
    
    Args:
        file_ids: List of file IDs to process
        llm_model: LLM model to use for extraction
        user_id: User ID for saving Q&As and progress updates
        files_batch_size: Number of files to process in each batch
        label_ids: Labels to apply to extracted Q&As
        max_concurrent_files: Maximum number of files to process concurrently
        
    Returns:
        Dictionary mapping file IDs to lists of created document IDs
    """
    if not user_id:
        raise ValueError("user_id is required for Q&A extraction")
    
    if not file_ids:
        return {}
    
    # Initialize progress tracking
    progress_data = {
        file_id: {
            "status": FileStatus.PROCESSING.value,
            "progress": 0,
            "qa_extraction_progress": 0,
            "qa_count": 0
        } for file_id in file_ids
    }
    
    # Send initial progress
    if user_id:
        await ws_manager.send(
            channel_id=user_id,
            event="curated_qa_extraction_progress",
            data=progress_data
        )
    
    extractor = CuratedQAExtractor(user_id)
    extractor.stats["total_files"] = len(file_ids)
    extractor.stats["start_time"] = time.time()
    results = {}
    
    try:
        # Process files in batches with controlled concurrency
        for i in range(0, len(file_ids), files_batch_size):
            current_batch = file_ids[i:i + files_batch_size]
            
            # Process batch with limited concurrency
            semaphore = asyncio.Semaphore(max_concurrent_files)
            
            async def process_file_with_semaphore(file_id: str) -> Tuple[str, List[str]]:
                async with semaphore:
                    created_docs = await extractor.process_single_file(file_id, llm_model, label_ids)
                    return file_id, created_docs
            
            # Execute batch processing
            batch_tasks = [process_file_with_semaphore(file_id) for file_id in current_batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Process results
            for result in batch_results:
                if isinstance(result, Exception):
                    print(f"File processing failed: {str(result)}")
                    traceback.print_exc()
                    extractor.stats["failed_files"] += 1
                else:
                    file_id, created_docs = result
                    results[file_id] = created_docs
            
            # Update overall progress
            processed_count = len(results)
            overall_progress = (processed_count / len(file_ids)) * 100
            
            if user_id:
                await ws_manager.send(
                    channel_id=user_id,
                    event="curated_qa_extraction_progress",
                    data={
                        "overall_progress": overall_progress, 
                        "processed_files": processed_count,
                        "total_files": len(file_ids),
                        "failed_files": extractor.stats["failed_files"],
                        "total_qas": extractor.stats["total_qas"]
                    }
                )
        
        # Calculate final statistics
        extractor.stats["end_time"] = time.time()
        processing_time = extractor.stats["end_time"] - extractor.stats["start_time"]
        
        # Send completion notification with statistics
        if user_id:
            await ws_manager.send(
                channel_id=user_id,
                event="curated_qa_extraction_progress",
                data={
                    "overall_progress": 100, 
                    "processed_files": len(file_ids),
                    "total_files": len(file_ids),
                    "failed_files": extractor.stats["failed_files"],
                    "total_qas": extractor.stats["total_qas"],
                    "processing_time_seconds": round(processing_time, 2),
                    "success_rate": round((extractor.stats["processed_files"] / len(file_ids)) * 100, 2)
                },
                completed=True
            )
        
        return results
        
    except Exception as e:
        print(f"Error in curated Q&A extraction: {str(e)}")
        traceback.print_exc()
        
        # Send error notification
        if user_id:
            await ws_manager.send(
                channel_id=user_id,
                event="curated_qa_extraction_progress",
                data={"error": str(e)},
                completed=True
            )
        
        return {}


async def process_and_extract_qa_from(
    file_id: str,
    llm_model: LLMModel = LLMModel.GEMINI_2_FLASH,
    label_ids: List[str] = [],
    pages_batch: int = 10,
    analyze_image: bool = True,
    user_id: str = None,
    data: dict = {},
):
    """Legacy function for backward compatibility."""
    extractor = CuratedQAExtractor(user_id)
    return await extractor.process_single_file(file_id, llm_model, label_ids)
    
    
    