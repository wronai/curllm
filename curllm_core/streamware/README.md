# Streamware - Component Architecture for CurLLM

Modern Python component framework inspired by Apache Camel for building composable web automation pipelines.

## Quick Start

```python
from curllm_core.streamware import flow

# Simple pipeline
result = (
    flow("curllm://browse?url=https://example.com")
    | "curllm://extract?instruction=Get all links"
    | "transform://csv"
    | "file://write?path=links.csv"
).run()
```

## Features

- **URI-based routing** - Component identification via URI schemes
- **Composable pipelines** - Chain components with pipe operator
- **Built-in components** - CurLLM, HTTP, File, Transform
- **Advanced patterns** - Split/Join, Multicast, Conditional routing
- **Streaming support** - Memory-efficient data processing
- **Metrics & diagnostics** - Built-in monitoring

## Available Components

| Component | Scheme | Purpose |
|-----------|--------|---------|
| CurLLM | `curllm://` | Web automation with LLM |
| HTTP | `http://`, `https://` | HTTP requests |
| Web | `web://` | Web requests helper |
| File | `file://` | File I/O operations |
| Transform | `transform://` | Data transformations |
| Split | `split://` | Split data into items |
| Join | `join://` | Join split data |
| Multicast | `multicast://` | Send to multiple destinations |
| Choose | `choose://` | Conditional routing |
| Filter | `filter://` | Filter data |

## Examples

### Web Scraping

```python
from curllm_core.streamware import flow, split, join

result = (
    flow("curllm://extract?url=https://news.ycombinator.com&instruction=Get top stories")
    | split("$.items[*]")
    | "curllm://extract?instruction=Get article details"
    | join()
    | "file://write?path=stories.json"
).run()
```

### Form Automation

```python
result = (
    flow("curllm://fill_form?url=https://example.com/contact")
    .with_data({"name": "John", "email": "john@example.com"})
    .run()
)
```

### Multi-destination Pipeline

```python
from curllm_core.streamware import multicast

flow("curllm://extract?url=https://example.com&instruction=Get data")
    | multicast([
        "file://write?path=backup.json",
        "transform://csv",
        "http://webhook.example.com?method=post"
    ])
```

## Documentation

See [STREAMWARE.md](../../docs/STREAMWARE.md) for complete documentation.

## Architecture

```
streamware/
├── core.py              # Base component classes
├── uri.py               # URI parsing
├── registry.py          # Component registry
├── flow.py              # Pipeline builder
├── patterns.py          # Advanced patterns
├── helpers.py           # Utilities
└── components/          # Built-in components
    ├── curllm.py
    ├── web.py
    ├── file.py
    └── transform.py
```

## Creating Custom Components

```python
from curllm_core.streamware import Component, register

@register("custom")
class CustomComponent(Component):
    def process(self, data):
        # Your logic here
        return processed_data
```

## License

Apache 2.0 (same as CurLLM)
