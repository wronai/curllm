# CurLLM Development Guidelines

## Core Rules

### 1. NO HARDCODED PATTERNS

```python
# ❌ FORBIDDEN
pattern = r'email[=:]([^,]+)'
match = re.search(pattern, text)

selector = "[name='email']"
selector = ".product-item"
selector = "#submit-button"

# ✅ REQUIRED
fields = await extract_fields_from_instruction_llm(llm, instruction)
selector = await generate_selector_for_field_llm(llm, "email", form_fields)
container = await generate_container_selector(page, llm, "products")
```

### 2. NO REGEX IN APPLICATION CODE

Regex is only allowed in:
- `_parse_json_response()` - to extract JSON from LLM output
- LLM-generated patterns - patterns that LLM creates dynamically

```python
# ❌ FORBIDDEN - Hardcoded regex
price = re.search(r'\d+[,.]?\d*\s*zł', text)

# ✅ ALLOWED - Parsing LLM output
def _parse_json_response(response: str) -> Dict:
    match = re.search(r'\{[^{}]*\}', response)
    return json.loads(match.group()) if match else None

# ✅ ALLOWED - LLM generates the pattern
pattern_info = await generate_price_pattern(page, llm)
# pattern_info["pattern"] contains LLM-generated regex
```

### 3. LLM FOR ALL DECISIONS

Every decision must go through LLM:

| Decision | Function |
|----------|----------|
| Page type | `analyze_page_type()` |
| Container selection | `find_product_containers()` |
| Field mapping | `extract_fields_from_instruction_llm()` |
| Selector generation | `generate_selector_for_field_llm()` |
| Action planning | `plan_next_action_llm()` |
| Validation | `validate_action_llm()` |

### 4. ATOMIC FUNCTIONS

Each function does ONE thing:

```python
# ❌ BAD - Monolithic
async def process_page(page, instruction):
    # 200 lines doing everything...

# ✅ GOOD - Atomic
async def analyze_page(page, llm):
    """Only analyzes page type."""

async def find_containers(page, llm):
    """Only finds containers."""

async def detect_fields(page, llm, container):
    """Only detects fields."""

async def extract_data(page, container, fields):
    """Only extracts data."""
```

### 5. FULL LOGGING

Every operation must be logged:

```python
async def my_function(page, llm, run_logger=None):
    if run_logger:
        run_logger.log_text("🔍 Starting operation...")
    
    result = await do_something()
    
    if run_logger:
        run_logger.log_text(f"✅ Completed: {result.get('status')}")
        run_logger.log_code("json", json.dumps(result, indent=2))
    
    return result
```

### 6. TYPE HINTS

All functions must have type hints:

```python
# ❌ BAD
async def extract(page, llm, instruction):
    pass

# ✅ GOOD
async def extract(
    page: Page,
    llm: Any,
    instruction: str,
    run_logger: Optional[RunLogger] = None
) -> Dict[str, Any]:
    pass
```

### 7. DOCSTRINGS

All public functions need docstrings:

```python
async def analyze_page_type(
    page,
    llm,
    run_logger=None
) -> Dict[str, Any]:
    """
    Analyze page type using LLM.
    
    Args:
        page: Playwright page object
        llm: LLM client instance
        run_logger: Optional logger for transparency
        
    Returns:
        {
            "page_type": str,
            "has_products": bool,
            "confidence": float,
            "reasoning": str
        }
    """
```

---

## Code Organization

### File Structure

```
component/
├── __init__.py          # Exports all public functions
├── module1.py           # Atomic functions for feature 1
├── module2.py           # Atomic functions for feature 2
└── llm_module.py        # LLM-based alternatives
```

### Import Order

```python
# 1. Standard library
import json
import asyncio
from typing import Dict, Any, List, Optional

# 2. Third-party
from playwright.async_api import Page

# 3. Local imports
from .llm_patterns import generate_price_pattern
from ..llm import SimpleOllama
```

### Export Pattern

```python
# __init__.py
from .page_analyzer import analyze_page_type, detect_price_format
from .container_finder import find_product_containers
from .llm_extractor import LLMIterativeExtractor, llm_extract_products

__all__ = [
    'analyze_page_type',
    'detect_price_format',
    'find_product_containers',
    'LLMIterativeExtractor',
    'llm_extract_products',
]
```

---

## LLM Prompt Guidelines

### Structure

```python
prompt = f"""[TASK DESCRIPTION]

[CONTEXT]
{formatted_context}

[SPECIFIC INSTRUCTIONS]
- Rule 1
- Rule 2
- Rule 3

[OUTPUT FORMAT]
Output JSON:
{{"key": "value", ...}}

JSON:"""
```

### Best Practices

