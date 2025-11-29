# API Client Examples

Examples for using curllm REST API from different languages.

## Start the API Server

```bash
# Start curllm server
curllm-web

# Or with Docker
docker-compose up curllm
```

The API runs at `http://localhost:8000` by default.

## Files

| File | Description |
|------|-------------|
| `node_api_example.js` | Node.js client example |
| `php_api_example.php` | PHP client example |

## Node.js Example

```javascript
const response = await fetch('http://localhost:8000/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        instruction: "Extract all links",
        url: "https://example.com"
    })
});

const result = await response.json();
console.log(result);
```

## PHP Example

```php
$response = file_get_contents('http://localhost:8000/run', false, 
    stream_context_create([
        'http' => [
            'method' => 'POST',
            'header' => 'Content-Type: application/json',
            'content' => json_encode([
                'instruction' => 'Extract all links',
                'url' => 'https://example.com'
            ])
        ]
    ])
);

$result = json_decode($response, true);
```

## curl Example

```bash
curl -X POST http://localhost:8000/run \
    -H "Content-Type: application/json" \
    -d '{"instruction": "Extract all links", "url": "https://example.com"}'
```

## Related Documentation

- [API Reference](../../docs/v2/api/API.md)
- [CLI Commands](../../docs/v2/api/CLI_COMMANDS.md)
