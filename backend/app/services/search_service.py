from app.services.vectorization_service import VectorizationService
from app.config.firebase import firebase_manager
from typing import Dict, Any, List, Literal, Optional
from datetime import datetime
from app.models.models import Collections
import re
import asyncio

def clean_markdown_text(text: str) -> str:
    """Clean markdown text by removing image references, formatting, and artifacts."""
    if not text or text.strip() == '.':
        return ""
    
    # Remove markdown image syntax: ![alt](src)
    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', '', text)
    
    # Remove markdown headers (keep the text content)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    
    # Remove markdown links but keep the text: [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    
    # Remove markdown formatting: **bold**, *italic*, `code`
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # bold
    text = re.sub(r'\*([^*]+)\*', r'\1', text)      # italic
    text = re.sub(r'`([^`]+)`', r'\1', text)        # code
    
    # Remove code blocks
    text = re.sub(r'```[\s\S]*?```', '', text)
    
    # Remove JSON blocks
    text = re.sub(r'```json[\s\S]*?```', '', text)
    
    # Remove URLs and file paths (keep only the text before them)
    text = re.sub(r'\s*\([^)]*\.pdf[^)]*\)', '', text)  # Remove PDF links
    text = re.sub(r'\s*\([^)]*http[^)]*\)', '', text)   # Remove HTTP links
    text = re.sub(r'\s*\([^)]*www[^)]*\)', '', text)    # Remove WWW links
    
    # Handle escaped characters
    text = text.replace('\\\\', '\\')  # Double backslash to single
    text = text.replace('\\%', '%')    # Escaped percent to percent
    
    # Clean up extra whitespace and newlines
    text = re.sub(r'\n\s*\n', '\n', text)  # Multiple newlines to single
    text = re.sub(r'[ \t]+', ' ', text)    # Multiple spaces to single
    text = text.strip()
    
    # Remove common OCR artifacts
    text = re.sub(r'^\.$', '', text)  # Single dot
    text = re.sub(r'^[.\s]+$', '', text)  # Only dots and spaces
    
    return text

def preserve_table_content(text: str) -> str:
    """Preserve table content while cleaning other markdown elements."""
    if not text or text.strip() == '.':
        return ""
    
    # Remove markdown image syntax: ![alt](src)
    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', '', text)
    
    # Remove markdown headers (keep the text content)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    
    # Remove markdown links but keep the text: [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    
    # Remove markdown formatting: **bold**, *italic*, `code` (but preserve table structure)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # bold
    text = re.sub(r'\*([^*]+)\*', r'\1', text)      # italic
    text = re.sub(r'`([^`]+)`', r'\1', text)        # code
    
    # Remove code blocks (but preserve table blocks)
    text = re.sub(r'```(?!.*\|)[\s\S]*?```', '', text)  # Only remove non-table code blocks
    
    # Remove JSON blocks
    text = re.sub(r'```json[\s\S]*?```', '', text)
    
    # Remove URLs and file paths (keep only the text before them)
    text = re.sub(r'\s*\([^)]*\.pdf[^)]*\)', '', text)  # Remove PDF links
    text = re.sub(r'\s*\([^)]*http[^)]*\)', '', text)   # Remove HTTP links
    text = re.sub(r'\s*\([^)]*www[^)]*\)', '', text)    # Remove WWW links
    
    # Handle escaped characters - do this BEFORE general backslash conversion
    text = text.replace('\\%', '%')    # Escaped percent to percent
    
    # Clean up extra whitespace but preserve table structure
    # Only clean spaces within non-table lines
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        if line.strip().startswith('|') and line.strip().endswith('|'):
            # This is a table line, clean up escaped characters but preserve structure
            line = line.strip()
            # Convert \\n to actual newlines
            line = line.replace('\\n', '\n')
            # Convert \\$ to $ (handle this BEFORE general backslash conversion)
            line = line.replace('\\\\$', '$')
            # Convert \\ to \ (for other escaped characters)
            line = line.replace('\\\\', '\\')
            # Clean up any remaining extra spaces around pipes
            line = re.sub(r'\s*\|\s*', '|', line)
            # Add back proper spacing
            line = line.replace('|', ' | ')
            # Clean up the ends
            line = line.strip()
            cleaned_lines.append(line)
        else:
            # This is not a table line, clean up whitespace
            cleaned_line = re.sub(r'[ \t]+', ' ', line.strip())
            if cleaned_line:
                cleaned_lines.append(cleaned_line)
    
    text = '\n'.join(cleaned_lines)
    
    # Remove common OCR artifacts (but not from table lines)
    text = re.sub(r'^\.$', '', text, flags=re.MULTILINE)  # Single dot on its own line
    text = re.sub(r'^[.\s]+$', '', text, flags=re.MULTILINE)  # Only dots and spaces on its own line
    
    return text.strip()

