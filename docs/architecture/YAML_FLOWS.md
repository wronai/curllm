# YAML Flow System - CurLLM Streamware

## Overview

The YAML Flow system allows you to define CurLLM automation pipelines in declarative YAML format, making them:
- **Reusable** - Save and share pipeline definitions
- **Configurable** - Use variables for flexibility
- **Versionable** - Track changes in git
- **Readable** - Clear, human-readable syntax

## Quick Start

### 1. Create a YAML Flow

Create `my_flow.yaml`:

```yaml
name: "Extract News Stories"
description: "Extract top stories from Hacker News"

diagnostics: true

input:
  type: "json"
  data:
    url: "https://news.ycombinator.com"
    max_items: 10

steps:
  - component: "curllm://extract"
    params:
      url: "${url}"
      instruction: "Get top ${max_items} story titles"
      stealth: true
      
  - component: "transform://csv"
    params:
      delimiter: ","
      
  - component: "file://write"
    params:
      path: "/tmp/stories.csv"
```

### 2. Run the Flow

```bash
# From command line
curllm-flow run my_flow.yaml

# With custom variables
curllm-flow run my_flow.yaml --var url=https://news.ycombinator.com

# From Python
from curllm_core.streamware import run_yaml_flow

result = run_yaml_flow("my_flow.yaml")
```

## YAML Flow Syntax

### Basic Structure

```yaml
name: "Flow Name"
description: "What this flow does"

# Optional: Enable diagnostics
diagnostics: true
trace: false

# Input data and variables
input:
  type: "json"
  data:
    variable1: "value1"
    variable2: 123

# Pipeline steps
steps:
  - component: "scheme://operation"
    params:
      param1: "value1"
      param2: true
      
  - component: "next://step"
    params:
      param3: "${variable1}"
```

### Variable Substitution

Use `${variable}` to reference input data:

```yaml
input:
  data:
    url: "https://example.com"
    max_results: 20
    
steps:
  - component: "curllm://extract"
    params:
      url: "${url}"
      instruction: "Get ${max_results} items"
```

### Components

Available component schemes:

#### CurLLM Components

```yaml
# Browse webpage
- component: "curllm://browse"
  params:
    url: "https://example.com"
    stealth: true
    visual: false

# Extract data
- component: "curllm://extract"
  params:
    url: "https://example.com"
    instruction: "Get all product prices"
    planner: true

# Fill form
- component: "curllm://fill_form"
  params:
    url: "https://example.com/contact"
    visual: true

# Execute BQL
- component: "curllm://bql"
  params:
    query: "page(url: '...') { title }"

# Screenshot
- component: "curllm://screenshot"
  params:
    url: "https://example.com"
```

#### HTTP/Web Components

```yaml
# HTTP GET
- component: "http://api.example.com/data"
  params:
    method: "get"

# HTTP POST
- component: "http://api.example.com/submit"
  params:
    method: "post"

# Web helper
- component: "web://get"
  params:
    url: "https://api.example.com/data"
```

#### File Components

```yaml
# Read file
- component: "file://read"
  params:
    path: "/tmp/input.json"

# Write file
- component: "file://write"
  params:
    path: "/tmp/output.json"

# Append to file
- component: "file://append"
  params:
    path: "/tmp/log.txt"
```

#### Transform Components

```yaml
# JSONPath extraction
- component: "transform://jsonpath"
  params:
    query: "$.items[*].name"

# CSV conversion
- component: "transform://csv"
  params:
    delimiter: ","

# Normalize data
- component: "transform://normalize"

# Flatten nested objects
- component: "transform://flatten"
```

#### Pattern Components

```yaml
# Split data
- component: "split://"
  params:
    type: "field"
    name: "items"

# Join data
- component: "join://"
  params:
    type: "list"

# Filter data
- component: "filter://condition"
  params:
    field: "price"
    min: 10
    max: 100
```

## Example Flows

### 1. Simple Extraction

