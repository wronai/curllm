# Functions - Atomic Reusable Operations

This folder contains small, atomic, reusable functions for extraction and form filling.

## Structure

```
functions/
├── README.md           # This file
├── __init__.py         # Python function loader
├── registry.py         # Function registry and discovery
├── extractors/         # Data extraction functions
│   ├── prices.py       # Price extraction
│   ├── names.py        # Product name extraction
│   └── specs.py        # Specification extraction
├── validators/         # Data validation functions
│   ├── price.py        # Price validation
│   └── url.py          # URL validation
├── transformers/       # Data transformation functions
│   ├── normalize.py    # Data normalization
│   └── clean.py        # Data cleaning
└── js/                 # JavaScript functions for browser
    ├── extractors.js   # DOM extraction
    ├── selectors.js    # Selector generation
    └── validators.js   # Client-side validation
```

## Usage

### Python Functions

```python
from functions import get_function, list_functions

# Get a specific function
extract_price = get_function("extractors.prices.extract_polish_price")
price = extract_price("1 234,56 zł")  # Returns: 1234.56

# List available functions
for func in list_functions("extractors"):
    print(func.name, func.description)
```

### JavaScript Functions

```javascript
// In browser context
const { extractPrice, cleanText } = await loadFunctions(['extractors', 'transformers']);

const price = extractPrice(element.textContent);
```

## Creating New Functions

### Python Function Template

```python
# functions/extractors/my_extractor.py

from functions.registry import register_function

@register_function(
    name="extract_something",
    category="extractors",
    description="Extracts something from text",
    examples=[
        {"input": "example input", "output": "expected output"}
    ]
)
def extract_something(text: str) -> str:
    """
    Extract something from text.
    
    Args:
        text: Input text
        
    Returns:
        Extracted value
    """
    # Implementation
    return result
```

### JavaScript Function Template

```javascript
// functions/js/my_function.js

/**
 * Extract something from element
 * @param {Element} element - DOM element
 * @returns {string} Extracted value
 */
function extractSomething(element) {
    // Implementation
    return result;
}

// Register for use
registerFunction('extractSomething', extractSomething, {
    category: 'extractors',
    description: 'Extracts something from DOM element'
});
```

## LLM-Generated Functions

The system can generate new atomic functions based on patterns and user feedback:

```python
from functions.generator import generate_function

# Generate from pattern
func = await generate_function(
    name="extract_allegro_price",
    pattern="Extract price from Allegro product card",
    examples=[
        {"input": "99,99 zł", "output": 99.99},
        {"input": "1 234 zł", "output": 1234.0}
    ]
)

# Function is saved to functions/extractors/generated/allegro_price.py
```

## Best Practices

1. **Keep functions atomic** - One function = one task
2. **Include examples** - Help with testing and LLM understanding
3. **Handle edge cases** - Return None or raise specific exceptions
4. **Type hints** - Always use type annotations
5. **Docstrings** - Document parameters and return values
