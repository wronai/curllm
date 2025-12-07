"""
Tests for DSL System - Strategy Parsing, Knowledge Base, Validation

Tests:
1. DSL parsing and generation
2. Knowledge base operations
3. Result validation
4. Strategy matching
"""

import pytest
import tempfile
import os
from pathlib import Path


class TestDSLParser:
    """Test DSL parsing and generation."""
    
    def test_parse_yaml_strategy(self):
        """Test parsing YAML format strategy."""
        from curllm_core.dsl import DSLParser, DSLStrategy
        
        yaml_content = """
url_pattern: "*.example.com/*"
task: extract_products
algorithm: statistical_containers
selector: div.product
fields:
  name: h3.title
  price: span.price
filter: "price < 1000"
metadata:
  success_rate: 0.95
  use_count: 10
"""
        
        parser = DSLParser()
        strategy = parser.parse(yaml_content)
        
        assert strategy.url_pattern == "*.example.com/*"
        assert strategy.task == "extract_products"
        assert strategy.algorithm == "statistical_containers"
        assert strategy.selector == "div.product"
        assert strategy.fields == {"name": "h3.title", "price": "span.price"}
        assert strategy.filter_expr == "price < 1000"
        assert strategy.success_rate == 0.95
        assert strategy.use_count == 10
    
    def test_parse_legacy_dsl_strategy(self):
        """Test parsing legacy @directive format for backward compatibility."""
        from curllm_core.dsl import DSLParser, DSLStrategy
        
        dsl_content = """
@url_pattern: *.example.com/*
@task: extract_products
@algorithm: statistical_containers
@selector: div.product
@fields:
  name: h3.title
  price: span.price
@filter: price < 1000
"""
        
        parser = DSLParser()
        strategy = parser.parse(dsl_content)
        
        assert strategy.url_pattern == "*.example.com/*"
        assert strategy.task == "extract_products"
        assert strategy.algorithm == "statistical_containers"
        assert strategy.selector == "div.product"
        assert strategy.fields == {"name": "h3.title", "price": "span.price"}
        assert strategy.filter_expr == "price < 1000"
    
    def test_parse_with_metadata(self):
        from curllm_core.dsl import DSLParser
        
        dsl_content = """
# Strategy: Ceneo Products
@url_pattern: *.ceneo.pl/*
@task: extract_products
# success_rate: 0.85
# use_count: 42
# last_used: 2024-01-15
"""
        
        parser = DSLParser()
        strategy = parser.parse(dsl_content)
        
        assert strategy.name == "Ceneo Products"
        assert strategy.success_rate == 0.85
        assert strategy.use_count == 42
        assert strategy.last_used == "2024-01-15"
    
    def test_to_yaml_roundtrip(self):
        """Test YAML serialization and parsing roundtrip."""
        from curllm_core.dsl import DSLParser, DSLStrategy
        
        original = DSLStrategy(
            url_pattern="*.shop.pl/*",
            task="extract_products",
            algorithm="pattern_detection",
            selector="div.item",
            fields={"name": "h2", "price": ".price"},
            filter_expr="price > 50",
            success_rate=0.9,
            use_count=10
        )
        
        yaml_text = original.to_yaml()
        
        # Verify YAML output contains expected keys
        assert 'url_pattern:' in yaml_text
        assert 'task:' in yaml_text
        assert 'algorithm:' in yaml_text
        assert 'metadata:' in yaml_text
        
        parser = DSLParser()
        parsed = parser.parse(yaml_text)
        
        assert parsed.url_pattern == original.url_pattern
        assert parsed.task == original.task
        assert parsed.algorithm == original.algorithm
        assert parsed.selector == original.selector
        assert parsed.fields == original.fields
        assert parsed.filter_expr == original.filter_expr
    
    def test_generate_from_result(self):
        from curllm_core.dsl import DSLParser
        
        parser = DSLParser()
        strategy = parser.generate_from_result(
            url="https://www.example.com/products",
            task="extract_products",
            selector="div.product-card",
            fields={"name": "h3", "price": ".price"},
            algorithm="statistical_containers",
            success=True
        )
        
        assert "example.com" in strategy.url_pattern
        assert strategy.task == "extract_products"
        assert strategy.selector == "div.product-card"
        assert strategy.success_rate == 1.0
    
    def test_save_and_load_strategy(self):
        from curllm_core.dsl import DSLParser, DSLStrategy
        
        with tempfile.TemporaryDirectory() as tmpdir:
            parser = DSLParser()
            
            strategy = DSLStrategy(
                url_pattern="*.test.com/*",
                task="extract",
                algorithm="test_algo",
                selector=".item"
            )
            
            filepath = parser.save_strategy(strategy, tmpdir)
            assert Path(filepath).exists()
            
            loaded = parser.parse_file(filepath)
            assert loaded.url_pattern == strategy.url_pattern
            assert loaded.task == strategy.task


