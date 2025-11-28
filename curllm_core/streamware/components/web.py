"""
Web/HTTP components for simple requests
"""

import json
import requests
from typing import Any, Dict, Optional
from ..core import Component
from ..uri import StreamwareURI
from ..registry import register
from ..exceptions import ComponentError, ConnectionError
from ...diagnostics import get_logger

logger = get_logger(__name__)


@register("http")
@register("https")
class HTTPComponent(Component):
    """
    HTTP/HTTPS component for web requests
    
    URI format:
        http://host/path?method=get&header_key=value
        https://api.example.com/endpoint?method=post
        
    Methods:
        - get (default)
        - post
        - put
        - delete
        - patch
    """
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def process(self, data: Any) -> Any:
        """Make HTTP request"""
        # Build URL from URI
        url = self.uri.get_full_url()
        if not url:
            raise ComponentError("Invalid HTTP URL")
            
        # Get method from params or data
        method = self.uri.get_param('method', 'get').lower()
        if isinstance(data, dict) and 'method' in data:
            method = data['method'].lower()
            
        # Get headers
        headers = {}
        for key, value in self.uri.params.items():
            if key.startswith('header_'):
                header_name = key[7:].replace('_', '-').title()
                headers[header_name] = value
                
        if isinstance(data, dict) and 'headers' in data:
            headers.update(data['headers'])
            
        # Get timeout
        timeout = self.uri.get_param('timeout', 30)
        
        try:
            logger.debug(f"HTTP {method.upper()} {url}")
            
            if method == 'get':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'post':
                json_data = data if isinstance(data, dict) and 'method' not in data else None
                response = requests.post(url, json=json_data, headers=headers, timeout=timeout)
            elif method == 'put':
                json_data = data if isinstance(data, dict) and 'method' not in data else None
                response = requests.put(url, json=json_data, headers=headers, timeout=timeout)
            elif method == 'delete':
                response = requests.delete(url, headers=headers, timeout=timeout)
            elif method == 'patch':
                json_data = data if isinstance(data, dict) and 'method' not in data else None
                response = requests.patch(url, json=json_data, headers=headers, timeout=timeout)
            else:
                raise ComponentError(f"Unsupported HTTP method: {method}")
                
            response.raise_for_status()
            
            # Try to return JSON if possible
            content_type = response.headers.get('Content-Type', '')
            if 'application/json' in content_type:
                return response.json()
            elif 'text/' in content_type:
                return response.text
            else:
                return {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "content": response.text[:1000],  # First 1KB
                }
                
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"HTTP request failed: {e}") from e
        except json.JSONDecodeError as e:
            # Return text if JSON decode fails
            return response.text


@register("web")
class WebComponent(HTTPComponent):
    """
    Alias for HTTPComponent for convenience
    
    URI format:
        web://get?url=https://example.com
        web://post?url=https://api.example.com/data
    """
    
    def process(self, data: Any) -> Any:
        """Make web request"""
        # Get URL from params or data
        url = self.uri.get_param('url')
        if not url and isinstance(data, dict):
            url = data.get('url')
            
        if not url:
            raise ComponentError("No URL specified for web request")
            
        # Create HTTP URI
        method = self.uri.operation or 'get'
        
        # Build new URI for HTTPComponent
        from ..uri import StreamwareURI
        http_uri_str = f"https://{url}" if not url.startswith('http') else url
        
        # Add method as parameter
        if '?' in http_uri_str:
            http_uri_str += f"&method={method}"
        else:
            http_uri_str += f"?method={method}"
            
        # Forward other params
        for key, value in self.uri.params.items():
            if key != 'url':
                http_uri_str += f"&{key}={value}"
                
        # Create HTTP component and process
        http_uri = StreamwareURI(http_uri_str)
        self.uri = http_uri
        
        return super().process(data)
