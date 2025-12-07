"""
Text and HTML Sanitization

Clean and normalize text from DOM to prevent parsing errors.
"""

import re
import html
from typing import Optional


def sanitize_text(text: Optional[str], max_length: int = 10000) -> str:
    """
    Sanitize text for safe processing.
    
    - Handles None/non-string inputs
    - Decodes HTML entities
    - Normalizes whitespace
    - Removes control characters
    - Truncates to max length
    
    Args:
        text: Input text (may be None or non-string)
        max_length: Maximum output length
        
    Returns:
        Clean text string (never None)
    """
    # Handle None and non-string
    if text is None:
        return ""
    
    if not isinstance(text, str):
        try:
            text = str(text)
        except Exception:
            return ""
    
    # Decode HTML entities
    try:
        text = html.unescape(text)
    except Exception:
        pass
    
    # Remove control characters (except newline, tab)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    
    # Normalize unicode whitespace
    text = text.replace('\xa0', ' ')  # Non-breaking space
    text = text.replace('\u200b', '')  # Zero-width space
    text = text.replace('\u200c', '')  # Zero-width non-joiner
    text = text.replace('\u200d', '')  # Zero-width joiner
    text = text.replace('\ufeff', '')  # BOM
    
    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # Truncate
    if len(text) > max_length:
        text = text[:max_length]
    
    return text


def sanitize_html(html_content: Optional[str], max_length: int = 50000) -> str:
    """
    Sanitize HTML content for parsing.
    
    Args:
        html_content: Raw HTML
        max_length: Maximum length
        
    Returns:
        Cleaned HTML string
    """
    if not html_content:
        return ""
    
    if not isinstance(html_content, str):
        try:
            html_content = str(html_content)
        except Exception:
            return ""
    
    # Remove script and style content (they can cause parsing issues)
    html_content = re.sub(
        r'<script[^>]*>.*?</script>',
        '', html_content, flags=re.IGNORECASE | re.DOTALL
    )
    html_content = re.sub(
        r'<style[^>]*>.*?</style>',
        '', html_content, flags=re.IGNORECASE | re.DOTALL
    )
    
    # Remove HTML comments
    html_content = re.sub(r'<!--.*?-->', '', html_content, flags=re.DOTALL)
    
    # Truncate
    if len(html_content) > max_length:
        html_content = html_content[:max_length]
    
    return html_content


def normalize_whitespace(text: Optional[str]) -> str:
    """
    Normalize all whitespace to single spaces.
    
    Args:
        text: Input text
        
    Returns:
        Text with normalized whitespace
    """
    if not text:
        return ""
    
    # Replace all whitespace sequences with single space
    return ' '.join(text.split())


def strip_html_tags(text: Optional[str]) -> str:
    """
    Remove all HTML tags from text.
    
    Args:
        text: Text possibly containing HTML
        
    Returns:
        Text without HTML tags
    """
    if not text:
        return ""
    
    # Remove tags
    clean = re.sub(r'<[^>]+>', ' ', text)
    
    # Decode entities
    clean = html.unescape(clean)
    
    # Normalize whitespace
    return normalize_whitespace(clean)


def extract_visible_text(html_content: Optional[str]) -> str:
    """
    Extract only visible text from HTML.
    
    Removes:
    - Script/style content
    - HTML tags
    - Hidden elements
    
    Args:
        html_content: HTML string
        
    Returns:
        Visible text content
    """
    if not html_content:
        return ""
    
    # Remove non-visible elements
    content = sanitize_html(html_content)
    
    # Remove noscript
    content = re.sub(
        r'<noscript[^>]*>.*?</noscript>',
        '', content, flags=re.IGNORECASE | re.DOTALL
    )
    
    # Remove hidden elements (common patterns)
    content = re.sub(
        r'<[^>]+(?:display\s*:\s*none|visibility\s*:\s*hidden)[^>]*>.*?</[^>]+>',
        '', content, flags=re.IGNORECASE | re.DOTALL
    )
    
    # Strip remaining tags
    return strip_html_tags(content)


def safe_encode(text: Optional[str], encoding: str = 'utf-8') -> bytes:
    """
    Safely encode text to bytes, handling encoding errors.
    
    Args:
        text: Text to encode
        encoding: Target encoding
        
    Returns:
        Encoded bytes
    """
    if not text:
        return b""
    
    try:
        return text.encode(encoding, errors='replace')
    except Exception:
        return b""


def safe_decode(data: Optional[bytes], encoding: str = 'utf-8') -> str:
    """
    Safely decode bytes to text, handling encoding errors.
    
    Args:
        data: Bytes to decode
        encoding: Source encoding
        
    Returns:
        Decoded text
    """
    if not data:
        return ""
    
    # Try specified encoding
    try:
        return data.decode(encoding, errors='replace')
    except Exception:
        pass
    
    # Try common encodings
    for enc in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
        try:
            return data.decode(enc, errors='replace')
        except Exception:
            continue
    
    return ""


def truncate_smart(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text at word boundary.
    
    Args:
        text: Text to truncate
        max_length: Maximum length (including suffix)
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text or ""
    
    # Truncate to max length minus suffix
    truncate_at = max_length - len(suffix)
    if truncate_at <= 0:
        return suffix[:max_length]
    
    truncated = text[:truncate_at]
    
    # Find last word boundary
    last_space = truncated.rfind(' ')
    if last_space > truncate_at * 0.7:  # Don't cut too much
        truncated = truncated[:last_space]
    
    return truncated.rstrip() + suffix