1. **Be specific** - Tell LLM exactly what you want
2. **Provide context** - Give relevant page/DOM information
3. **Define output format** - Always specify JSON structure
4. **End with trigger** - End prompt with "JSON:" to trigger JSON output

### Example

```python
prompt = f"""Find the CSS selector for the email field.

Form fields available:
{fields_text}

Rules:
- Match by name, id, or type attribute
- Prefer specific selectors over generic ones
- Return null if not found

Output JSON:
{{"selector": "CSS selector or null", "confidence": 0.0-1.0}}

JSON:"""
```

---

## Error Handling

### Always Handle LLM Failures

```python
async def my_llm_function(llm, data):
    try:
        response = await llm.ainvoke(prompt)
        result = _parse_json_response(response)
        
        if result:
            return result
    except Exception as e:
        if run_logger:
            run_logger.log_text(f"⚠️ LLM failed: {e}")
    
    # Always return a valid fallback
    return {"found": False, "error": "LLM failed"}
```

### Graceful Degradation

```python
# Try LLM first, fall back to simple logic
async def extract_fields(instruction):
    try:
        return await extract_fields_from_instruction_llm(llm, instruction)
    except Exception:
        # Simple fallback without regex
        return _simple_key_value_parse(instruction)
```

---

## Testing

### Unit Test Structure

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_analyze_page_type():
    # Mock LLM
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = '{"page_type": "product_listing", "confidence": 0.9}'
    
    # Mock page
    mock_page = MagicMock()
    mock_page.evaluate = AsyncMock(return_value={"title": "Products"})
    
    # Test
    result = await analyze_page_type(mock_page, mock_llm)
    
    assert result["page_type"] == "product_listing"
    assert result["confidence"] >= 0.8
```

### Integration Test

```python
@pytest.mark.asyncio
async def test_full_extraction():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("https://test-shop.example.com")
        
        result = await llm_extract_products(page, llm, "Find all products")
        
        assert result["count"] > 0
        assert all("name" in p for p in result["products"])
        
        await browser.close()
```

---

## Naming Conventions

### Functions

```python
# Async functions - descriptive verb
async def analyze_page_type()
async def find_product_containers()
async def extract_field_value()

# LLM functions - suffix with _llm
async def extract_fields_from_instruction_llm()
async def generate_selector_for_field_llm()

# Private helpers - prefix with _
def _parse_json_response()
def _format_context()
```

### Variables

```python
# Clear, descriptive names
page_context = {}
container_selector = ".product"
field_mapping = []

# Avoid abbreviations
# ❌ pg, ctx, sel, fld
# ✅ page, context, selector, field
```

### Constants

```python
# UPPER_SNAKE_CASE
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30000
LLM_MODEL = "qwen2.5:7b"
```

---

## Performance Guidelines

### Batch LLM Calls

```python
# ❌ BAD - One call per item
for product in products:
    price = await parse_price_llm(llm, product["price_text"])

# ✅ GOOD - Batch when possible
prices = await parse_prices_batch_llm(llm, [p["price_text"] for p in products])
```

### Cache Results

```python
# Cache page analysis
if not self.state.get("page_analysis"):
    self.state["page_analysis"] = await analyze_page_type(page, llm)

# Reuse cached result
page_type = self.state["page_analysis"]["page_type"]
```

### Limit Context Size

```python
# ❌ BAD - Send entire DOM
context = page.content()  # Could be 100KB+

# ✅ GOOD - Send relevant subset
context = await page.evaluate("""
    () => ({
        title: document.title,
        forms: document.querySelectorAll('form').length,
        text: document.body.innerText.substring(0, 500)
    })
""")
```

---

## Deprecation Process

### Mark as Deprecated

```python
"""
Module description.

DEPRECATED: Use streamware.components.extraction.LLMIterativeExtractor instead.
"""

import warnings

def old_function():
    """DEPRECATED: Use new_function() instead."""
    warnings.warn(
        "old_function is deprecated, use new_function instead",
        DeprecationWarning,
        stacklevel=2
    )
    return new_function()
```

### Provide Migration Path

```python
# In __init__.py - export both old and new
from .old_module import OldClass  # Deprecated
from .new_module import NewClass  # Recommended

# In documentation
"""
Migration:
    # OLD
    from module import OldClass
    obj = OldClass()
    
    # NEW  
    from module import NewClass
    obj = NewClass()
"""
```

---

## Git Workflow

### Commit Messages

```
feat(extraction): Add LLM-based container detection
fix(form): Handle CAPTCHA detection failure
refactor(decision): Replace regex with LLM parsing
docs: Add component reference documentation
test: Add integration tests for extraction
```

### Branch Naming

```
feature/llm-extraction
fix/captcha-handling
refactor/remove-hardcoded-selectors
docs/architecture-update
```
