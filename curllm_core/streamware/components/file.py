"""
File I/O components
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Iterator
from ..core import Component, StreamComponent
from ..uri import StreamwareURI
from ..registry import register
from ..exceptions import ComponentError
from ...diagnostics import get_logger

logger = get_logger(__name__)


@register("file")
class FileComponent(Component):
    """
    File I/O component
    
    URI format:
        file://read?path=/path/to/file.json
        file://write?path=/path/to/output.json&mode=w
        file://append?path=/path/to/log.txt
        
    Operations:
        - read: Read file content
        - write: Write data to file
        - append: Append data to file
        - exists: Check if file exists
        - delete: Delete file
    """
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def process(self, data: Any) -> Any:
        """Process file operation"""
        operation = self.uri.operation or self.uri.path or "read"
        
        if operation == "read":
            return self._read_file(data)
        elif operation == "write":
            return self._write_file(data)
        elif operation == "append":
            return self._append_file(data)
        elif operation == "exists":
            return self._file_exists(data)
        elif operation == "delete":
            return self._delete_file(data)
        else:
            raise ComponentError(f"Unknown file operation: {operation}")
            
    def _read_file(self, data: Any) -> Any:
        """Read file content"""
        path = self._get_path(data)
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Try to parse JSON
            if path.endswith('.json'):
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    pass
                    
            return content
            
        except FileNotFoundError:
            raise ComponentError(f"File not found: {path}")
        except Exception as e:
            raise ComponentError(f"Error reading file {path}: {e}") from e
            
    def _write_file(self, data: Any) -> Dict[str, Any]:
        """Write data to file"""
        path = self._get_path(data)
        mode = self.uri.get_param('mode', 'w')
        
        try:
            # Create parent directories
            os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
            
            with open(path, mode, encoding='utf-8') as f:
                if isinstance(data, (dict, list)):
                    json.dump(data, f, indent=2)
                elif isinstance(data, str):
                    f.write(data)
                else:
                    f.write(str(data))
                    
            return {
                "success": True,
                "path": path,
                "bytes_written": os.path.getsize(path)
            }
            
        except Exception as e:
            raise ComponentError(f"Error writing file {path}: {e}") from e
            
    def _append_file(self, data: Any) -> Dict[str, Any]:
        """Append data to file"""
        self.uri.set_param('mode', 'a')
        return self._write_file(data)
        
    def _file_exists(self, data: Any) -> Dict[str, bool]:
        """Check if file exists"""
        path = self._get_path(data)
        return {
            "path": path,
            "exists": os.path.exists(path)
        }
        
    def _delete_file(self, data: Any) -> Dict[str, Any]:
        """Delete file"""
        path = self._get_path(data)
        
        try:
            if os.path.exists(path):
                os.remove(path)
                return {"success": True, "path": path}
            else:
                return {"success": False, "path": path, "error": "File not found"}
                
        except Exception as e:
            raise ComponentError(f"Error deleting file {path}: {e}") from e
            
    def _get_path(self, data: Any) -> str:
        """Get file path from URI or data"""
        path = self.uri.get_param('path')
        
        if not path and isinstance(data, dict):
            path = data.get('path')
            
        if not path:
            raise ComponentError("No file path specified")
            
        return path


@register("file-stream")
class FileStreamComponent(StreamComponent):
    """
    Streaming file component for reading/writing large files
    
    URI format:
        file-stream://read?path=/path/to/large.jsonl
        file-stream://write?path=/path/to/output.jsonl
    """
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def stream(self, input_stream: Optional[Iterator]) -> Iterator:
        """Stream file operations"""
        operation = self.uri.operation or "read"
        path = self.uri.get_param('path')
        
        if not path:
            raise ComponentError("No file path specified")
            
        if operation == "read":
            yield from self._read_lines(path)
        elif operation == "write":
            yield from self._write_lines(path, input_stream)
        else:
            raise ComponentError(f"Unknown stream operation: {operation}")
            
    def _read_lines(self, path: str) -> Iterator:
        """Read file line by line"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                        
                    # Try to parse JSON
                    if path.endswith('.jsonl') or path.endswith('.ndjson'):
                        try:
                            yield json.loads(line)
                        except json.JSONDecodeError:
                            yield line
                    else:
                        yield line
                        
        except FileNotFoundError:
            raise ComponentError(f"File not found: {path}")
        except Exception as e:
            raise ComponentError(f"Error reading file {path}: {e}") from e
            
    def _write_lines(self, path: str, input_stream: Iterator) -> Iterator:
        """Write stream to file line by line"""
        try:
            # Create parent directories
            os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
            
            mode = self.uri.get_param('mode', 'w')
            
            with open(path, mode, encoding='utf-8') as f:
                for item in input_stream:
                    if isinstance(item, (dict, list)):
                        f.write(json.dumps(item) + '\n')
                    else:
                        f.write(str(item) + '\n')
                    yield item
                    
        except Exception as e:
            raise ComponentError(f"Error writing file {path}: {e}") from e
