import re
import base64
from PIL import Image
from io import BytesIO
import pandas as pd
from typing import Optional, Dict
from app.config.llm_factory import LLMFactory, LLMModel
from app.models.images_models import ImageAnalysisResult
from langchain_core.messages import HumanMessage


def extract_context_around_image_id(
    markdown: str,
    image_id: str,
    context_chars: int = 150
) -> Optional[Dict[str, str]]:
    """
    Extract context and metadata for a given image ID in markdown.

    Args:
        markdown (str): Full markdown text.
        image_id (str): Image filename or unique identifier (e.g., 'img-3.jpeg').
        context_chars (int): Number of characters before and after to return as context.

    Returns:
        Dict[str, str] if found, else None.
    """
    # Regex to match markdown image syntax: ![alt](src)
    pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')

    for match in pattern.finditer(markdown):
        alt_text, src = match.group(1), match.group(2)

        if image_id in src:
            start, end = match.span()

            context_before = markdown[max(0, start - context_chars):start].strip()
            context_after = markdown[end:min(len(markdown), end + context_chars)].strip()

            return {
                "alt_text": alt_text,
                "src": src,
                "context_before": context_before,
                "context_after": context_after
            }

    return None  # If image ID not found

async def convert_image_to_structured_output(image_base64: str, context: str = None, llm_model: LLMModel = LLMModel.GEMINI_2_FLASH)->ImageAnalysisResult:
    prompt = """You are an expert visual document analyst.
Given an image extracted from a document, analyze it carefully and provide the following structured information
"""
    if context:
        prompt += f"\n\nContext of the document: {context}"
    ImageAnalyser = LLMFactory.get_llm_with_structured_output(llm_model, ImageAnalysisResult)
    result = await ImageAnalyser.ainvoke([HumanMessage(
        content=[
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": image_base64}
        ]
    )])
    return result 


def maybe_compress_base64_image(data_uri: str, quality: int = 60, size_threshold_mb: float = 0.9) -> str:
    """Compress base64 image only if size > size_threshold_mb."""
    # Extract MIME type and base64 data
    match = re.match(r"data:(image/\w+);base64,(.*)", data_uri)
    if not match:
        raise ValueError("Invalid data URI format")

    mime_type, base64_data = match.groups()
    image_bytes = base64.b64decode(base64_data)

    # Check size
    size_mb = len(image_bytes) / (1024 * 1024) 
    
    if size_mb <= size_threshold_mb:
        return data_uri  # No compression needed

    # Open image with PIL
    with Image.open(BytesIO(image_bytes)) as img:
        print(f"Original image dimensions: {img.size}")
        
        # Convert to RGB if needed
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            print(f"Converted image mode from {img.mode} to RGB")

        # Try compression with quality first
        output = BytesIO()
        img.save(output, format="JPEG", quality=quality, optimize=True)
        compressed_data = output.getvalue()
        compressed_size_mb = len(compressed_data) / (1024 * 1024)
        
        print(f"Compressed size with quality {quality}: {compressed_size_mb:.2f} MB")
        
        # If still too large, try resizing
        if compressed_size_mb > size_threshold_mb:
            print("Still too large, attempting to resize...")
            
            # Calculate new dimensions to reduce size by ~50%
            scale_factor = 0.8  # Start with 80% of original size
            new_width = int(img.width * scale_factor)
            new_height = int(img.height * scale_factor)
            
            # Keep trying smaller sizes until we get under the threshold
            max_attempts = 5
            attempt = 0
            
            while compressed_size_mb > size_threshold_mb and attempt < max_attempts:
                resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                output = BytesIO()
                resized_img.save(output, format="JPEG", quality=quality, optimize=True)
                compressed_data = output.getvalue()
                compressed_size_mb = len(compressed_data) / (1024 * 1024)
                
                print(f"Attempt {attempt + 1}: Resized to {new_width}x{new_height}, size: {compressed_size_mb:.2f} MB")
                
                if compressed_size_mb > size_threshold_mb:
                    # Further reduce dimensions
                    scale_factor *= 0.8
                    new_width = int(img.width * scale_factor)
                    new_height = int(img.height * scale_factor)
                    attempt += 1
                else:
                    break
            
            if compressed_size_mb > size_threshold_mb:
                print(f"Warning: Could not compress below {size_threshold_mb} MB threshold. Final size: {compressed_size_mb:.2f} MB")

    # Encode back to base64
    compressed_base64 = base64.b64encode(compressed_data).decode("utf-8")
    final_data_uri = f"data:image/jpeg;base64,{compressed_base64}"
    
    # Verify final size
    final_size_mb = len(compressed_base64) * 3/4 / (1024 * 1024)  # Account for base64 encoding overhead
    print(f"Final compressed image size: {final_size_mb:.2f} MB")
    
    return final_data_uri