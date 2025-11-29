# Orchestration Examples

Advanced extraction orchestration with multiple strategies.

## Contents

| File | Description |
|------|-------------|
| `orchestrator_example.py` | Multi-strategy extraction orchestrator |
| `semantic_query_example.py` | Semantic queries with LLM understanding |

## Orchestration Pipeline

```
1. Quick Page Check
   ↓ (price_count, product_links, page_type)
2. LLM-Guided Extraction
   ↓ (container selector, field detection)
3. Dynamic Detection (fallback)
   ↓ (statistical + LLM hybrid)
4. Iterative Extractor (fallback)
   ↓ (atomic DOM queries)
5. Multi-Criteria Filtering
   ↓ (price filters, keyword matching)
6. Result Validation
```

## Usage

```bash
python orchestrator_example.py
python semantic_query_example.py
```

## Example: Custom Orchestration

```python
from curllm_core.extraction_orchestrator import ExtractionOrchestrator

async def extract_products(page, llm, instruction):
    orchestrator = ExtractionOrchestrator(page, llm, instruction, logger)
    
    # Try multiple strategies in order
    result = await orchestrator.extract()
    
    return result['products']
```
