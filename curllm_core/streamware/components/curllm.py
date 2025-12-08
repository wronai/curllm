"""
CurLLM Component - Web automation with LLM integration for Streamware
"""

import json
import re
from typing import Any, Optional, Dict, Iterator, Callable
from ..core import Component, StreamComponent
from ..uri import StreamwareURI
from ..registry import register
from ..exceptions import ComponentError
from ...diagnostics import get_logger
from ...executor import CurllmExecutor
from ...config import config

logger = get_logger(__name__)

MIME_JSON = "application/json"


@register("curllm")
class CurLLMComponent(Component):
    """
    CurLLM component for web automation with LLM
    
    URI format:
        curllm://action?url=https://example.com&param=value
        
    Actions:
        - browse: Navigate to URL and interact with page
        - extract: Extract data using LLM instructions
        - fill_form: Fill forms using provided data
        - screenshot: Take screenshot
        - bql: Execute BQL (Browser Query Language)
        - execute: Direct executor call
    """
    
    input_mime = MIME_JSON
    output_mime = MIME_JSON
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.action = uri.operation or uri.path or "browse"
        self.executor = None
        
    def _get_executor(self) -> CurllmExecutor:
        """Get or create executor instance"""
        if not self.executor:
            self.executor = CurllmExecutor()
        return self.executor
        
    def process(self, data: Any) -> Any:
        """Process data based on CurLLM action"""
        action_map: Dict[str, Callable[[Any], Any]] = {
            "browse": self._browse,
            "extract": self._extract,
            "fill_form": self._fill_form,
            "screenshot": self._screenshot,
            "bql": self._execute_bql,
            "execute": self._execute,
        }
        handler = action_map.get(self.action)
        if not handler:
            raise ComponentError(f"Unknown CurLLM action: {self.action}")
        return handler(data)
            
    def _browse(self, data: Any) -> Dict[str, Any]:
        """Browse to URL and interact with page"""
        url = self.uri.get_param('url')
        if not url and isinstance(data, dict):
            url = data.get('url')
        if not url:
            raise ComponentError("No URL specified for browsing")
            
        # Build request payload
        request_data = {
            "url": url,
            "params": {
                "visual_mode": self.uri.get_param('visual', False),
                "stealth_mode": self.uri.get_param('stealth', False),
                "captcha_solver": self.uri.get_param('captcha', False),
            }
        }
        
        # Add instruction if provided
        instruction = self.uri.get_param('instruction')
        if instruction:
            request_data["data"] = instruction
        elif isinstance(data, dict) and 'instruction' in data:
            request_data["data"] = data['instruction']
            
        # Add session ID if provided
        if self.uri.get_param('session'):
            request_data["params"]["session_id"] = self.uri.get_param('session')
            
        return self._execute_request(request_data)
        
    def _extract(self, data: Any) -> Dict[str, Any]:
        """Extract data from page using LLM"""
        url = self.uri.get_param('url')
        instruction = self.uri.get_param('instruction')
        
        # Get from input data if not in URI
        if isinstance(data, dict):
            url = url or data.get('url')
            instruction = instruction or data.get('instruction')
            
        if not url:
            raise ComponentError("No URL specified for extraction")
        if not instruction:
            raise ComponentError("No extraction instruction provided")
            
        request_data = {
            "url": url,
            "data": instruction,
            "params": {
                "hierarchical_planner": self.uri.get_param('planner', True),
                "visual_mode": self.uri.get_param('visual', False),
                "stealth_mode": self.uri.get_param('stealth', True),
            }
        }
        
        return self._execute_request(request_data)
        
    def _fill_form(self, data: Any) -> Dict[str, Any]:
        """Fill forms on a webpage"""
        url = self.uri.get_param('url')
        form_data = self.uri.get_param('data')
        
        # Get from input data if not in URI
        if isinstance(data, dict):
            url = url or data.get('url')
            form_data = form_data or data.get('form_data', data)
            
        if not url:
            raise ComponentError("No URL specified for form filling")
        if not form_data:
            raise ComponentError("No form data provided")
            
        # Build instruction for form filling
        instruction = self._build_form_instruction(form_data)
        
        request_data = {
            "url": url,
            "data": instruction,
            "params": {
                "hierarchical_planner": True,
                "visual_mode": self.uri.get_param('visual', True),
                "stealth_mode": self.uri.get_param('stealth', True),
                "llm_orchestrator": True,
            }
        }
        
        return self._execute_request(request_data)
        
    def _screenshot(self, data: Any) -> Dict[str, Any]:
        """Take screenshot of webpage"""
        url = self.uri.get_param('url')
        
        if not url and isinstance(data, dict):
            url = data.get('url')
        if not url:
            raise ComponentError("No URL specified for screenshot")
            
        request_data = {
            "url": url,
            "data": "Take a screenshot",
            "params": {
                "visual_mode": True,
            }
        }
        
        return self._execute_request(request_data)
        
    def _execute_bql(self, data: Any) -> Dict[str, Any]:
        """Execute BQL (Browser Query Language) query"""
        query = self.uri.get_param('query')
        
        if not query and isinstance(data, dict):
            query = data.get('query')
        elif not query and isinstance(data, str):
            query = data
            
        if not query:
            raise ComponentError("No BQL query provided")
            
        request_data = {
            "use_bql": True,
            "data": query,
            "params": {}
        }
        
        # Extract URL from BQL query if present (simple parsing)
        url = self._extract_url_from_query(query)
        if url:
            request_data["url"] = url
                
        return self._execute_request(request_data)
        
    def _execute(self, data: Any) -> Dict[str, Any]:
        """Direct executor call"""
        if isinstance(data, dict):
            request_data = data
        else:
            request_data = {"data": data}
            
        # Add URI params to request
        for key, value in self.uri.params.items():
            if key not in request_data:
                request_data[key] = value
                
        return self._execute_request(request_data)
        
    def _execute_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute request using CurllmExecutor"""
        try:
            executor = self._get_executor()
            
            logger.debug(f"CurLLM request: {json.dumps(request_data, indent=2)[:500]}")
            
            # Execute through the executor
            result = executor.execute(request_data)
            
            logger.debug(f"CurLLM response: {json.dumps(result, indent=2)[:500]}")
            
            return result
            
        except Exception as e:
            raise ComponentError(f"CurLLM execution error: {e}") from e
            
    def _build_form_instruction(self, form_data: Dict[str, Any]) -> str:
        """Build form filling instruction from data"""
        parts = ["Fill the form with the following data:"]
        
        for field, value in form_data.items():
            # Convert field names to readable format
            readable_field = field.replace('_', ' ').title()
            parts.append(f"{readable_field}: {value}")
            
        return " ".join(parts)
    
    def _extract_url_from_query(self, query: str) -> Optional[str]:
        """Extract URL from BQL query without regex - simple parsing"""
        url_markers = ['url:', 'URL:', 'Url:']
        for marker in url_markers:
            if marker in query:
                start_idx = query.find(marker) + len(marker)
                rest = query[start_idx:].strip()
                return self._extract_url_value(rest)
        return None

    @staticmethod
    def _extract_url_value(rest: str) -> Optional[str]:
        if rest.startswith('"'):
            end_idx = rest.find('"', 1)
            return rest[1:end_idx] if end_idx > 0 else None
        if rest.startswith("'"):
            end_idx = rest.find("'", 1)
            return rest[1:end_idx] if end_idx > 0 else None
        end_idx = rest.find(' ')
        return rest[:end_idx] if end_idx > 0 else rest
        
    def __del__(self):
        """Cleanup executor on component destruction"""
        if self.executor:
            try:
                self.executor.cleanup()
            except Exception as e:
                logger.debug(f"Executor cleanup failed: {e}")


@register("curllm-stream")
class CurLLMStreamComponent(StreamComponent):
    """
    Streaming version of CurLLM component for processing multiple pages/tasks
    
    URI format:
        curllm-stream://action?param=value
    """
    
    input_mime = MIME_JSON
    output_mime = MIME_JSON
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.base_component = CurLLMComponent(uri)
        
    def stream(self, input_stream: Optional[Iterator]) -> Iterator:
        """Process stream of URLs or tasks"""
        if input_stream:
            for item in input_stream:
                try:
                    result = self.base_component.process(item)
                    yield result
                except Exception as e:
                    logger.error(f"Error processing item in stream: {e}")
                    yield {"error": str(e), "input": item}
                    
    def __del__(self):
        """Cleanup on destruction"""
        if hasattr(self, 'base_component'):
            del self.base_component


# Helper functions for common CurLLM operations

def browse(url: str, instruction: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Browse to URL and optionally interact with page
    
    Args:
        url: URL to browse
        instruction: Optional instruction for interaction
        **kwargs: Additional parameters (visual, stealth, captcha, etc.)
        
    Returns:
        Result from CurLLM
    """
    from ..registry import create_component
    
    uri = f"curllm://browse?url={url}"
    if instruction:
        uri += f"&instruction={instruction}"
    for key, value in kwargs.items():
        uri += f"&{key}={value}"
        
    component = create_component(uri)
    return component.process(None)


