# Streamware Component Architecture for CurLLM

Streamware is a modular, component-based architecture for CurLLM inspired by Apache Camel. It provides URI-based routing and composable pipelines for web automation workflows.

## Overview

Streamware enables you to build powerful web automation pipelines using a declarative, composable syntax:

```python
from curllm_core.streamware import flow

# Simple pipeline
result = (
    flow("curllm://browse?url=https://example.com&stealth=true")
    | "curllm://extract?instruction=Get all product prices"
    | "transform://csv"
    | "file://write?path=products.csv"
).run()
```

## Core Concepts

### 1. Components

Components are reusable processing units that handle specific tasks:

- **CurLLM Components**: Web automation with LLM
- **HTTP/Web Components**: Simple HTTP requests
- **File Components**: File I/O operations
- **Transform Components**: Data transformations
- **Pattern Components**: Split, join, multicast, filter, choose

### 2. URI-based Routing

Each component is identified by a URI scheme:

```
curllm://action?param1=value1&param2=value2
http://api.example.com/endpoint?method=post
file://write?path=/tmp/output.json
transform://jsonpath?query=$.items[*]
```

### 3. Flow Builder

Chain components using the pipe operator (`|`):

```python
flow("source") | "transform" | "destination"
```

## Built-in Components

### CurLLM Components

**Scheme**: `curllm://`

Actions:
- `browse`: Navigate and interact with pages
- `extract`: Extract data using LLM
- `fill_form`: Fill web forms
- `screenshot`: Take screenshots
- `bql`: Execute BQL queries
- `execute`: Direct executor call

Examples:

```python
# Browse with stealth mode
flow("curllm://browse?url=https://example.com&stealth=true&visual=false")

# Extract data
flow("curllm://extract?url=https://news.ycombinator.com&instruction=Get top 10 stories")

# Fill form
flow("curllm://fill_form?url=https://example.com/contact")
    .with_data({"name": "John", "email": "john@example.com"})

# BQL query
flow("curllm://bql").with_data({
    "query": 'page(url: "https://example.com") { title, links { text, url } }'
})
```

### HTTP/Web Components

**Scheme**: `http://`, `https://`, `web://`

Methods: GET, POST, PUT, DELETE, PATCH

Examples:

```python
# GET request
flow("http://api.example.com/data")

# POST request
flow("http://api.example.com/users?method=post")
    .with_data({"name": "John", "email": "john@example.com"})

# With headers
flow("http://api.example.com/data?header_Authorization=Bearer token")
```

### File Components

**Scheme**: `file://`

Operations:
- `read`: Read file content
- `write`: Write to file
- `append`: Append to file
- `exists`: Check file existence
- `delete`: Delete file

Examples:

```python
# Read JSON file
flow("file://read?path=/tmp/data.json")

# Write data
flow("file://write?path=/tmp/output.json")
    .with_data({"message": "Hello"})

# Append to log
flow("file://append?path=/tmp/app.log")
    .with_data("Log entry\n")
```

### Transform Components

**Scheme**: `transform://`, `jsonpath://`, `csv://`

Types:
- `json`: Parse/serialize JSON
- `jsonpath`: Extract using JSONPath
- `csv`: Convert to CSV
- `normalize`: Normalize data structure
- `flatten`: Flatten nested objects

Examples:

```python
# Extract with JSONPath
flow("transform://jsonpath?query=$.items[*].name")

# Convert to CSV
flow("transform://csv?delimiter=,")

# Normalize data
flow("transform://normalize")
```

## Advanced Patterns

### Split/Join

Process items individually then collect results:

```python
from curllm_core.streamware import split, join

result = (
    flow("http://api.example.com/items")
    | split("$.items[*]")  # Split array
    | "curllm://extract?instruction=Get details"  # Process each
    | join()  # Collect results
    | "file://write?path=results.json"
).run()
```

### Multicast

Send data to multiple destinations:

```python
from curllm_core.streamware import multicast

flow("curllm://extract?url=https://example.com&instruction=Get data")
    | multicast([
        "file://write?path=/tmp/backup.json",
        "transform://csv",
        "http://api.example.com/webhook?method=post"
    ])
```

### Conditional Routing

Route based on conditions:

```python
from curllm_core.streamware import choose

flow("http://api.example.com/events")
    | choose()
        .when("$.priority == 'high'", "file://write?path=/tmp/high.json")
        .when("$.priority == 'low'", "file://write?path=/tmp/low.json")
        .otherwise("file://write?path=/tmp/default.json")
```

### Filter

Filter data based on conditions:

```python
flow("http://api.example.com/users")
    | "filter://condition?field=age&min=18&max=65"
    | "file://write?path=/tmp/filtered_users.json"
```

## Streaming

Process data in streams for memory efficiency:

```python
# Stream multiple pages
urls = [
    {"url": "https://example1.com"},
    {"url": "https://example2.com"},
    {"url": "https://example3.com"},
]

for result in flow("curllm-stream://browse").stream(iter(urls)):
    print(f"Processed: {result}")
```

## Helper Functions

### Pipeline Builder

