# Product Extraction Examples

Extract product data from e-commerce websites.

## Quick Start

```bash
# Extract all products
curllm "https://shop.example.com/products" -d "Extract all products with prices"

# Filter by price
curllm "https://shop.example.com/products" -d "Extract products under $100"
```

## Files

| File | Description |
|------|-------------|
| `extract_products.py` | Python extraction example |
| `extract_products.sh` | Bash CLI example |
| `curl_api.sh` | REST API example |

## Python Example

```python
from curllm_core import CurllmExecutor, LLMConfig

async def extract_products():
    executor = CurllmExecutor(LLMConfig(provider="openai/gpt-4o-mini"))
    
    result = await executor.execute_workflow(
        instruction="Extract all products with name, price, and image URL",
        url="https://shop.example.com/products"
    )
    
    return result.get("result", {}).get("products", [])
```

## Output Format

```json
{
  "products": [
    {"name": "Product 1", "price": 29.99, "image": "https://..."},
    {"name": "Product 2", "price": 49.99, "image": "https://..."}
  ]
}
```

## Related

- [Extraction Guide](../../../docs/v2/guides/EXAMPLES.md)
- [BQL Examples](../../bql/)
