from app.config.firebase import firebase_manager
from app.config.llm_factory import LLMFactory, LLMModel
from app.models.models import Collections, KnowledgeItem, WebPageContent
from app.services.knowledgehub.scarping_service import fetch_and_convert_to_markdown
from app.services.vectorization_service import VectorizationService, PageChunk
from app.services.websocket_manager import ws_manager
from typing import List, Dict, Optional, Tuple
import asyncio
from uuid import uuid4
import traceback
import time
from urllib.parse import urlparse

class WebPageProcessor:
    """Handles processing of web pages for knowledge hub with progress tracking."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.vectorization_service = VectorizationService()
        self.stats = {
            "total_urls": 0,
            "processed_urls": 0,
            "failed_urls": 0,
            "total_chunks": 0,
            "start_time": None,
            "end_time": None
        }
        self.progress_data = {}
        
    async def _update_progress(self, url: str, progress: float, status: str, 
                              chunk_progress: Optional[float] = None, chunk_count: Optional[int] = None):
        """Update progress for web page processing and chunking."""
        self.progress_data[url] = {
            "status": status,
            "progress": progress,
            "chunking_progress": chunk_progress or 0,
            "chunk_count": chunk_count or 0,
            "timestamp": int(time.time())
        }
        
        if self.user_id:
            await ws_manager.send(
                channel_id=self.user_id,
                event="web_page_processing_progress",
                data=self.progress_data
            )
    
    async def _scrape_web_page(self, url: str, retry_count: int = 0) -> Dict:
        """Scrape a web page with retry logic."""
        max_retries = 2
        try:
            await self._update_progress(url, 0, "scraping", 0, 0)
            
            # Use the existing scraping service
            result = fetch_and_convert_to_markdown(url)
            
            if result["status"] == "success":
                await self._update_progress(url, 50, "scraped", 0, 0)
                return result
            else:
                raise Exception(result.get("error", "Unknown scraping error"))
                
        except Exception as e:
            print(f"Error scraping URL {url} (attempt {retry_count + 1}): {str(e)}")
            if retry_count < max_retries:
                print(f"Retrying scraping for URL {url}...")
                await asyncio.sleep(1 * (retry_count + 1))  # Exponential backoff
                return await self._scrape_web_page(url, retry_count + 1)
            else:
                traceback.print_exc()
                await self._update_progress(url, 100, "failed", 0, 0)
                return {"url": url, "status": "failed", "error": str(e)}
    
    # async def _extract_page_metadata(self, url: str, markdown_content: str, model: LLMModel) -> Dict:
    #     """Extract metadata from web page content using LLM."""
    #     try:
    #         # Create a simple prompt for metadata extraction
    #         metadata_prompt = f"""
    #         Extract key metadata from this web page content:
            
    #         URL: {url}
    #         Content: {markdown_content[:2000]}...
            
    #         Provide a JSON response with:
    #         - title: The page title
    #         - description: A brief description of the page content
    #         - key_topics: List of main topics covered
    #         - content_type: Type of content (article, documentation, product page, etc.)
    #         """
            
    #         messages = [
    #             {"role": "system", "content": "You are a helpful assistant that extracts metadata from web pages."},
    #             {"role": "user", "content": metadata_prompt},
    #         ]
            
    #         # Use a simple LLM call for metadata extraction
    #         response = await LLMFactory.get_llm(model).ainvoke(messages)
            
    #         # Parse the response (assuming it returns JSON-like structure)
    #         # For now, we'll use a simple approach
    #         return {
    #             "title": f"Web Page - {urlparse(url).netloc}",
    #             "description": f"Scraped content from {url}",
    #             "key_topics": [],
    #             "content_type": "web_page"
    #         }
            
    #     except Exception as e:
    #         print(f"Error extracting metadata for {url}: {str(e)}")
    #         return {
    #             "title": f"Web Page - {urlparse(url).netloc}",
    #             "description": f"Scraped content from {url}",
    #             "key_topics": [],
    #             "content_type": "web_page"
    #         }
    
    async def _chunk_and_vectorize_content(self, url: str, markdown_content: str, 
                                         title: str, kh_item_id: str, user_id: str) -> int:
        """Chunk and vectorize the web page content."""
        try:
            # Chunk the markdown content
            chunks = self.vectorization_service.hybrid_chunk_markdown_with_headers(markdown_content)
            total_chunks = len(chunks)
            
            if total_chunks == 0:
                await self._update_progress(url, 100, "failed", 0, 0)
                return 0
            
            # Update progress for chunking
            await self._update_progress(url, 75, "chunking", 50, total_chunks)
            
            # Convert chunks to PageChunk format for vectorization
            page_chunks = []
            for chunk in chunks:
                page_chunk = PageChunk(
                    content=chunk.content,
                    page_numbers=chunk.page_numbers,
                    metadata={
                        "url": url,
                        "title": title,
                        "kh_item_id": kh_item_id,
                        "user_id": user_id,
                        "type": "web_page",
                        "source": "web_scraping",
                        "created_at": int(time.time()),
                    }
                )
                page_chunks.append(page_chunk)
            
            # Vectorize the chunks
            await self.vectorization_service.embed_and_upload(page_chunks, batch_size=50)
            
            await self._update_progress(url, 100, "completed", 100, total_chunks)
            return total_chunks
            
        except Exception as e:
            print(f"Error chunking and vectorizing content for {url}: {str(e)}")
            traceback.print_exc()
            await self._update_progress(url, 100, "failed", 0, 0)
            return 0
    
    async def _save_web_page_item(self, url: str, title: str, markdown_content: str, 
                                 label_ids: List[str] = []) -> str:
        """Save web page item to the knowledge hub."""
        try:
            document_id = str(uuid4())
            knowledge_item = KnowledgeItem(
                id=document_id,
                user_id=self.user_id,
                type="web_page",
                labelIds=label_ids,
                content=WebPageContent(
                    url=url,
                    title=title,
                    scraped_text=markdown_content,
                    last_scraped=int(time.time())
                )
            ).to_dict()
            
            await firebase_manager.create_document(
                collection=Collections.KNOWLEDGE_HUB.value,
                data=knowledge_item,
                document_id=document_id
            )
            
            return document_id
            
        except Exception as e:
            print(f"Error saving web page item: {str(e)}")
            traceback.print_exc()
            return ""
    
    async def process_single_url(self, url: str, llm_model: LLMModel, 
                               label_ids: List[str] = []) -> str:
        """Process a single URL for web page extraction."""
        try:
            # Scrape the web page
            scrape_result = await self._scrape_web_page(url)
            
            if scrape_result["status"] != "success":
                self.stats["failed_urls"] += 1
                return ""
            
            markdown_content = scrape_result["markdown"]
            
            # Extract metadata
            # metadata = await self._extract_page_metadata(url, markdown_content, llm_model)
            title = "Web Page"
            
            # Save to knowledge hub
            document_id = await self._save_web_page_item(url, title, markdown_content, label_ids)
            
            if not document_id:
                self.stats["failed_urls"] += 1
                return ""
            
            # Chunk and vectorize content
            _markdown_content = {
                "page_1": markdown_content
            }
            chunk_count = await self._chunk_and_vectorize_content(url, _markdown_content, title, document_id ,self.user_id)
            
            # Update statistics
            self.stats["processed_urls"] += 1
            self.stats["total_chunks"] += chunk_count
            
            return document_id
            
        except Exception as e:
            print(f"Error processing URL {url}: {str(e)}")
            traceback.print_exc()
            await self._update_progress(url, 100, "failed", 0, 0)
            self.stats["failed_urls"] += 1
            return ""

