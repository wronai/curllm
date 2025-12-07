"""
DSL - Domain Specific Language for Extraction and Form Filling

Unified DSL for:
1. Extraction strategies (selectors, fields, filters)
2. Form filling recipes (field mappings, submit actions)
3. Algorithm selection (which method works best)
4. Result validation (expected output format)

DSL Format:
```
@url_pattern: *.ceneo.pl/*
@task: extract_products
@algorithm: statistical_containers + llm_validation
@selector: div.product-card
@fields:
  name: h3.product-name
  price: span.price | parse_price(PLN)
  url: a.product-link @href
@filter: price < 2000
@validate: has(name, price) && count >= 5
```

Knowledge Base:
- Tracks algorithm success rates per domain
- Learns optimal strategies from history
- Suggests best approach for new tasks
"""

from .parser import DSLParser, DSLStrategy
from .executor import DSLExecutor
from .knowledge_base import KnowledgeBase, StrategyRecord
from .validator import ResultValidator

__all__ = [
    'DSLParser',
    'DSLStrategy', 
    'DSLExecutor',
    'KnowledgeBase',
    'StrategyRecord',
    'ResultValidator',
]
