"""
Data transformation components
"""

import json
import csv
import io
from typing import Any, Dict, List
from ..core import TransformComponent
from ..uri import StreamwareURI
from ..registry import register
from ..exceptions import ComponentError
from ...diagnostics import get_logger

logger = get_logger(__name__)


@register("transform")
class TransformComponent(TransformComponent):
    """
    Generic data transformation component
    
    URI format:
        transform://type?params
        
    Types:
        - json: Parse/serialize JSON
        - jsonpath: Extract using JSONPath
        - csv: Convert to/from CSV
        - template: Apply Jinja2 template
        - normalize: Normalize data structure
        - flatten: Flatten nested structure
    """
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def transform(self, data: Any) -> Any:
        """Transform data based on type"""
        transform_type = self.uri.operation or self.uri.path or "json"
        
        if transform_type == "json":
            return self._transform_json(data)
        elif transform_type == "jsonpath":
            return self._transform_jsonpath(data)
        elif transform_type == "csv":
            return self._transform_csv(data)
        elif transform_type == "normalize":
            return self._normalize(data)
        elif transform_type == "flatten":
            return self._flatten(data)
        else:
            raise ComponentError(f"Unknown transform type: {transform_type}")
            
    def _transform_json(self, data: Any) -> Any:
        """Parse or serialize JSON"""
        if isinstance(data, str):
            try:
                return json.loads(data)
            except json.JSONDecodeError as e:
                raise ComponentError(f"Invalid JSON: {e}") from e
        else:
            return json.dumps(data, indent=2)
            
    def _transform_jsonpath(self, data: Any) -> Any:
        """Extract data using JSONPath (simplified)"""
        query = self.uri.get_param('query', '$')
        
        # Simple JSONPath implementation
        if query == '$':
            return data
        elif query.startswith('$.'):
            path = query[2:].split('.')
            result = data
            
            for key in path:
                if key.endswith('[*]'):
                    # Array access
                    key = key[:-3]
                    if isinstance(result, dict) and key in result:
                        result = result[key]
                    if isinstance(result, list):
                        return result
                elif '[' in key and ']' in key:
                    # Indexed access
                    field, index = key.split('[')
                    index = int(index.rstrip(']'))
                    if isinstance(result, dict) and field in result:
                        result = result[field]
                    if isinstance(result, list) and index < len(result):
                        result = result[index]
                else:
                    # Simple field access
                    if isinstance(result, dict) and key in result:
                        result = result[key]
                    else:
                        return None
                        
            return result
        else:
            return data
            
    def _transform_csv(self, data: Any) -> str:
        """Convert data to CSV format"""
        delimiter = self.uri.get_param('delimiter', ',')
        
        if not isinstance(data, list):
            data = [data]
            
        if not data:
            return ""
            
        output = io.StringIO()
        
        # Get headers from first item
        if isinstance(data[0], dict):
            headers = list(data[0].keys())
            writer = csv.DictWriter(output, fieldnames=headers, delimiter=delimiter)
            writer.writeheader()
            writer.writerows(data)
        else:
            writer = csv.writer(output, delimiter=delimiter)
            for row in data:
                if isinstance(row, (list, tuple)):
                    writer.writerow(row)
                else:
                    writer.writerow([row])
                    
        return output.getvalue()
        
    def _normalize(self, data: Any) -> Dict[str, Any]:
        """Normalize data structure"""
        if isinstance(data, dict):
            # Already normalized
            return data
        elif isinstance(data, list):
            return {"items": data}
        else:
            return {"value": data}
            
    def _flatten(self, data: Any, parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """Flatten nested dictionary"""
        items = []
        
        if isinstance(data, dict):
            for k, v in data.items():
                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                
                if isinstance(v, dict):
                    items.extend(self._flatten(v, new_key, sep=sep).items())
                elif isinstance(v, list):
                    items.append((new_key, v))
                else:
                    items.append((new_key, v))
        else:
            return {parent_key: data}
            
        return dict(items)


@register("jsonpath")
class JSONPathComponent(TransformComponent):
    """
    Dedicated JSONPath component
    
    URI format:
        jsonpath://extract?query=$.items[*].name
    """
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def transform(self, data: Any) -> Any:
        """Extract data using JSONPath"""
        query = self.uri.get_param('query', '$')
        
        # Use transform component's JSONPath implementation
        transform_uri = StreamwareURI(f"transform://jsonpath?query={query}")
        transform_comp = TransformComponent(transform_uri)
        return transform_comp.transform(data)


@register("csv")
class CSVComponent(TransformComponent):
    """
    Dedicated CSV component
    
    URI format:
        csv://convert?delimiter=,
    """
    
    input_mime = "application/json"
    output_mime = "text/csv"
    
    def transform(self, data: Any) -> str:
        """Convert to CSV"""
        delimiter = self.uri.get_param('delimiter', ',')
        
        transform_uri = StreamwareURI(f"transform://csv?delimiter={delimiter}")
        transform_comp = TransformComponent(transform_uri)
        return transform_comp.transform(data)