```python
from curllm_core.streamware import pipeline

result = pipeline(
    "curllm://browse?url=https://example.com",
    "curllm://extract?instruction=Get data",
    "transform://csv",
    "file://write?path=output.csv"
).run()
```

### Metrics Tracking

```python
from curllm_core.streamware import metrics

with metrics.track("scraping_pipeline"):
    result = flow("curllm://extract?url=...").run()

stats = metrics.get_stats("scraping_pipeline")
print(f"Processed: {stats['processed']}, Errors: {stats['errors']}")
```

### Batch Processing

```python
from curllm_core.streamware import batch_process

urls = ["https://example1.com", "https://example2.com", ...]
results = batch_process(urls, "curllm://browse", batch_size=5)
```

### Diagnostics

```python
from curllm_core.streamware import enable_diagnostics

enable_diagnostics("DEBUG")  # Enable detailed logging

result = (
    flow("curllm://browse?url=...")
    .with_diagnostics(trace=True)  # Per-pipeline diagnostics
    .run()
)
```

## Creating Custom Components

```python
from curllm_core.streamware import Component, register

@register("mycustom")
class MyCustomComponent(Component):
    input_mime = "application/json"
    output_mime = "application/json"
    
    def process(self, data):
        # Process data
        result = transform_data(data)
        return result

# Use it
flow("mycustom://action?param=value")
```

## Real-World Examples

### Web Scraping Pipeline

```python
result = (
    flow("curllm://browse?url=https://news.ycombinator.com&stealth=true")
    | "curllm://extract?instruction=Get all stories with score > 100"
    | "transform://jsonpath?query=$.items[*]"
    | split("$[*]")
    | "curllm://extract?instruction=Get full article content"
    | join()
    | "transform://csv"
    | "file://write?path=/tmp/articles.csv"
).with_diagnostics().run()
```

### Form Automation

```python
form_data = {
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+1234567890",
    "message": "Contact request"
}

result = (
    flow("curllm://fill_form?url=https://example.com/contact&visual=true")
    .with_data(form_data)
    | "file://write?path=/tmp/form_result.json"
).run()
```

### Multi-site Data Collection

```python
sites = [
    "https://site1.com",
    "https://site2.com",
    "https://site3.com"
]

for site in sites:
    with metrics.track(f"scrape_{site}"):
        result = (
            flow(f"curllm://extract?url={site}&instruction=Get product listings")
            | "transform://normalize"
            | f"file://write?path=/tmp/{site.replace('://', '_')}.json"
        ).run()
```

### ETL Pipeline

```python
result = (
    flow("curllm://extract?url=https://data-source.com&instruction=Get data")
    | "transform://normalize"
    | split("$.items[*]")
    | "transform://flatten"
    | join()
    | "transform://csv"
    | "file://write?path=/tmp/etl_output.csv"
    | multicast([
        "file://write?path=/tmp/backup.csv",
        "http://api.example.com/import?method=post"
    ])
).run()
```

## Best Practices

1. **Use stealth mode** for production scraping: `stealth=true`
2. **Enable diagnostics** during development: `enable_diagnostics("DEBUG")`
3. **Track metrics** for monitoring: `metrics.track("pipeline_name")`
4. **Handle errors** with try/except blocks
5. **Use streaming** for large datasets to save memory
6. **Batch processing** for multiple items
7. **Component reuse**: Create custom components for repeated logic

## API Reference

### Core Classes

- `Component`: Base component class
- `StreamComponent`: Base streaming component
- `TransformComponent`: Base transformation component
- `StreamwareURI`: URI parser
- `Flow`: Pipeline builder

### Functions

- `flow(uri)`: Create pipeline
- `pipeline(*steps)`: Create multi-step pipeline
- `split(pattern, type)`: Split data
- `join(type)`: Join split data
- `multicast(destinations)`: Send to multiple destinations
- `choose()`: Conditional routing
- `enable_diagnostics(level)`: Enable logging
- `batch_process(items, pipeline, batch_size)`: Batch processing

### Decorators

- `@register(scheme)`: Register component

## Component Registry

List all available components:

```python
from curllm_core.streamware import list_available_components, describe_component

# List all schemes
schemes = list_available_components()
print(schemes)  # ['curllm', 'http', 'https', 'file', 'transform', ...]

# Get component details
info = describe_component('curllm')
print(info)
```

## Architecture

```
curllm_core/
└── streamware/
    ├── __init__.py          # Main exports
    ├── core.py              # Base component classes
    ├── uri.py               # URI parsing
    ├── exceptions.py        # Custom exceptions
    ├── registry.py          # Component registry
    ├── flow.py              # Flow builder
    ├── patterns.py          # Split, join, multicast, choose
    ├── helpers.py           # Helper utilities
    └── components/          # Built-in components
        ├── __init__.py
        ├── curllm.py        # CurLLM components
        ├── web.py           # HTTP/Web components
        ├── file.py          # File I/O components
        └── transform.py     # Transform components
```

## Testing

```python
# examples/streamware_examples.py contains 15+ examples
python examples/streamware_examples.py
```

## License

Same as CurLLM (Apache 2.0)
