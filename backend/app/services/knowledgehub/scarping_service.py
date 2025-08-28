# services/scraper.py
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from urllib.parse import urlparse
import time
import random

def fetch_and_convert_to_markdown(url: str, timeout: int = 15) -> dict:
    """
    Fetch a web page and convert it to markdown format.
    
    Args:
        url: The URL to scrape
        timeout: Request timeout in seconds
        
    Returns:
        Dictionary with scraping results
    """
    try:
        # Add headers to mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Add a small delay to be respectful to servers
        time.sleep(random.uniform(0.5, 1.5))
        
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status()

        # Check if content is HTML
        content_type = response.headers.get('content-type', '').lower()
        if 'text/html' not in content_type:
            return {
                "url": url,
                "status": "failed",
                "error": f"Content type not supported: {content_type}"
            }

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove unnecessary tags that don't contribute to content
        for tag in soup(["script", "style", "noscript", "iframe", "nav", "footer", "header", "aside"]):
            tag.decompose()

        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, str) and text.strip().startswith('<!--')):
            comment.extract()

        # Try to find the main content area
        main_content = None
        
        # Look for common content containers
        for selector in ['main', 'article', '.content', '.main-content', '#content', '#main']:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        # If no main content found, use body
        if not main_content:
            main_content = soup.body or soup

        # Extract title
        title_tag = soup.find('title')
        title = title_tag.get_text().strip() if title_tag else urlparse(url).netloc

        # Convert to markdown
        markdown = md(str(main_content), heading_style="ATX", bullets="-")
        
        # Clean up the markdown
        markdown = clean_markdown_content(markdown)
        
        return {
            "url": url,
            "status": "success",
            "markdown": markdown,
            "title": title,
            "content_length": len(markdown)
        }

    except requests.exceptions.Timeout:
        return {
            "url": url,
            "status": "failed",
            "error": "Request timeout"
        }
    except requests.exceptions.ConnectionError:
        return {
            "url": url,
            "status": "failed",
            "error": "Connection error"
        }
    except requests.exceptions.HTTPError as e:
        return {
            "url": url,
            "status": "failed",
            "error": f"HTTP error: {e.response.status_code}"
        }
    except Exception as e:
        return {
            "url": url,
            "status": "failed",
            "error": str(e)
        }

def clean_markdown_content(markdown: str) -> str:
    """
    Clean and format markdown content for better readability.
    
    Args:
        markdown: Raw markdown content
        
    Returns:
        Cleaned markdown content
    """
    if not markdown:
        return ""
    
    # Remove excessive whitespace
    lines = markdown.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Remove excessive whitespace
        line = line.strip()
        
        # Skip empty lines at the beginning
        if not cleaned_lines and not line:
            continue
            
        # Add non-empty lines
        if line:
            cleaned_lines.append(line)
        # Add single empty line between content
        elif cleaned_lines and cleaned_lines[-1]:
            cleaned_lines.append("")
    
    # Remove trailing empty lines
    while cleaned_lines and not cleaned_lines[-1]:
        cleaned_lines.pop()
    
    return '\n'.join(cleaned_lines)

def validate_url(url: str) -> bool:
    """
    Validate if a URL is properly formatted.
    
    Args:
        url: URL to validate
        
    Returns:
        True if URL is valid, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def extract_domain(url: str) -> str:
    """
    Extract domain from URL.
    
    Args:
        url: URL to extract domain from
        
    Returns:
        Domain name
    """
    try:
        return urlparse(url).netloc
    except Exception:
        return ""
