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
            
        method = self._get_method(data)
        headers = self._build_headers(data)
        timeout = self.uri.get_param('timeout', 30)
        json_payload = data if isinstance(data, dict) and 'method' not in data else None
        
        try:
            logger.debug(f"HTTP {method.upper()} {url}")
            
            request_map = {
                'get': lambda: requests.get(url, headers=headers, timeout=timeout),
                'delete': lambda: requests.delete(url, headers=headers, timeout=timeout),
                'post': lambda: requests.post(url, json=json_payload, headers=headers, timeout=timeout),
                'put': lambda: requests.put(url, json=json_payload, headers=headers, timeout=timeout),
                'patch': lambda: requests.patch(url, json=json_payload, headers=headers, timeout=timeout),
            }
            sender = request_map.get(method)
            if not sender:
                raise ComponentError(f"Unsupported HTTP method: {method}")
            
            response = sender()
                
            response.raise_for_status()
            
            return self._parse_response(response)
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"HTTP request failed: {e}") from e
        except json.JSONDecodeError as e:
            # Return text if JSON decode fails
            return response.text

    def _get_method(self, data: Any) -> str:
        method = self.uri.get_param('method', 'get').lower()
        if isinstance(data, dict) and 'method' in data:
            method = data['method'].lower()
        return method

    def _build_headers(self, data: Any) -> Dict[str, Any]:
        headers: Dict[str, Any] = {}
        for key, value in self.uri.params.items():
            if key.startswith('header_'):
                header_name = key[7:].replace('_', '-').title()
                headers[header_name] = value
        if isinstance(data, dict) and 'headers' in data:
            headers.update(data['headers'])
        return headers

    def _parse_response(self, response: requests.Response) -> Any:
        content_type = response.headers.get('Content-Type', '')
        if 'application/json' in content_type:
            return response.json()
        if 'text/' in content_type:
            return response.text
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "content": response.text[:1000],  # First 1KB
        }


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
