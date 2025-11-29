# Form Automation Examples

Examples for filling and submitting web forms.

## Projects

### [contact/](contact/) - Contact Form Filling
Fill contact forms with name, email, message.

```bash
# CLI
curllm "https://example.com/contact" -d "Fill form: name=John, email=john@example.com"

# Python
python examples/forms/contact/fill_form.py
```

### [login/](login/) - Login Automation
Automate login forms including WordPress.

```bash
# CLI
curllm "https://wordpress.site/wp-admin" -d "Login: user=admin, pass=secret"

# Python
python examples/forms/login/wordpress_login.py
```

## Features Demonstrated

- **Automatic field detection** - LLM finds form fields
- **Smart mapping** - Maps user data to correct fields
- **Validation handling** - Detects and handles errors
- **CAPTCHA support** - Optional CAPTCHA solving

## Related Documentation

- [Form Filling Guide](../../docs/v2/features/FORM_FILLING.md)
- [LLM-Guided Form Filling](../../docs/v2/features/LLM_GUIDED_FORM_FILLING.md)
- [Vision Form Analysis](../../docs/v2/features/VISION_FORM_ANALYSIS.md)