def extract_data(url: str, instruction: str, **kwargs) -> Dict[str, Any]:
    """
    Extract data from webpage using LLM
    
    Args:
        url: URL to extract from
        instruction: Extraction instruction
        **kwargs: Additional parameters
        
    Returns:
        Extracted data
    """
    from ..registry import create_component
    
    uri = f"curllm://extract?url={url}&instruction={instruction}"
    for key, value in kwargs.items():
        uri += f"&{key}={value}"
        
    component = create_component(uri)
    return component.process(None)


def fill_form(url: str, form_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """
    Fill form on webpage
    
    Args:
        url: URL with form
        form_data: Data to fill
        **kwargs: Additional parameters
        
    Returns:
        Result of form submission
    """
    from ..registry import create_component
    
    uri = f"curllm://fill_form?url={url}"
    for key, value in kwargs.items():
        uri += f"&{key}={value}"
        
    component = create_component(uri)
    return component.process({"form_data": form_data})


def execute_bql(query: str, **kwargs) -> Dict[str, Any]:
    """
    Execute BQL query
    
    Args:
        query: BQL query string
        **kwargs: Additional parameters
        
    Returns:
        Query results
    """
    from ..registry import create_component
    
    uri = "curllm://bql"
    for key, value in kwargs.items():
        uri += f"&{key}={value}"
        
    component = create_component(uri)
    return component.process({"query": query})
