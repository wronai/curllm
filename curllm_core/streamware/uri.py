"""
StreamwareURI - URI parsing and handling for component routing
"""

from typing import Any, Dict, Optional
from urllib.parse import urlparse, parse_qs, unquote
from .exceptions import URIError


class StreamwareURI:
    """
    Parse and handle Streamware URIs
    
    Format: scheme://operation?param1=value1&param2=value2
    
    Examples:
        curllm://browse?url=https://example.com&visual=true
        http://api.example.com/data?method=post
        file://write?path=/tmp/output.json
    """
    
    def __init__(self, uri: str):
        self.original = uri
        self._parse(uri)
        
    def _parse(self, uri: str):
        """Parse URI into components"""
        try:
            parsed = urlparse(uri)
            
            self.scheme = parsed.scheme
            self.netloc = parsed.netloc
            self.path = parsed.path.lstrip('/')
            # Operation can be netloc (curllm://browse?...) or path (curllm:///browse?...)
            self.operation = self.netloc or self.path or None
            
            # Parse query parameters
            self.params = {}
            if parsed.query:
                query_params = parse_qs(parsed.query)
                # Flatten single-value lists
                for key, values in query_params.items():
                    if len(values) == 1:
                        # Try to convert to appropriate type
                        value = unquote(values[0])
                        self.params[key] = self._convert_value(value)
                    else:
                        self.params[key] = [unquote(v) for v in values]
                        
        except Exception as e:
            raise URIError(f"Invalid URI format: {uri}") from e
            
    def _convert_value(self, value: str) -> Any:
        """Convert string value to appropriate type"""
        # Boolean conversion
        if value.lower() in ('true', 'yes', '1'):
            return True
        elif value.lower() in ('false', 'no', '0'):
            return False
            
        # Numeric conversion
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass
            
        # Return as string
        return value
        
    def get_param(self, key: str, default: Any = None) -> Any:
        """Get parameter value with default"""
        return self.params.get(key, default)
        
    def has_param(self, key: str) -> bool:
        """Check if parameter exists"""
        return key in self.params
        
    def set_param(self, key: str, value: Any):
        """Set parameter value"""
        self.params[key] = value
        
    def get_full_url(self) -> str:
        """Get full URL (for http/https schemes)"""
        if self.scheme in ('http', 'https'):
            url = f"{self.scheme}://{self.netloc}{self.path}"
            return url
        return None
        
    def __str__(self) -> str:
        return self.original
        
    def __repr__(self) -> str:
        return f"StreamwareURI('{self.original}')"