async def process_web_pages(
    urls: List[str],
    llm_model: LLMModel = LLMModel.GEMINI_2_FLASH,
    user_id: str = None,
    urls_batch_size: int = 3,
    label_ids: List[str] = [],
    max_concurrent_urls: int = 2
) -> Dict[str, str]:
    """
    Process multiple web pages for knowledge hub with comprehensive progress tracking.
    
    Args:
        urls: List of URLs to process
        llm_model: LLM model to use for metadata extraction
        user_id: User ID for saving web pages and progress updates
        urls_batch_size: Number of URLs to process in each batch
        label_ids: Labels to apply to extracted web pages
        max_concurrent_urls: Maximum number of URLs to process concurrently
        
    Returns:
        Dictionary mapping URLs to created document IDs
    """
    if not user_id:
        raise ValueError("user_id is required for web page processing")
    
    if not urls:
        return {}
    
    # Initialize progress tracking
    progress_data = {
        url: {
            "status": "processing",
            "progress": 0,
            "chunking_progress": 0,
            "chunk_count": 0
        } for url in urls
    }
    
    # Send initial progress
    if user_id:
        await ws_manager.send(
            channel_id=user_id,
            event="web_page_processing_progress",
            data=progress_data
        )
    
    processor = WebPageProcessor(user_id)
    processor.stats["total_urls"] = len(urls)
    processor.stats["start_time"] = time.time()
    results = {}
    
    try:
        # Process URLs in batches with controlled concurrency
        for i in range(0, len(urls), urls_batch_size):
            current_batch = urls[i:i + urls_batch_size]
            
            # Process batch with limited concurrency
            semaphore = asyncio.Semaphore(max_concurrent_urls)
            
            async def process_url_with_semaphore(url: str) -> Tuple[str, str]:
                async with semaphore:
                    document_id = await processor.process_single_url(url, llm_model, label_ids)
                    return url, document_id
            
            # Execute batch processing
            batch_tasks = [process_url_with_semaphore(url) for url in current_batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Process results
            for result in batch_results:
                if isinstance(result, Exception):
                    print(f"URL processing failed: {str(result)}")
                    traceback.print_exc()
                    processor.stats["failed_urls"] += 1
                else:
                    url, document_id = result
                    if document_id:
                        results[url] = document_id
            
            # Update overall progress
            processed_count = len(results)
            overall_progress = (processed_count / len(urls)) * 100
            
            if user_id:
                await ws_manager.send(
                    channel_id=user_id,
                    event="web_page_processing_progress",
                    data={
                        "overall_progress": overall_progress, 
                        "processed_urls": processed_count,
                        "total_urls": len(urls),
                        "failed_urls": processor.stats["failed_urls"],
                        "total_chunks": processor.stats["total_chunks"]
                    }
                )
        
        # Calculate final statistics
        processor.stats["end_time"] = time.time()
        processing_time = processor.stats["end_time"] - processor.stats["start_time"]
        
        # Send completion notification with statistics
        if user_id:
            await ws_manager.send(
                channel_id=user_id,
                event="web_page_processing_progress",
                data={
                    "overall_progress": 100, 
                    "processed_urls": len(urls),
                    "total_urls": len(urls),
                    "failed_urls": processor.stats["failed_urls"],
                    "total_chunks": processor.stats["total_chunks"],
                    "processing_time_seconds": round(processing_time, 2),
                    "success_rate": round((processor.stats["processed_urls"] / len(urls)) * 100, 2)
                },
                completed=True
            )
        
        return results
        
    except Exception as e:
        print(f"Error in web page processing: {str(e)}")
        traceback.print_exc()
        
        # Send error notification
        if user_id:
            await ws_manager.send(
                channel_id=user_id,
                event="web_page_processing_progress",
                data={"error": str(e)},
                completed=True
            )
        
        return {}

async def process_single_web_page(
    url: str,
    llm_model: LLMModel = LLMModel.GEMINI_2_FLASH,
    label_ids: List[str] = [],
    user_id: str = None
) -> str:
    """Process a single web page for knowledge hub."""
    if not user_id:
        raise ValueError("user_id is required for web page processing")
    
    processor = WebPageProcessor(user_id)
    return await processor.process_single_url(url, llm_model, label_ids)
