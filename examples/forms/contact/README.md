# Contact Form Examples

Fill contact forms automatically.

## Quick Start

```bash
# CLI
curllm "https://example.com/contact" \
    -d "Fill form: name=John Doe, email=john@example.com, message=Hello"
```

## Files

| File | Description |
|------|-------------|
| `fill_form.py` | Python form filling example |
| `fill_form.sh` | Bash CLI example |
| `curl_api.sh` | REST API example |

## Python Example

```python
from curllm_core import CurllmExecutor

async def fill_contact_form():
    executor = CurllmExecutor()
    
    result = await executor.execute_workflow(
        instruction="Fill form: name=John Doe, email=john@example.com, message=Test",
        url="https://example.com/contact",
        visual_mode=True  # Enable for complex forms
    )
    
    return result
```

## Related

- [Form Filling Guide](../../../docs/v2/features/FORM_FILLING.md)
- [Login Examples](../login/)