def extract_table_markdown(text: str) -> str:
    """Extract only the table markdown content from text."""
    if not text:
        return ""
    
    # More flexible pattern to match markdown tables
    # This handles tables with or without separator rows
    table_pattern = re.compile(
        r"""(
            (?:^\|.*\|\s*\n)+
            (?:^\|(?:\s*:?-+:?\s*\|)+\s*\n)?
            (?:^\|.*\|\s*\n?)*
        )""",
        re.MULTILINE | re.VERBOSE
    )
    
    matches = table_pattern.findall(text)
    if matches:
        # Join all table matches with newlines, preserving structure
        tables = []
        for match in matches:
            if match.strip():
                # Clean up the table while preserving structure
                table_lines = match.strip().split('\n')
                cleaned_table_lines = []
                
                for line in table_lines:
                    line = line.strip()
                    if line.startswith('|') and line.endswith('|'):
                        # Clean up escaped characters in table lines
                        # Convert \\n to actual newlines
                        line = line.replace('\\n', '\n')
                        # Convert \\$ to $ (handle this BEFORE general backslash conversion)
                        line = line.replace('\\\\$', '$')
                        # Convert \\ to \ (for other escaped characters)
                        line = line.replace('\\\\', '\\')
                        # Clean up any remaining extra spaces
                        line = re.sub(r'\s*\|\s*', '|', line)
                        # Add back proper spacing
                        line = line.replace('|', ' | ')
                        # Clean up the ends
                        line = line.strip()
                        
                        cleaned_table_lines.append(line)
                
                if cleaned_table_lines:
                    tables.append('\n'.join(cleaned_table_lines))
                
        return '\n\n'.join(tables)
    
    return ""

def extract_image_names(text: str) -> List[str]:
    """Extract image names from markdown image syntax."""
    if not text:
        return []
    
    # Pattern to match markdown image syntax: ![alt](src)
    image_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
    matches = image_pattern.findall(text)
    
    if matches:
        # Extract image filenames from the src part
        image_names = []
        for alt_text, src in matches:
            # Get the filename from the src (handle both relative and absolute paths)
            filename = src.split('/')[-1]  # Get the last part of the path
            image_names.append(filename)
        
        return list(set(image_names))  # Remove duplicates
    
    return []

def extract_table_names(text: str) -> List[str]:
    """Extract table names from markdown table reference syntax."""
    if not text:
        return []
    
    # Pattern to match table reference syntax: <!--TABLE_REFERENCE: table-0-->
    table_pattern = re.compile(r'<!--TABLE_REFERENCE:\s*([^>]+)-->')
    matches = table_pattern.findall(text)
    
    if matches:
        # Extract table names from the reference
        table_names = []
        for match in matches:
            table_name = match.strip()
            if table_name:
                table_names.append(table_name)
        
        return list(set(table_names))  # Remove duplicates
    
    return []

async def fetch_table_data(file_id: str, table_names: List[str]) -> List[Dict[str, Any]]:
    """Fetch table data from Firebase FilesData collection."""
    if not table_names:
        return []
    
    # Fetch table data from FilesData collection
    file_data_collection = Collections.FILE_DATA.value
    table_data = await firebase_manager.query_collection(
        collection=file_data_collection,
        filters=[("file_id", "==", file_id), ("name", "in", table_names)]
    )
    
    # Extract table data from csv_data field
    tables = []
    for record in table_data:
        if record.get('csv_data'):
            tables.append({
                "id": record.get("id"), 
                'name': record.get('name', ''),
                'csv_data': record.get('csv_data', {}),
                'page_number': record.get('page_number', 0)
            })
    
    return tables

async def fetch_image_data(file_id: str, image_names: List[str]) -> List[Dict[str, Any]]:
    """Fetch base64 encoded images from Firebase FilesData collection."""
    if not image_names:
        return []
    
    # Fetch image data from FilesData collection
    file_data_collection = Collections.FILE_DATA.value
    image_data = await firebase_manager.query_collection(
        collection=file_data_collection,
        filters=[("file_id", "==", file_id), ("name", "in", image_names)]
    )
    
    # Extract base64 data from image_url field
    images = []
    for record in image_data:
        if record.get('image_url'):
            images.append({
                "id": record.get("id"), 
                'name': record.get('name', ''),
                'base64': record.get('image_url', ''),
                'type': record.get('type', ''),
                'size': record.get('size', 0),
                "page_number": record.get('page_number', 0)
            })
    
    return images

