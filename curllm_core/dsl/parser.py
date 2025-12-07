"""
DSL Parser - Parse and Generate Strategies in YAML Format

Strategy files are stored as YAML for:
- Wide IDE/editor support
- Human readability
- Native Python parsing
- Comments support

Example strategy.yaml:
```yaml
url_pattern: "*.ceneo.pl/*"
task: extract_products
algorithm: statistical_containers
selector: div.product-card
fields:
  name: h3.title
  price: span.price
  url: a[href]
filter: "price < 2000"
metadata:
  success_rate: 0.95
  use_count: 42
```
"""

import re
import json
import yaml
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from pathlib import Path


@dataclass
class DSLStrategy:
    """Parsed DSL strategy."""
    
    # Identification
    url_pattern: str = "*"
    task: str = "extract"
    name: str = ""
    
    # Algorithm selection
    algorithm: str = "auto"
    fallback_algorithms: List[str] = field(default_factory=list)
    
    # Extraction config
    selector: str = ""
    fields: Dict[str, str] = field(default_factory=dict)
    filter_expr: str = ""
    
    # Form filling config
    form_selector: str = ""
    form_fields: Dict[str, str] = field(default_factory=dict)
    submit_selector: str = ""
    
    # Validation
    validate_expr: str = ""
    expected_fields: List[str] = field(default_factory=list)
    min_items: int = 1
    
    # Actions
    wait_for: str = ""
    pre_actions: List[str] = field(default_factory=list)
    post_actions: List[str] = field(default_factory=list)
    
    # Metadata
    success_rate: float = 0.0
    last_used: str = ""
    use_count: int = 0
    source_file: str = ""
    
    def to_yaml(self) -> str:
        """Convert strategy to YAML format."""
        data = {
            'url_pattern': self.url_pattern,
            'task': self.task,
        }
        
        if self.name:
            data['name'] = self.name
        
        if self.algorithm and self.algorithm != 'auto':
            data['algorithm'] = self.algorithm
        
        if self.fallback_algorithms:
            data['fallback_algorithms'] = self.fallback_algorithms
        
        if self.selector:
            data['selector'] = self.selector
        
        if self.fields:
            data['fields'] = self.fields
        
        if self.filter_expr:
            data['filter'] = self.filter_expr
        
        if self.form_selector:
            data['form'] = {'selector': self.form_selector}
            if self.form_fields:
                data['form']['fields'] = self.form_fields
            if self.submit_selector:
                data['form']['submit'] = self.submit_selector
        
        if self.validate_expr:
            data['validate'] = self.validate_expr
        
        if self.expected_fields:
            data['expected_fields'] = self.expected_fields
        
        if self.min_items > 1:
            data['min_items'] = self.min_items
        
        if self.wait_for:
            data['wait_for'] = self.wait_for
        
        if self.pre_actions:
            data['pre_actions'] = self.pre_actions
        
        if self.post_actions:
            data['post_actions'] = self.post_actions
        
        # Metadata section
        metadata = {}
        if self.success_rate > 0:
            metadata['success_rate'] = round(self.success_rate, 2)
        if self.use_count > 0:
            metadata['use_count'] = self.use_count
        if self.last_used:
            metadata['last_used'] = self.last_used
        
        if metadata:
            data['metadata'] = metadata
        
        return yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    def to_dsl(self) -> str:
        """Alias for to_yaml() for backward compatibility."""
        return self.to_yaml()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return {
            "url_pattern": self.url_pattern,
            "task": self.task,
            "name": self.name,
            "algorithm": self.algorithm,
            "fallback_algorithms": self.fallback_algorithms,
            "selector": self.selector,
            "fields": self.fields,
            "filter_expr": self.filter_expr,
            "form_selector": self.form_selector,
            "form_fields": self.form_fields,
            "submit_selector": self.submit_selector,
            "validate_expr": self.validate_expr,
            "expected_fields": self.expected_fields,
            "min_items": self.min_items,
            "wait_for": self.wait_for,
            "pre_actions": self.pre_actions,
            "post_actions": self.post_actions,
            "success_rate": self.success_rate,
            "last_used": self.last_used,
            "use_count": self.use_count,
            "source_file": self.source_file,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DSLStrategy":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class DSLParser:
    """Parse YAML strategy files."""
    
    def parse(self, content: str) -> DSLStrategy:
        """Parse DSL content into strategy."""
        strategy = DSLStrategy()
        current_section = None
        
        for line in content.split('\n'):
            line = line.rstrip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Parse comments for metadata
            comment_match = self.COMMENT_PATTERN.match(line)
            if comment_match:
                comment = comment_match.group(1)
                if ':' in comment:
                    key, value = comment.split(':', 1)
                    key = key.strip().lower().replace(' ', '_')
                    value = value.strip()
                    if key == 'success_rate':
                        strategy.success_rate = float(value)
                    elif key == 'use_count':
                        strategy.use_count = int(value)
                    elif key == 'last_used':
                        strategy.last_used = value
                    elif key == 'strategy':
                        strategy.name = value
                continue
            
            # Parse directives
            directive_match = self.DIRECTIVE_PATTERN.match(line)
            if directive_match:
                directive = directive_match.group(1)
                value = directive_match.group(2).strip()
                
                current_section = directive
                self._apply_directive(strategy, directive, value)
                continue
            
            # Parse indented fields (for @fields, @form_fields sections)
            field_match = self.FIELD_PATTERN.match(line)
            if field_match and current_section:
                field_name = field_match.group(2)
                field_value = field_match.group(3)
                
                if current_section == 'fields':
                    strategy.fields[field_name] = field_value
                elif current_section == 'form_fields':
                    strategy.form_fields[field_name] = field_value
                continue
            
            # Parse list items (for @pre_actions, @post_actions)
            list_match = self.LIST_ITEM_PATTERN.match(line)
            if list_match and current_section:
                item = list_match.group(2)
                
                if current_section == 'pre_actions':
                    strategy.pre_actions.append(item)
                elif current_section == 'post_actions':
                    strategy.post_actions.append(item)
                elif current_section == 'fallback':
                    strategy.fallback_algorithms.append(item)
                continue
        
        return strategy
    
    def _apply_directive(self, strategy: DSLStrategy, directive: str, value: str):
        """Apply a directive to the strategy."""
        if directive == 'url_pattern':
            strategy.url_pattern = value
        elif directive == 'task':
            strategy.task = value
        elif directive == 'algorithm':
            strategy.algorithm = value
        elif directive == 'fallback':
            if value:
                strategy.fallback_algorithms = [v.strip() for v in value.split(',')]
        elif directive == 'selector':
            strategy.selector = value
        elif directive == 'filter':
            strategy.filter_expr = value
        elif directive == 'form':
            strategy.form_selector = value
        elif directive == 'submit':
            strategy.submit_selector = value
        elif directive == 'validate':
            strategy.validate_expr = value
        elif directive == 'wait':
            strategy.wait_for = value
        elif directive == 'min_items':
            strategy.min_items = int(value)
        elif directive == 'expected_fields':
            strategy.expected_fields = [f.strip() for f in value.split(',')]
    
    def parse_file(self, filepath: str) -> DSLStrategy:
        """Parse DSL from file."""
        path = Path(filepath)
        content = path.read_text(encoding='utf-8')
        strategy = self.parse(content)
        strategy.source_file = str(path)
        return strategy
    
    def generate_from_result(
        self,
        url: str,
        task: str,
        selector: str,
        fields: Dict[str, str],
        algorithm: str,
        success: bool,
        filter_expr: str = ""
    ) -> DSLStrategy:
        """Generate DSL strategy from successful extraction."""
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        # Create pattern from domain
        url_pattern = f"*{parsed.netloc}/*"
        
        strategy = DSLStrategy(
            url_pattern=url_pattern,
            task=task,
            algorithm=algorithm,
            selector=selector,
            fields=fields,
            filter_expr=filter_expr,
            success_rate=1.0 if success else 0.0,
            use_count=1,
        )
        
        return strategy
    
    def save_strategy(self, strategy: DSLStrategy, directory: str = "dsl") -> str:
        """Save strategy to DSL file."""
        from urllib.parse import urlparse
        import hashlib
        from datetime import datetime
        
        # Create directory if needed
        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)
        
        # Generate filename from URL pattern
        pattern = strategy.url_pattern.replace('*', '').replace('/', '_').strip('_')
        if not pattern:
            pattern = "default"
        
        # Add hash for uniqueness
        content_hash = hashlib.md5(strategy.to_dsl().encode()).hexdigest()[:8]
        filename = f"{pattern}_{strategy.task}_{content_hash}.dsl"
        
        filepath = dir_path / filename
        filepath.write_text(strategy.to_dsl(), encoding='utf-8')
        
        strategy.source_file = str(filepath)
        strategy.last_used = datetime.now().isoformat()
        
        return str(filepath)
