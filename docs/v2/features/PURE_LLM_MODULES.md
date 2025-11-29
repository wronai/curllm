# Pure LLM Modules Reference

## Overview

CurLLM uses a **Pure LLM approach** - NO hardcoded regex patterns or CSS selectors.
All decisions are made by the LLM based on actual DOM content.

## Module Status

### ✅ Pure LLM Modules (Recommended)

| Module | Location | Purpose |
|--------|----------|---------|
| `llm_extractor.py` | `extraction/` | Main extraction orchestrator |
| `page_analyzer.py` | `extraction/` | LLM-based page type detection |
| `container_finder.py` | `extraction/` | LLM-based container discovery |
| `field_detector.py` | `extraction/` | LLM-based field identification |
| `llm_patterns.py` | `extraction/` | LLM generates patterns on demand |
| `llm_decision.py` | `components/` | LLM-based decision making |

### ⚠️ Deprecated Modules (Legacy)

| Module | Location | Replacement |
|--------|----------|-------------|
| `extractor.py` | `extraction/` | `llm_extractor.py` |
| `container.py` | `extraction/` | `container_finder.py` |
| `selector.py` | `extraction/` | `llm_patterns.py` |
| `iterative_extractor.py` | `curllm_core/` | `extraction/llm_extractor.py` |

## Key Principle: NO HARDCODED PATTERNS

```python
# ❌ FORBIDDEN - Hardcoded regex
price_match = re.search(r'\d+[,.]?\d*\s*zł', text)

# ❌ FORBIDDEN - Hardcoded selector
container = page.query_selector('.product-item')

# ✅ CORRECT - LLM analyzes DOM
price = await parse_price_with_llm(llm, text)

# ✅ CORRECT - LLM generates selector
selector = await generate_container_selector(page, llm, "products")
```

## Pure LLM Functions

### Page Analysis

```python
from curllm_core.streamware.components.extraction import analyze_page_type

result = await analyze_page_type(page, llm)
# Returns: {"page_type": "product_listing", "confidence": 0.9, ...}
```

### Container Detection

```python
from curllm_core.streamware.components.extraction import find_product_containers

result = await find_product_containers(page, llm, instruction)
# LLM analyzes DOM structure and returns best containers
```

### Field Extraction

```python
from curllm_core.streamware.components.extraction import detect_product_fields

result = await detect_product_fields(page, llm, container_selector)
# LLM identifies name, price, url fields within containers
```

### Pattern Generation (LLM creates patterns)

```python
from curllm_core.streamware.components.extraction import generate_price_pattern

result = await generate_price_pattern(page, llm)
# LLM generates regex pattern based on actual price examples in DOM
# Returns: {"pattern": r"\d+,\d{2}\s*zł", "currency": "PLN", ...}
```

### Price Parsing

```python
# Inside LLMIterativeExtractor
price = await self._parse_price_with_llm("299,99 zł")
# LLM extracts numeric value: 299.99
```

### Decision Making

```python
from curllm_core.streamware.components.llm_decision import (
    extract_fields_from_instruction_llm,
    plan_next_action_llm
)

# LLM parses instruction
fields = await extract_fields_from_instruction_llm(llm, "email=test@example.com")
# Returns: {"email": "test@example.com"}

# LLM plans next action
action = await plan_next_action_llm(llm, instruction, page_context, history)
# Returns: {"type": "fill", "selector": "...", "value": "..."}
```

## Full Extraction Pipeline

```python
from curllm_core.streamware.components.extraction import llm_extract_products

# All steps use LLM - NO REGEX
result = await llm_extract_products(
    page=page,
    llm=llm,
    instruction="Find products under 500zł"
)

# Pipeline:
# 1. analyze_page_type() → LLM determines page type
# 2. find_product_containers() → LLM finds containers  
# 3. detect_product_fields() → LLM identifies fields
# 4. _parse_price_with_llm() → LLM parses prices
# 5. _validate_results() → Verify data makes sense
```

## Migration Guide

### From Old extractor.py

```python
# OLD (deprecated)
from curllm_core.streamware.components.extraction.extractor import extract_products

# NEW (recommended)
from curllm_core.streamware.components.extraction import llm_extract_products
result = await llm_extract_products(page, llm, instruction)
```

### From Old container.py

```python
# OLD (deprecated)
from curllm_core.streamware.components.extraction.container import detect_containers

# NEW (recommended)
from curllm_core.streamware.components.extraction import find_product_containers
result = await find_product_containers(page, llm, instruction)
```

### From Old iterative_extractor.py

```python
# OLD (deprecated)
from curllm_core.iterative_extractor import IterativeExtractor

# NEW (recommended)
from curllm_core.streamware.components.extraction import LLMIterativeExtractor
extractor = LLMIterativeExtractor(page, llm, instruction)
result = await extractor.run()
```

## Why Pure LLM?

1. **Adaptability** - Works with any website structure
2. **No maintenance** - No need to update selectors when sites change
3. **Semantic understanding** - LLM understands context, not just patterns
4. **Fewer bugs** - No regex edge cases to handle
5. **Transparency** - Every decision is logged and explainable