```yaml
name: "Simple Extraction"
description: "Extract links from a webpage"

steps:
  - component: "curllm://extract"
    params:
      url: "https://example.com"
      instruction: "Get all links"
      
  - component: "file://write"
    params:
      path: "/tmp/links.json"
```

### 2. Multi-step Pipeline

```yaml
name: "Product Scraping"
description: "Scrape products, transform, and export"

diagnostics: true

input:
  data:
    url: "https://shop.example.com"
    
steps:
  - component: "curllm://browse"
    params:
      url: "${url}"
      stealth: true
      
  - component: "curllm://extract"
    params:
      instruction: "Get all products with name and price"
      
  - component: "transform://jsonpath"
    params:
      query: "$.items[*]"
      
  - component: "transform://csv"
    
  - component: "file://write"
    params:
      path: "/tmp/products.csv"
```

### 3. Batch Processing

```yaml
name: "Multi-Site Scraping"
description: "Process multiple websites"

input:
  data:
    sites:
      - "https://site1.com"
      - "https://site2.com"
      - "https://site3.com"

steps:
  - component: "split://"
    params:
      type: "field"
      name: "sites"
      
  - component: "curllm://browse"
    params:
      stealth: true
      
  - component: "curllm://extract"
    params:
      instruction: "Get main content"
      
  - component: "join://"
    params:
      type: "list"
      
  - component: "file://write"
    params:
      path: "/tmp/multi_site_data.json"
```

### 4. Form Automation

```yaml
name: "Contact Form"
description: "Fill contact forms automatically"

input:
  data:
    url: "https://example.com/contact"
    form_data:
      name: "John Doe"
      email: "john@example.com"
      message: "Test message"

steps:
  - component: "curllm://fill_form"
    params:
      url: "${url}"
      visual: true
      stealth: true
      
  - component: "file://write"
    params:
      path: "/tmp/form_result.json"
```

## CLI Commands

### Run Flow

```bash
# Basic run
curllm-flow run my_flow.yaml

# With variables
curllm-flow run my_flow.yaml --var url=https://example.com --var max=20

# With input data from file
curllm-flow run my_flow.yaml --input-file data.json

# With inline JSON input
curllm-flow run my_flow.yaml --input '{"key":"value"}'

# Save output to file
curllm-flow run my_flow.yaml --output result.json

# Verbose mode
curllm-flow run my_flow.yaml --verbose

# Quiet mode
curllm-flow run my_flow.yaml --quiet
```

### Validate Flow

```bash
# Validate syntax
curllm-flow validate my_flow.yaml

# Verbose validation
curllm-flow validate my_flow.yaml --verbose
```

### List Flows

```bash
# List flows in default directory
curllm-flow list

# List flows in specific directory
curllm-flow list /path/to/flows/

# Lists all .yaml and .yml files
```

### Flow Information

```bash
# Show detailed flow info
curllm-flow info my_flow.yaml

# Shows:
# - Name and description
# - Input requirements
# - Steps and parameters
# - Diagnostics settings
```

## Python API

### Basic Usage

```python
from curllm_core.streamware import run_yaml_flow

# Simple run
result = run_yaml_flow("my_flow.yaml")

# With variables
result = run_yaml_flow(
    "my_flow.yaml",
    variables={"url": "https://example.com"}
)

# With input data
result = run_yaml_flow(
    "my_flow.yaml",
    input_data={"custom": "data"}
)
```

### Advanced Usage

```python
from curllm_core.streamware import YAMLFlowRunner

# Create runner
runner = YAMLFlowRunner()

# Set variables
runner.set_variable("url", "https://example.com")
runner.set_variables({"max": 20, "format": "csv"})

# Load and validate
spec = runner.load_yaml("my_flow.yaml")
is_valid = runner.validate_yaml("my_flow.yaml")

# Build flow
flow = runner.build_flow(spec)

# Run
result = runner.run_yaml("my_flow.yaml")

# Stream mode
for item in runner.run_yaml_stream("my_flow.yaml"):
    process(item)
```

## Best Practices

### 1. Use Descriptive Names

```yaml
name: "E-commerce Product Scraping Pipeline"
description: "Extract product data from multiple categories, transform to CSV, and upload"
```