async def query_index(user_id: str, index_name: str, query: str, filters: Dict[str, Any], limit: int, offset: int) -> List[Dict[str, Any]]:
    """Query the vector index for relevant documents based on index type."""
    
    # Ensure filters is always a dictionary
    if not filters:
        filters = {"user_id": {"$eq": user_id}}
    else:
        filters["user_id"] = {"$eq": user_id}

    # Handle different index types by applying appropriate filters
    if index_name == "tables":
        filters["has_table"] = {"$eq": True}
    elif index_name == "images":
        filters["has_image"] = {"$eq": True}
    elif index_name == "curated_qas":
        filters["type"] = {"$eq": "curated_qa"}
    # For "documents" or any other index_name, no additional filters needed

    # VECTOR_DB_NAME = "magic-dossier-pdfs"
    print(f"Searching {index_name} with query: '{query}'")
    
    vectorization_service = VectorizationService()
    results = await vectorization_service.query_context(query, filters, aggregation=False, top_k=limit)
    print(f"Found {len(results) if results else 0} raw results from vector database")
    
    # Ensure results is always a list
    if not results:
        print("No results returned from vectorization service")
        return []
    
    # Convert Pinecone ScoredVector objects to dictionaries
    formatted_results = []
    for result in results:
        # Filter out results with null or zero scores
        if result.score is None or result.score <= 0:
            continue
            
        formatted_result = {
            'id': result.id,
            'title': result.metadata.get('title', ''), 
            'metadata': result.metadata,
            'score': result.score,
            'values': getattr(result, 'values', [])
        }
        formatted_results.append(formatted_result)
    
    print(f"Returning {len(formatted_results)} results after score filtering")
    return formatted_results

def is_meaningful_text(text: str, min_length: int = 10) -> bool:
    """Check if text is meaningful (not empty, not just gibberish)."""
    if not text or len(text.strip()) < min_length:
        return False
    
    # Remove common non-meaningful patterns
    cleaned = text.strip()
    
    # Check if it's just repeated characters or symbols
    if len(set(cleaned)) < 3:  # Too few unique characters
        return False
    
    # For table content, be more lenient with the alphabetic character requirement
    # Tables often contain numbers, symbols, and formatting
    alpha_chars = sum(1 for c in cleaned if c.isalpha())
    total_chars = len(cleaned)
    
    # If it's mostly table-like content (contains pipes), be more lenient
    if '|' in cleaned:
        # For tables, require at least 10% alphabetic or 20% alphanumeric
        alphanumeric_chars = sum(1 for c in cleaned if c.isalnum())
        return alpha_chars >= total_chars * 0.1 or alphanumeric_chars >= total_chars * 0.2
    else:
        # For regular text, require 30% alphabetic characters
        if alpha_chars < total_chars * 0.3:
            return False
    
    # Check if it's just numbers and symbols (but allow for table formatting)
    if '|' not in cleaned and not any(c.isalpha() for c in cleaned):
        return False
    
    return True

