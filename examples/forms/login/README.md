# Login Automation Examples

Automate login forms including WordPress, standard logins, and 2FA.

## Quick Start

```bash
# CLI - WordPress
curllm "https://site.com/wp-admin" \
    -d "Login: username=admin, password=secret"

# CLI - Generic login
curllm "https://app.example.com/login" \
    -d "Login with email=user@example.com, password=mypass"
```

## Files

| File | Description |
|------|-------------|
| `wordpress_login.py` | WordPress login automation |
| `wordpress_login.sh` | WordPress CLI example |
| `generic_login.py` | Generic login form |

## Python Example

```python
from curllm_core import CurllmExecutor

async def wordpress_login():
    executor = CurllmExecutor()
    
    result = await executor.execute_workflow(
        instruction="Login: username=admin, password=secret123",
        url="https://mysite.com/wp-admin",
        stealth_mode=True  # Avoid detection
    )
    
    return result
```

## Features

- **Credential handling** - Secure credential passing
- **2FA support** - Handle two-factor authentication
- **Session persistence** - Keep logged-in state
- **Stealth mode** - Avoid bot detection

## Related

- [Form Filling Guide](../../../docs/v2/features/FORM_FILLING.md)
- [Contact Form Examples](../contact/)