### 2. Enable Diagnostics During Development

```yaml
diagnostics: true
trace: true  # For detailed debugging
```

### 3. Use Variables for Reusability

```yaml
input:
  data:
    base_url: "https://example.com"
    output_dir: "/tmp/scraping"
    max_items: 50

steps:
  - component: "curllm://extract"
    params:
      url: "${base_url}/products"
      instruction: "Get ${max_items} products"
  - component: "file://write"
    params:
      path: "${output_dir}/products.json"
```

### 4. Save Intermediate Results

```yaml
steps:
  - component: "curllm://extract"
    # ... extraction ...
  - component: "file://write"
    params:
      path: "/tmp/raw_data.json"  # Save raw data
  - component: "transform://csv"
  - component: "file://write"
    params:
      path: "/tmp/final_data.csv"  # Save processed data
```

### 5. Handle Errors Gracefully

```yaml
# Use diagnostics to track issues
diagnostics: true

# Split risky operations
steps:
  - component: "curllm://browse"
    params:
      stealth: true  # Reduce detection
  - component: "file://write"
    params:
      path: "/tmp/checkpoint.json"  # Checkpoint progress
```

## Directory Structure

Recommended organization:

```
project/
├── flows/
│   ├── production/
│   │   ├── daily_scrape.yaml
│   │   └── weekly_report.yaml
│   ├── development/
│   │   ├── test_extraction.yaml
│   │   └── debug_flow.yaml
│   └── templates/
│       ├── scraping_template.yaml
│       └── form_fill_template.yaml
├── data/
│   ├── input/
│   └── output/
└── results/
```

## Troubleshooting

### Flow Validation Errors

```bash
# Check syntax
curllm-flow validate my_flow.yaml --verbose

# Common issues:
# - Missing 'steps' field
# - Invalid component scheme
# - Missing required parameters
```

### Variable Not Replaced

```yaml
# ✗ Wrong - variable not in input.data
steps:
  - component: "curllm://browse"
    params:
      url: "${undefined_var}"  # Error!

# ✓ Correct - define in input
input:
  data:
    my_url: "https://example.com"
steps:
  - component: "curllm://browse"
    params:
      url: "${my_url}"  # Works!
```

### Component Not Found

```bash
# List available components
python -c "from curllm_core.streamware import list_available_components; print(list_available_components())"

# Check component registration
curllm-flow info my_flow.yaml
```

## Migration from Legacy Code

### Before (Legacy)

```python
executor = CurllmExecutor()
result = executor.execute({
    "url": "https://example.com",
    "data": "Get all links",
    "params": {"stealth_mode": True}
})
```

### After (YAML Flow)

```yaml
name: "Link Extraction"
steps:
  - component: "curllm://extract"
    params:
      url: "https://example.com"
      instruction: "Get all links"
      stealth: true
```

### After (Python Streamware)

```python
from curllm_core.streamware import flow

result = flow("curllm://extract?url=https://example.com&instruction=Get all links&stealth=true").run()
```

## Examples Repository

See `flows/` directory for complete examples:

- `example_browse.yaml` - Simple browsing
- `example_extraction.yaml` - Data extraction
- `example_form_fill.yaml` - Form automation
- `example_scraping_pipeline.yaml` - Complete pipeline
- `example_bql.yaml` - BQL queries
- `example_multi_site.yaml` - Multi-site processing
- `example_http_pipeline.yaml` - API integration
- `example_screenshot.yaml` - Screenshots

## Next Steps

1. **Explore examples**: `curllm-flow list flows/`
2. **Run an example**: `curllm-flow run flows/example_browse.yaml`
3. **Create your flow**: Copy and modify an example
4. **Validate**: `curllm-flow validate my_flow.yaml`
5. **Run**: `curllm-flow run my_flow.yaml`

## Support

- **Documentation**: `docs/STREAMWARE.md`
- **Examples**: `examples/streamware_examples.py`
- **API Reference**: `docs/STREAMWARE.md#api-reference`
