# Streamware Examples

Streamware is curllm's component-based architecture for building data pipelines.

## Quick Start

```python
from curllm_core.streamware import Flow, pipeline

# Simple pipeline
flow = Flow() >> "extract://products" >> "transform://filter?price_max=100" >> "file://output.json"
result = await flow.execute(url="https://shop.example.com")
```

## Files

| File | Description |
|------|-------------|
| `streamware_quickstart.py` | Quick start guide |
| `streamware_examples.py` | Comprehensive examples |

## Component Types

| Scheme | Description | Example |
|--------|-------------|---------|
| `extract://` | Data extraction | `extract://products`, `extract://links` |
| `transform://` | Data transformation | `transform://filter`, `transform://map` |
| `file://` | File operations | `file://output.json`, `file://data.csv` |
| `form://` | Form operations | `form://fill`, `form://submit` |

## Pipeline Example

```python
from curllm_core.streamware import Flow

async def product_pipeline():
    flow = (
        Flow()
        >> "extract://products?include_images=true"
        >> "transform://filter?price_max=50"
        >> "transform://sort?by=price"
        >> "file://cheap_products.json"
    )
    
    return await flow.execute(url="https://shop.example.com/products")
```

## Related Documentation

- [Streamware Architecture](../../docs/v2/architecture/STREAMWARE.md)
- [Components Guide](../../docs/v2/architecture/COMPONENTS.md)
- [YAML Flows](../../docs/v2/architecture/YAML_FLOWS.md)
