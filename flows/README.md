# YAML Flow Examples

This directory contains example YAML flow definitions for Streamware pipelines.

## Available Flows

### Basic Flows

1. **example_browse.yaml** - Simple web browsing
   - Browse a webpage
   - Save result to file

2. **example_extraction.yaml** - Data extraction
   - Extract data using LLM
   - Transform to CSV
   - Save output

3. **example_form_fill.yaml** - Form automation
   - Fill web forms automatically
   - Handle contact forms

4. **example_screenshot.yaml** - Screenshot capture
   - Capture webpage screenshots

### Advanced Flows

5. **example_scraping_pipeline.yaml** - Complete scraping pipeline
   - Stealth browsing
   - Data extraction
   - Multiple output formats (JSON, CSV)

6. **example_bql.yaml** - BQL query execution
   - Execute Browser Query Language
   - Extract structured data

7. **example_multi_site.yaml** - Multi-site scraping
   - Process multiple websites
   - Split/Join pattern
   - Aggregate results

8. **example_http_pipeline.yaml** - API to scraping
   - Get data from HTTP API
   - Scrape resulting URLs
   - Combine results

## YAML Flow Format

```yaml
name: "Flow Name"
description: "Flow description"

# Optional: Enable diagnostics
diagnostics: true
trace: false

# Input data
input:
  type: "json"
  data:
    key: "value"

# Pipeline steps
steps:
  - component: "scheme://operation"
    params:
      param1: "value1"
      param2: true
      
  - component: "next://step"
    params:
      param3: "value3"
```

## Variable Substitution

Use `${variable}` syntax for variable substitution:

```yaml
input:
  data:
    url: "https://example.com"
    
steps:
  - component: "curllm://browse"
    params:
      url: "${url}"  # Will be replaced with https://example.com
```

## Running YAML Flows

### From Python

```python
from curllm_core.streamware.yaml_runner import run_yaml_flow

# Run flow
result = run_yaml_flow("flows/example_browse.yaml")

# With variables
result = run_yaml_flow(
    "flows/example_extraction.yaml",
    variables={"url": "https://custom-url.com"}
)

# With input data
result = run_yaml_flow(
    "flows/example_browse.yaml",
    input_data={"url": "https://example.com"}
)
```

### From CLI

```bash
# Run a flow
curllm flow run flows/example_browse.yaml

# With variables
curllm flow run flows/example_extraction.yaml --var url=https://example.com

# Validate flow
curllm flow validate flows/example_browse.yaml

# List available flows
curllm flow list flows/
```

## Component Reference

### CurLLM Components

- `curllm://browse` - Browse webpage
- `curllm://extract` - Extract data with LLM
- `curllm://fill_form` - Fill web forms
- `curllm://screenshot` - Take screenshot
- `curllm://bql` - Execute BQL query

### HTTP Components

- `http://` or `https://` - HTTP requests
- `web://` - Web request helper

### File Components

- `file://read` - Read file
- `file://write` - Write file
- `file://append` - Append to file

### Transform Components

- `transform://json` - JSON operations
- `transform://jsonpath` - JSONPath extraction
- `transform://csv` - CSV conversion
- `transform://normalize` - Normalize data

### Pattern Components

- `split://` - Split data
- `join://` - Join data
- `multicast://` - Multiple destinations
- `choose://` - Conditional routing
- `filter://` - Filter data

## Common Parameters

### CurLLM Parameters

- `url` - Target URL
- `instruction` - LLM instruction
- `stealth` - Enable stealth mode (bool)
- `visual` - Enable visual mode (bool)
- `captcha` - Enable captcha solving (bool)
- `planner` - Enable hierarchical planner (bool)

### File Parameters

- `path` - File path
- `mode` - Write mode (w, a)

### Transform Parameters

- `query` - JSONPath query
- `delimiter` - CSV delimiter

## Best Practices

1. **Use variables** for reusable flows
2. **Enable diagnostics** during development
3. **Validate flows** before running in production
4. **Add descriptions** for clarity
5. **Use meaningful names** for flows
6. **Split complex flows** into smaller reusable flows
7. **Save intermediate results** for debugging

## Examples

### Simple Extraction

```yaml
name: "Quick Extraction"
steps:
  - component: "curllm://extract"
    params:
      url: "https://example.com"
      instruction: "Get all links"
  - component: "file://write"
    params:
      path: "/tmp/links.json"
```

### Multi-step Pipeline

```yaml
name: "Complex Pipeline"
diagnostics: true
steps:
  - component: "curllm://browse"
    params:
      url: "https://example.com"
      stealth: true
  - component: "curllm://extract"
    params:
      instruction: "Get product data"
  - component: "transform://jsonpath"
    params:
      query: "$.items[*]"
  - component: "transform://csv"
  - component: "file://write"
    params:
      path: "/tmp/products.csv"
```

## Troubleshooting

### Flow Not Running

1. Check YAML syntax: `curllm flow validate flow.yaml`
2. Verify component names are correct
3. Check required parameters are provided
4. Enable diagnostics for detailed logs

### Variable Not Replaced

- Ensure variable is defined in `input.data`
- Use correct syntax: `${variable}`
- Variables are case-sensitive

### Component Errors

- Check component documentation
- Verify parameter types (bool, string, int)
- Enable trace mode for detailed error info

## Creating Custom Flows

1. Copy an example flow
2. Modify steps and parameters
3. Validate: `curllm flow validate your_flow.yaml`
4. Test: `curllm flow run your_flow.yaml`
5. Iterate and refine

## Contributing

Add new example flows to this directory with:
- Descriptive name
- Clear documentation
- Realistic use case
- Working example
