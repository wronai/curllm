# Dynamic Detection Examples

Advanced examples showing LLM-guided container and pattern detection.

## Contents

| File | Description |
|------|-------------|
| `dynamic_detection_example.py` | Dynamic container detection using statistical + LLM hybrid |
| `atomic_query_example.py` | Atomic DOM queries with iterative extraction |

## Features Demonstrated

- **Statistical Analysis**: Depth analysis, class frequency patterns
- **LLM Validation**: Container validation with confidence scoring
- **CSS/Script Filtering**: Automatic filtering of non-product content
- **Dynamic Heuristics**: LLM-discovered URL patterns

## Usage

```bash
# Run dynamic detection
python dynamic_detection_example.py

# Run atomic query example  
python atomic_query_example.py
```

## Key Concepts

### Dynamic Container Detection
```python
from curllm_core.dynamic_container_detector import DynamicContainerDetector

detector = DynamicContainerDetector(llm, run_logger)
result = await detector.detect_with_llm(page, "Extract products")
# Result: {"selector": ".box-row", "count": 15, "confidence": 0.9}
```

### LLM Heuristics Discovery
```python
from curllm_core.llm_heuristics import LLMHeuristicsDiscovery

discovery = LLMHeuristicsDiscovery(page, llm, logger)
patterns = await discovery.build_dynamic_selectors()
# Result: {"product_link_selector": "a[href*='/p/'], a[href$='.html']"}
```
