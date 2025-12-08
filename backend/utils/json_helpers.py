# Kunwar - 29604570

"""
JSON parsing helpers for handling Gemini responses
"""
import json
import re
from typing import Any, Optional
import structlog

logger = structlog.get_logger()


def extract_json_from_markdown(text: str) -> Optional[str]:
    """
    Extract JSON from markdown code blocks
    
    Handles formats like:
    ```json
    {...}
    ```
    
    or just {...}
    """
    if not text:
        return None
    
    # Try to find JSON in markdown code blocks
    patterns = [
        r'```json\s*\n(.*?)\n```',  # ```json ... ```
        r'```\s*\n(.*?)\n```',       # ``` ... ```
        r'`(.*?)`',                   # `...`
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
    
    # Try to find JSON by locating { and }
    if '{' in text and '}' in text:
        start = text.find('{')
        end = text.rfind('}') + 1
        if start < end:
            return text[start:end].strip()
    
    # If no markdown found, return original text
    return text.strip()


def parse_json_response(text: str, logger_context: str = "json_parse_error", fallback: Any = None) -> Any:
    """
    Parse JSON from text, handling markdown wrapping and errors gracefully
    
    Args:
        text: Text that may contain JSON
        logger_context: Context string for logging errors
        fallback: Value to return if parsing fails
    
    Returns:
        Parsed JSON or fallback value
    
    Raises:
        ValueError: If parsing fails and no fallback is provided
    """
    if not text:
        logger.warning(f"{logger_context}_empty_text")
        if fallback is None:
            raise ValueError("Empty JSON text received")
        return fallback
    
    # Extract JSON from markdown if present
    json_text = extract_json_from_markdown(text)
    
    if not json_text:
        logger.warning(f"{logger_context}_no_json_found")
        if fallback is None:
            raise ValueError("No JSON found in text")
        return fallback
    
    # Try to parse JSON
    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        logger.error(logger_context, 
                    error=str(e),
                    text_preview=json_text[:200])
        if fallback is None:
            raise ValueError(f"JSON parsing failed: {e}")
        return fallback


def clean_json_string(text: str) -> str:
    """
    Clean JSON string by removing common parsing issues.
    Handles BOM characters, escaped newlines, and trailing commas
    that often appear in LLM-generated JSON.
    """
    if not text:
        return text
    
    # Remove BOM
    text = text.replace('\ufeff', '')
    
    # Remove trailing commas before } or ]
    text = re.sub(r',(\s*[}\]])', r'\1', text)
    
    # Fix common escape issues
    text = text.replace('\\n', '\n')
    
    return text.strip()