async def format_search_results_with_file_metadata(search_results: List[Dict[str, Any]], content_type: str = "document", order_by: Optional[dict] = None) -> List[Dict[str, Any]]:
    """Format search results by grouping chunks by file ID and aggregating content."""
    if not search_results:
        return []
    
    print(f"Formatting {len(search_results)} search results for {content_type} content")
    
    # Choose the appropriate text cleaning function
    if content_type == "table":
        clean_function = preserve_table_content
    else:
        clean_function = clean_markdown_text
    
    # Group search results by file_id
    file_groups = {}
    for result in search_results:
        # Skip results with null or zero scores
        score = result.get('score', 0.0)
        if score is None or score <= 0.1:
            continue
            
        file_id = result.get('metadata', {}).get('file_id')
        if not file_id:
            continue
            
        if file_id not in file_groups:
            file_groups[file_id] = {
                'chunks': [],
                'highest_score': 0.0,
                'all_pages': set(),
                'all_text': [],
                'all_tables': [],  # Add table content collection
                'all_image_names': set(),  # Add image names collection for fetching
                'all_table_names': set(),  # Add table names collection for fetching
                'all_curated_qas': []  # Add curated qa names collection for fetching
            }
        
        # Add chunk to group
        file_groups[file_id]['chunks'].append(result)
        
        # Track highest score
        if score > file_groups[file_id]['highest_score']:
            file_groups[file_id]['highest_score'] = score
        
        # Collect pages and text
        metadata = result.get('metadata', {})
        
        # Handle page_numbers (plural) from vector database
        if metadata.get('page_numbers'):
            for page in metadata['page_numbers']:
                file_groups[file_id]['all_pages'].add(page)
        elif metadata.get('page_number'):  # Fallback to singular
            file_groups[file_id]['all_pages'].add(metadata['page_number'])
        
        # Handle text content
        if metadata.get('text'):
            # Clean the text using the appropriate function
            cleaned_text = clean_function(metadata['text'])
            if cleaned_text and is_meaningful_text(cleaned_text):  # Only add meaningful cleaned text
                file_groups[file_id]['all_text'].append(cleaned_text)
                
                # Extract table content if this is a table search
                if content_type == "table":
                    table_content = extract_table_markdown(metadata['text'])
                    if table_content:  # Only check if table content exists, not if it's meaningful
                        file_groups[file_id]['all_tables'].append(table_content)
                    
                    # Extract table names for fetching from Firebase
                    table_names = extract_table_names(metadata['text'])
                    if table_names:
                        file_groups[file_id]['all_table_names'].update(table_names)
                
                # Extract image names if this is an image search
                if content_type == "image":
                    image_names = extract_image_names(metadata['text'])
                    if image_names:
                        file_groups[file_id]['all_image_names'].update(image_names)

                if content_type == "curated_qa":
                    file_groups[file_id]['all_curated_qas'].append({
                        "id": metadata.get("id"),
                        "kh_item_id": metadata.get("kh_item_id"),
                        "question": metadata.get("question"),
                        "page_number": [int(page.split("_")[-1]) for page in metadata.get("page_numbers", [])][0] if metadata.get("page_numbers") else None,
                        "answer": metadata.get("answer"),
                        "reference": metadata.get("reference"),
                        "created_at": metadata.get("created_at")
                    })
    
    print(f"Grouped into {len(file_groups)} file groups")
    
    # Check if we have any file groups after filtering
    if not file_groups:
        print("No file groups found after score filtering")
        return []
    
    # Extract unique file IDs
    file_ids = list(file_groups.keys())
    
    # Fetch file documents from Firebase
    file_documents = await firebase_manager.get_documents(
        collection=Collections.FILE, 
        list_ids=file_ids
    )
    
    # Create a mapping of file_id to file data for quick lookup
    file_map = {doc['id']: doc for doc in file_documents}
    
    # Format aggregated results
    formatted_results = []
    for file_id, group_data in file_groups.items():
        file_data = file_map.get(file_id, {})
        
        # Convert timestamp to readable date if available
        upload_date = file_data.get('created_at') or file_data.get('created_at') or 0

        # Sort pages and join text
        sorted_pages = sorted(list(group_data['all_pages']))
        concatenated_text = ' '.join(group_data['all_text'])
        
        # Join table content
        concatenated_tables = '\n\n'.join(group_data['all_tables'])
        
        # Get table names
        table_names = sorted(list(group_data['all_table_names']))
        
        # Get image names
        image_names = sorted(list(group_data['all_image_names']))
        
        # Skip files with no meaningful content
        has_meaningful_content = (
            (concatenated_text and is_meaningful_text(concatenated_text)) or
            (content_type == "table" and concatenated_tables) or  # Just check if table content exists
            (content_type == "image" and image_names)
        )
        
        if not has_meaningful_content:
            continue
        
        formatted_result = {
            'id': file_id,
            'title': file_data.get('name', 'Unknown'),
            'url': file_data.get('url', ''),
            'upload_date': upload_date,
            'score': group_data['highest_score'],
            'pages': sorted_pages,
            'text': concatenated_text,
            'chunk_count': len(group_data['chunks']),
            'metadata': {
                'file_id': file_id,
                'name': file_data.get('name'),
                'pages_found': sorted_pages,
                'total_chunks': len(group_data['chunks']),
                'content_type': content_type
            }
        }
        
        # Add user_id to formatted result if present in metadata
        if file_data.get('user_id'):
            formatted_result['user_id'] = file_data['user_id']
        
        # Add table field for table searches
        if content_type == "table":
            formatted_result['table'] = concatenated_tables
            
            # Fetch actual table data from Firebase if table names are found
            if table_names:
                table_data = await fetch_table_data(file_id, table_names)
                formatted_result['table_data'] = table_data
        
        # Add images field for image searches
        if content_type == "image" and image_names:
            # Fetch actual image data from Firebase
            image_data = await fetch_image_data(file_id, image_names)
            formatted_result['images'] = image_data
        
        if content_type == "curated_qa":
            formatted_result['curated_qas'] = group_data['all_curated_qas']
        
        formatted_results.append(formatted_result)
    
    # Sort results by order_by dict if provided, else by score descending
    
    if order_by and isinstance(order_by, dict):
        order_field, order_dir = next(iter(order_by.items()))
        reverse = order_dir.lower() == "desc"
        formatted_results.sort(
            key=lambda x: x.get(order_field, 0),
            reverse=reverse
        )
    else:
        formatted_results.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    print(f"Returning {len(formatted_results)} formatted results")
    return formatted_results
