#!/usr/bin/env python3
"""
Test script for the text cleaning function
"""

import re

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

# Test cases based on the user's sample data
test_cases = [
    {
        "name": "onsemi PDF with images",
        "input": "# onsemi SiC Solutions\n## Featured solutions\n![img-0.jpeg](img-0.jpeg)\n![img-2.jpeg](img-2.jpeg)",
        "expected": "onsemi SiC Solutions\nFeatured solutions"
    },
    {
        "name": "Single dot OCR artifact",
        "input": ".",
        "expected": ""
    },
    {
        "name": "Molex PDF with repeated content",
        "input": "## Mini50 Connection Systems\nAchieve 50\\% space savings over traditional USCAR 0.64 mm connectors with sealed or unsealed Mini50 single- and dual-row receptacles, with smaller terminals to fit more low-current electrical circuits in interior transportation-vehicle environments.  \nD Download datasheet (/wcm/connect/be69b66e-4639-473a-9faf6de9b3db80ff/987651-6273.pdf?\nMOD=AJPERES\\&CVID=o0Ncsfl\\&attachment=false\\&id=1650371936801)",
        "expected": "Mini50 Connection Systems\nAchieve 50% space savings over traditional USCAR 0.64 mm connectors with sealed or unsealed Mini50 single- and dual-row receptacles, with smaller terminals to fit more low-current electrical circuits in interior transportation-vehicle environments.\nD Download datasheet"
    },
    {
        "name": "ELECTROMECHANICAL with image",
        "input": "# ELECTROMECHANICAL\n![img-4.jpeg](img-4.jpeg)",
        "expected": "ELECTROMECHANICAL"
    }
]

def run_tests():
    print("Testing text cleaning function...\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}: {test_case['name']}")
        print(f"Input: {repr(test_case['input'])}")
        
        result = clean_markdown_text(test_case['input'])
        print(f"Output: {repr(result)}")
        print(f"Expected: {repr(test_case['expected'])}")
        
        # Simple comparison (ignoring whitespace differences)
        if result.strip() == test_case['expected'].strip():
            print("✅ PASS")
        else:
            print("❌ FAIL")
        print("-" * 80)

if __name__ == "__main__":
    run_tests() 