class TestKnowledgeBase:
    """Test knowledge base operations."""
    
    def test_record_execution(self):
        from curllm_core.dsl import KnowledgeBase, StrategyRecord
        
        with tempfile.TemporaryDirectory() as tmpdir:
            kb = KnowledgeBase(os.path.join(tmpdir, "test.db"))
            
            record = StrategyRecord(
                url="https://example.com/products",
                domain="example.com",
                task="extract_products",
                algorithm="statistical",
                selector=".product",
                fields={"name": "h3"},
                success=True,
                items_extracted=10,
                execution_time_ms=500
            )
            
            exec_id = kb.record_execution(record)
            assert exec_id > 0
    
    def test_get_best_strategy(self):
        from curllm_core.dsl import KnowledgeBase, StrategyRecord
        
        with tempfile.TemporaryDirectory() as tmpdir:
            kb = KnowledgeBase(os.path.join(tmpdir, "test.db"))
            
            # Add successful execution
            record = StrategyRecord(
                url="https://shop.com/products",
                domain="shop.com",
                task="extract_products",
                algorithm="statistical",
                selector=".product",
                fields={"name": "h3", "price": ".price"},
                success=True,
                items_extracted=20,
                execution_time_ms=300
            )
            kb.record_execution(record)
            
            # Get best strategy
            best = kb.get_best_strategy("https://shop.com/other", "extract_products")
            
            assert best is not None
            assert best['algorithm'] == "statistical"
            assert best['selector'] == ".product"
            assert best['success_rate'] == 1.0
    
    def test_algorithm_rankings(self):
        from curllm_core.dsl import KnowledgeBase, StrategyRecord
        
        with tempfile.TemporaryDirectory() as tmpdir:
            kb = KnowledgeBase(os.path.join(tmpdir, "test.db"))
            
            # Add multiple executions
            for i in range(3):
                kb.record_execution(StrategyRecord(
                    url=f"https://site{i}.com/page",
                    domain=f"site{i}.com",
                    task="extract",
                    algorithm="algo_a",
                    selector=".item",
                    fields={},
                    success=True,
                    items_extracted=5,
                    execution_time_ms=100
                ))
            
            kb.record_execution(StrategyRecord(
                url="https://site4.com/page",
                domain="site4.com",
                task="extract",
                algorithm="algo_b",
                selector=".item",
                fields={},
                success=False,
                items_extracted=0,
                execution_time_ms=100
            ))
            
            rankings = kb.get_algorithm_rankings(task="extract")
            
            assert len(rankings) >= 1
            assert rankings[0]['algorithm'] == "algo_a"
            assert rankings[0]['success_rate'] == 1.0
    
    def test_suggest_algorithms(self):
        from curllm_core.dsl import KnowledgeBase
        
        with tempfile.TemporaryDirectory() as tmpdir:
            kb = KnowledgeBase(os.path.join(tmpdir, "test.db"))
            
            suggestions = kb.suggest_algorithms("https://new-site.com", "extract_products")
            
            assert len(suggestions) > 0
            assert "statistical_containers" in suggestions
    
    def test_statistics(self):
        from curllm_core.dsl import KnowledgeBase, StrategyRecord
        
        with tempfile.TemporaryDirectory() as tmpdir:
            kb = KnowledgeBase(os.path.join(tmpdir, "test.db"))
            
            kb.record_execution(StrategyRecord(
                url="https://test.com/page",
                domain="test.com",
                task="extract",
                algorithm="test",
                selector=".item",
                fields={},
                success=True,
                items_extracted=10,
                execution_time_ms=200
            ))
            
            stats = kb.get_statistics()
            
            assert stats['total_strategies'] >= 1
            assert stats['total_executions'] >= 1
            assert stats['unique_domains'] >= 1


