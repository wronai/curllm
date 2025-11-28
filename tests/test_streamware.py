"""
Unit tests for Streamware component architecture
"""

import pytest
import json
import tempfile
import os
from pathlib import Path

from curllm_core.streamware import (
    flow,
    Flow,
    Component,
    StreamComponent,
    StreamwareURI,
    register,
    create_component,
    list_components,
    ComponentError,
    URIError,
    pipeline,
    split,
    join,
)


class TestStreamwareURI:
    """Test URI parsing"""
    
    def test_basic_uri_parsing(self):
        uri = StreamwareURI("curllm://browse?url=https://example.com")
        assert uri.scheme == "curllm"
        assert uri.operation == "browse"
        assert uri.get_param('url') == "https://example.com"
    
    def test_uri_with_multiple_params(self):
        uri = StreamwareURI("curllm://extract?url=https://example.com&visual=true&stealth=false")
        assert uri.get_param('url') == "https://example.com"
        assert uri.get_param('visual') is True
        assert uri.get_param('stealth') is False
    
    def test_uri_param_types(self):
        uri = StreamwareURI("test://action?count=10&rate=3.14&enabled=true")
        assert uri.get_param('count') == 10
        assert uri.get_param('rate') == 3.14
        assert uri.get_param('enabled') is True
    
    def test_uri_default_values(self):
        uri = StreamwareURI("test://action")
        assert uri.get_param('missing', 'default') == 'default'


class TestComponentRegistry:
    """Test component registration"""
    
    def test_register_component(self):
        @register("test-component")
        class TestComponent(Component):
            def process(self, data):
                return data
        
        component = create_component("test-component://action")
        assert isinstance(component, TestComponent)
    
    def test_list_components(self):
        components = list_components()
        assert isinstance(components, list)
        assert len(components) > 0
        
        # Check for built-in components
        schemes = [c['scheme'] for c in components]
        assert 'curllm' in schemes
        assert 'file' in schemes


class TestFileComponent:
    """Test file I/O operations"""
    
    def test_write_and_read_json(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            # Write
            data = {"message": "test", "count": 42}
            result = (
                flow(f"file://write?path={temp_path}")
                .with_data(data)
                .run()
            )
            assert result['success'] is True
            
            # Read
            read_data = flow(f"file://read?path={temp_path}").run()
            assert read_data == data
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_file_exists(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name
        
        try:
            result = flow(f"file://exists?path={temp_path}").run()
            assert result['exists'] is True
            
            os.unlink(temp_path)
            
            result = flow(f"file://exists?path={temp_path}").run()
            assert result['exists'] is False
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestTransformComponent:
    """Test data transformations"""
    
    def test_jsonpath_extraction(self):
        data = {
            "items": [
                {"name": "item1", "value": 10},
                {"name": "item2", "value": 20},
            ]
        }
        
        result = (
            flow("transform://jsonpath?query=$.items[*]")
            .with_data(data)
            .run()
        )
        
        assert isinstance(result, list)
        assert len(result) == 2
    
    def test_csv_conversion(self):
        data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]
        
        csv_output = (
            flow("transform://csv?delimiter=,")
            .with_data(data)
            .run()
        )
        
        assert isinstance(csv_output, str)
        assert "name,age" in csv_output
        assert "Alice,30" in csv_output
    
    def test_normalize(self):
        data = [1, 2, 3]
        
        result = (
            flow("transform://normalize")
            .with_data(data)
            .run()
        )
        
        assert isinstance(result, dict)
        assert "items" in result
        assert result["items"] == data


class TestFlowBuilder:
    """Test Flow builder and pipeline composition"""
    
    def test_simple_flow(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            data = {"test": "value"}
            
            result = (
                flow(f"file://write?path={temp_path}")
                .with_data(data)
                .run()
            )
            
            assert result['success'] is True
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_pipeline_composition(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            data = {"items": [1, 2, 3, 4, 5]}
            
            result = (
                flow("transform://normalize")
                .with_data(data)
                | "transform://jsonpath?query=$.items"
                | f"file://write?path={temp_path}"
            ).run()
            
            assert result['success'] is True
            
            # Verify file content (jsonpath extracted the items array)
            read_data = flow(f"file://read?path={temp_path}").run()
            assert read_data == [1, 2, 3, 4, 5]
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_pipeline_helper(self):
        data = {"value": 42}
        
        result = pipeline(
            "transform://normalize",
            "transform://jsonpath?query=$.value"
        ).with_data(data).run()
        
        # jsonpath extracts the value field, so result is 42
        assert result == 42


class TestPatterns:
    """Test advanced patterns"""
    
    def test_split_and_join(self):
        data = {"items": [1, 2, 3, 4, 5]}
        
        result = (
            flow("transform://normalize")
            .with_data(data)
            | split("$.items[*]")
            | join()
        ).run()
        
        assert isinstance(result, list)
    
    def test_filter(self):
        data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 17},
            {"name": "Charlie", "age": 25},
        ]
        
        result = (
            flow("filter://condition?field=age&min=18")
            .with_data(data)
            .run()
        )
        
        assert len(result) == 2
        assert all(item['age'] >= 18 for item in result)


class TestCustomComponent:
    """Test custom component creation"""
    
    def test_custom_component_registration(self):
        @register("custom-test")
        class CustomTestComponent(Component):
            input_mime = "application/json"
            output_mime = "application/json"
            
            def process(self, data):
                return {"custom": True, "data": data}
        
        result = (
            flow("custom-test://action")
            .with_data({"test": "value"})
            .run()
        )
        
        assert result['custom'] is True
        assert result['data']['test'] == "value"


class TestErrorHandling:
    """Test error handling"""
    
    def test_invalid_uri(self):
        with pytest.raises(Exception):
            flow("invalid:::uri").run()
    
    def test_missing_file(self):
        with pytest.raises(ComponentError):
            flow("file://read?path=/nonexistent/file.json").run()
    
    def test_unknown_scheme(self):
        with pytest.raises(Exception):
            flow("unknownscheme://action").run()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
