# CurLLM Components Reference

## Table of Contents

1. [Extraction Components](#extraction-components)
2. [Form Components](#form-components)
3. [Decision Components](#decision-components)
4. [BQL Components](#bql-components)
5. [Vision Components](#vision-components)
6. [Browser Components](#browser-components)
7. [LLM Components](#llm-components)

---

## Extraction Components

Location: `curllm_core/streamware/components/extraction/`

### Overview

Pure LLM-based product extraction system. **NO HARDCODED REGEX OR SELECTORS.**

### page_analyzer.py

Analyzes page type using LLM.

```python
async def analyze_page_type(
    page,           # Playwright page
    llm,            # LLM client
    run_logger=None # Optional logger
) -> Dict[str, Any]:
    """
    Returns:
        {
            "page_type": "product_listing" | "single_product" | "category" | "homepage" | "other",
            "has_products": bool,
            "confidence": float,  # 0.0 - 1.0
            "reasoning": str
        }
    """
```

```python
async def detect_price_format(
    page,
    llm,
    run_logger=None
) -> Dict[str, Any]:
    """
    Returns:
        {
            "format": "text" | "image" | "mixed",
            "currency": "PLN" | "EUR" | "USD" | "other",
            "sample": str  # Example price
        }
    """
```

### container_finder.py

Finds product containers using LLM.

```python
async def find_product_containers(
    page,
    llm,
    instruction: str = "",
    run_logger=None
) -> Dict[str, Any]:
    """
    Returns:
        {
            "found": bool,
            "containers": [
                {"selector": str, "count": int, "confidence": float}
            ],
            "best": {"selector": str, "reasoning": str}
        }
    """
```

```python
async def analyze_container_content(
    page,
    llm,
    container_selector: str,
    run_logger=None
) -> Dict[str, Any]:
    """
    Returns:
        {
            "is_product_container": bool,
            "content_type": "products" | "navigation" | "articles" | "other",
            "has_prices": bool,
            "has_names": bool,
            "reasoning": str
        }
    """
```

### field_detector.py

Detects product fields using LLM.

```python
async def detect_product_fields(
    page,
    llm,
    container_selector: str,
    run_logger=None
) -> Dict[str, Any]:
    """
    Returns:
        {
            "found": bool,
            "fields": {
                "name": {"selector": str, "sample": str},
                "price": {"selector": str, "sample": str},
                "url": {"selector": str, "sample": str},
                "image": {"selector": str, "sample": str}
            },
            "completeness": float  # 0.0 - 1.0
        }
    """
```

```python
async def extract_field_value(
    page,
    llm,
    container_element,
    field_name: str,
    run_logger=None
) -> Optional[str]:
    """
    Extract single field value using LLM when selector fails.
    """
```

### llm_patterns.py

LLM generates patterns/selectors dynamically.

```python
async def generate_price_pattern(page, llm, run_logger=None) -> Dict[str, Any]:
    """
    LLM generates regex pattern for prices based on actual page content.
    
    Returns:
        {
            "pattern": str,      # Regex pattern
            "currency": str,
            "format": str,
            "examples": [str]
        }
    """
```

```python
async def generate_product_link_pattern(page, llm, run_logger=None) -> Dict[str, Any]:
    """
    LLM generates regex pattern for product links.
    
    Returns:
        {
            "pattern": str,      # Regex for URLs
            "selector": str,     # CSS selector
            "examples": [str]
        }
    """
```

```python
async def generate_container_selector(
    page,
    llm,
    content_type: str = "products",
    run_logger=None
) -> Dict[str, Any]:
    """
    Returns:
        {
            "selector": str,
            "count": int,
            "confidence": float,
            "alternatives": [str]
        }
    """
```

```python
async def generate_extraction_strategy(
    page,
    llm,
    instruction: str,
    run_logger=None
) -> Dict[str, Any]:
    """
    Complete extraction strategy from LLM.
    
    Returns:
        {
            "container_selector": str,
            "fields": {
                "name": {"selector": str, "type": "text"},
                "price": {"selector": str, "type": "text|image"},
                "url": {"selector": str, "type": "attribute:href"}
            },
            "filters": {
                "price_max": float | None,
                "price_min": float | None
            },
            "confidence": float
        }
    """
```

### llm_extractor.py

Main extraction orchestrator.

```python
class LLMIterativeExtractor:
    """
    Pipeline:
    1. analyze_page_type() - Determine page type
    2. find_product_containers() - Find containers
    3. detect_product_fields() - Identify fields
    4. extract_products() - Extract each product
    5. filter_products() - Apply filters
    """
    
    async def run(self, max_items: int = 50) -> Dict[str, Any]:
        """
        Returns:
            {
                "products": [{name, price, url, image}, ...],
                "count": int,
                "reason": str,
                "metadata": {...}
            }
        """
```

```python
async def llm_extract_products(
    page,
    llm,
    instruction: str,
    max_items: int = 50,
    run_logger=None
) -> Dict[str, Any]:
    """Convenience function for extraction."""
```

---

## Form Components

Location: `curllm_core/streamware/components/form/`

### smart_orchestrator.py

Intelligent form filling with LLM verification.

```python
class SmartFormOrchestrator:
    """
    Features:
    - Field type validation
    - Per-field verification
    - Post-submit evaluation
    - Retry mechanisms
    - CAPTCHA handling
    """
    
    async def orchestrate(
        self,
        user_data: Dict[str, str],
        instruction: str = ""
    ) -> Dict[str, Any]:
        """
        Returns:
            {
                "success": bool,
                "fields_filled": int,
                "submission_result": {...},
                "captcha_handled": bool,
                "retries": int
            }
        """
```

### Key Methods

```python
async def _detect_fields(page) -> List[Dict]:
    """Detect all form fields on page."""

async def _smart_map_fields(fields, data, instruction) -> List[Dict]:
    """LLM-based field mapping."""

async def _fill_with_verification(mapping) -> Dict:
    """Fill fields and verify each one."""

async def _detect_captcha(page) -> bool:
    """Detect CAPTCHA presence."""

async def _handle_captcha(page) -> bool:
    """Solve CAPTCHA using Vision LLM."""

async def _submit_with_evaluation(page) -> Dict:
    """Submit and evaluate success with LLM."""
```

---

## Decision Components

Location: `curllm_core/streamware/components/llm_decision.py`

### Functions

```python
async def extract_fields_from_instruction_llm(
    llm,
    instruction: str,
    available_fields: List[str] = None,
    run_logger=None
) -> Dict[str, str]:
    """
    Extract field=value pairs from instruction.
    
    Example:
        Input: "fill form with email=test@example.com, name=John"
        Output: {"email": "test@example.com", "name": "John"}
    """
```

```python
async def parse_selector_name_llm(
    llm,
    selector: str,
    run_logger=None
) -> Optional[str]:
    """
    Extract field name from CSS selector.
    
    Example:
        Input: "[name='email-input']"
        Output: "email-input"
    """
```

```python
async def plan_next_action_llm(
    llm,
    instruction: str,
    page_context: Dict[str, Any],
    history: List[Dict] = None,
    run_logger=None
) -> Dict[str, Any]:
    """
    Returns:
        {
            "type": "fill" | "click" | "wait" | "complete",
            "selector": str,
            "value": str,
            "reason": str
        }
    """
```

```python
async def validate_action_llm(
    llm,
    action: Dict[str, Any],
    before_state: Dict[str, Any],
    after_state: Dict[str, Any],
    run_logger=None
) -> Dict[str, Any]:
    """
    Returns:
        {
            "success": bool,
            "reason": str,
            "confidence": float
        }
    """
```

```python
async def interpret_instruction_llm(
    llm,
    instruction: str,
    run_logger=None
) -> Dict[str, Any]:
    """
    Returns:
        {
            "intent": "fill_form" | "navigate" | "extract_data" | "click" | "search",
            "url": str | None,
            "form_data": Dict[str, str],
            "expected_outcome": str,
            "steps": [str]
        }
    """
```

```python
async def generate_selector_for_field_llm(
    llm,
    field_name: str,
    form_fields: List[Dict],
    run_logger=None
) -> Optional[str]:
    """Generate CSS selector for a semantic field name."""
```

---

## BQL Components

Location: `curllm_core/streamware/components/bql/`

### parser.py

```python
class BQLParser:
    """Parse BQL queries into executable AST."""
    
    def parse(self, query: str) -> BQLNode:
        """Parse BQL string into node tree."""
```

### executor.py

```python
class BQLExecutor:
    """Execute parsed BQL queries."""
    
    async def execute(self, node: BQLNode, page) -> Any:
        """Execute BQL node on page."""
```

### Example BQL

```bql
QUERY products FROM "https://shop.example.com/category" {
    name: .product-name
    price: .price-value
    url: a.product-link@href
    image: img.product-image@src
}
WHERE price < 500
ORDER BY price ASC
LIMIT 20
```

---

## Vision Components

Location: `curllm_core/streamware/components/vision/`

### analyzer.py

```python
class VisionAnalyzer:
    """OpenCV-based visual analysis."""
    
    def detect_captcha_patterns(self, image_path: str) -> Dict:
        """Detect CAPTCHA patterns in image."""
    
    def detect_distorted_text(self, image_path: str) -> bool:
        """Detect distorted/warped text using FFT."""
```

### form_analysis.py

```python
async def analyze_form_fields_vision(
    llm,
    screenshot_path: str,
    run_logger=None
) -> Dict[str, Any]:
    """
    Analyze form using Vision LLM.
    
    Returns:
        {
            "visible_fields": [...],
            "honeypots": [...],
            "recommended_fill_order": [...],
            "captcha_detected": bool
        }
    """
```

### captcha/vision_solve.py

```python
async def solve_captcha_with_vision(
    page,
    llm,
    screenshot_path: str
) -> Dict[str, Any]:
    """
    Solve CAPTCHA using Vision LLM.
    
    Returns:
        {
            "solved": bool,
            "answer": str,
            "confidence": float
        }
    """
```

---

## Browser Components

Location: `curllm_core/streamware/components/browser/`

### stealth.py

```python
async def apply_stealth_mode(page) -> None:
    """Apply anti-detection measures."""

async def randomize_viewport(page) -> None:
    """Randomize viewport size."""

async def inject_stealth_scripts(page) -> None:
    """Inject scripts to evade bot detection."""
```

### navigation.py

```python
async def navigate_with_retry(
    page,
    url: str,
    max_retries: int = 3
) -> bool:
    """Navigate with automatic retry on failure."""

async def wait_for_load(page, timeout: int = 30000) -> bool:
    """Wait for page to fully load."""
```

---

## LLM Components

Location: `curllm_core/streamware/components/llm/`

### client.py

```python
class SimpleOllama:
    """Minimal Ollama client for LLM calls."""
    
    async def ainvoke(self, prompt: str) -> str:
        """Generate text response."""
    
    async def ainvoke_with_image(
        self,
        prompt: str,
        image_path: str
    ) -> str:
        """Generate response with image (Vision LLM)."""
```

### factory.py

```python
def setup_llm() -> Any:
    """Initialize LLM client based on configuration."""

def get_llm() -> Any:
    """Get or create global LLM instance."""
```

---

## Usage Examples

### Complete Extraction Example

```python
import asyncio
from playwright.async_api import async_playwright
from curllm_core.streamware.components.extraction import llm_extract_products
from curllm_core.llm import SimpleOllama

async def extract_products():
    llm = SimpleOllama()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("https://example-shop.com/products")
        
        result = await llm_extract_products(
            page=page,
            llm=llm,
            instruction="Find all electronics under $500"
        )
        
        for product in result["products"]:
            print(f"{product['name']}: ${product['price']}")
        
        await browser.close()

asyncio.run(extract_products())
```

### Complete Form Filling Example

```python
import asyncio
from playwright.async_api import async_playwright
from curllm_core.streamware.components.form import SmartFormOrchestrator
from curllm_core.llm import SimpleOllama

async def fill_contact_form():
    llm = SimpleOllama()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto("https://example.com/contact")
        
        orchestrator = SmartFormOrchestrator(page, llm)
        result = await orchestrator.orchestrate(
            user_data={
                "name": "John Doe",
                "email": "john@example.com",
                "message": "Hello, this is a test message."
            },
            instruction="Fill and submit the contact form"
        )
        
        print(f"Success: {result['success']}")
        await browser.close()

asyncio.run(fill_contact_form())
```

---

## Component Registration

Components are registered using decorators:

```python
from curllm_core.streamware.registry import register

@register("my-component")
class MyComponent(Component):
    """Custom component."""
    
    def process(self, data: Any) -> Dict[str, Any]:
        # Implementation
        pass
```

Usage:

```python
from curllm_core.streamware.registry import create_component

component = create_component("my-component://action?param=value")
result = component.process(input_data)
```