class TestResultValidator:
    """Test result validation."""
    
    def test_validate_structure_list(self):
        from curllm_core.dsl import ResultValidator
        
        validator = ResultValidator()
        
        data = [
            {"name": "Product A", "price": 100, "url": "/a"},
            {"name": "Product B", "price": 200, "url": "/b"},
        ]
        
        result = validator.validate_structure(data, ["name", "price", "url"], min_items=2)
        
        assert result.valid
        assert result.score > 0.8
    
    def test_validate_structure_missing_fields(self):
        from curllm_core.dsl import ResultValidator
        
        validator = ResultValidator()
        
        data = [
            {"name": "Product A"},  # missing price, url
        ]
        
        result = validator.validate_structure(data, ["name", "price", "url"], min_items=1)
        
        assert len(result.issues) > 0
        assert result.score < 1.0
    
    def test_validate_prices(self):
        from curllm_core.dsl import ResultValidator
        
        validator = ResultValidator()
        
        data = [
            {"name": "A", "price": 100},
            {"name": "B", "price": 200},
            {"name": "C", "price": 300},
        ]
        
        result = validator.validate_prices(data)
        
        assert result.valid
        assert result.score == 1.0
    
    def test_validate_prices_invalid(self):
        from curllm_core.dsl import ResultValidator
        
        validator = ResultValidator()
        
        data = [
            {"name": "A", "price": -50},  # negative
            {"name": "B", "price": "abc"},  # not numeric
        ]
        
        result = validator.validate_prices(data)
        
        assert len(result.issues) > 0
        assert result.score < 1.0
    
    def test_validate_names(self):
        from curllm_core.dsl import ResultValidator
        
        validator = ResultValidator()
        
        data = [
            {"name": "Valid Product Name"},
            {"name": "Another Product"},
        ]
        
        result = validator.validate_names(data)
        
        assert result.valid
        assert result.score == 1.0
    
    def test_try_fix_json_valid(self):
        from curllm_core.dsl import ResultValidator
        
        validator = ResultValidator()
        
        success, data = validator.try_fix_json('{"name": "test", "price": 100}')
        
        assert success
        assert data == {"name": "test", "price": 100}
    
    def test_try_fix_json_trailing_comma(self):
        from curllm_core.dsl import ResultValidator
        
        validator = ResultValidator()
        
        success, data = validator.try_fix_json('{"name": "test", "price": 100,}')
        
        assert success
        assert data["name"] == "test"
    
    def test_try_fix_json_code_block(self):
        from curllm_core.dsl import ResultValidator
        
        validator = ResultValidator()
        
        text = '''Here is the JSON:
```json
{"name": "test", "price": 100}
```
'''
        
        success, data = validator.try_fix_json(text)
        
        assert success
        assert data["name"] == "test"
    
    def test_try_fix_json_single_quotes(self):
        from curllm_core.dsl import ResultValidator
        
        validator = ResultValidator()
        
        success, data = validator.try_fix_json("{'name': 'test', 'price': 100}")
        
        assert success
        assert data["name"] == "test"


class TestDSLStrategy:
    """Test DSLStrategy dataclass."""
    
    def test_to_dict(self):
        from curllm_core.dsl import DSLStrategy
        
        strategy = DSLStrategy(
            url_pattern="*.example.com/*",
            task="extract",
            algorithm="test",
            selector=".item"
        )
        
        d = strategy.to_dict()
        
        assert d["url_pattern"] == "*.example.com/*"
        assert d["task"] == "extract"
        assert d["algorithm"] == "test"
        assert d["selector"] == ".item"
    
    def test_from_dict(self):
        from curllm_core.dsl import DSLStrategy
        
        data = {
            "url_pattern": "*.shop.pl/*",
            "task": "extract_products",
            "algorithm": "statistical",
            "selector": ".product",
            "fields": {"name": "h3", "price": ".price"},
            "success_rate": 0.95,
            "use_count": 100
        }
        
        strategy = DSLStrategy.from_dict(data)
        
        assert strategy.url_pattern == "*.shop.pl/*"
        assert strategy.task == "extract_products"
        assert strategy.fields == {"name": "h3", "price": ".price"}
        assert strategy.success_rate == 0.95
        assert strategy.use_count == 100
