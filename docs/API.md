# API

Docs: [Home](../README.md) | [Installation](Installation.md) | [Environment](Environment.md) | [API](API.md) | [Playwright+BQL](Playwright_BQL.md) | [Examples](EXAMPLES.md) | [Docker](Docker.md) | [Devbox](Devbox.md) | [Troubleshooting](Troubleshooting.md) | [Instrukcja](../INSTRUKCJA.md)

## REST Endpoints

- GET `/health`
  - Returns server status and model info.

- POST `/api/execute`
  - Content-Type: application/json
  - Payload:
    ```json
    {
      "url": "https://example.com",
      "data": "instruction or query",
      "visual_mode": false,
      "stealth_mode": false,
      "captcha_solver": false,
      "use_bql": false,
      "headers": {"Accept-Language": "pl-PL,pl;q=0.9"}
    }
    ```
  - Response shape:
    ```json
    {
      "success": true,
      "result": {"...": "..."},
      "screenshots": ["screenshots/domain/step_0_xxx.png"],
      "steps_taken": 3,
      "run_log": "logs/run-YYYYMMDD-HHMMSS.md",
      "timestamp": "2025-11-24T08:27:36.528Z"
    }
    ```

- GET `/api/models`
  - Lists available Ollama models.

- GET `/api/screenshot/<filename>`
  - Serves saved screenshots.

## Headers

- Set `Accept-Language` to influence content language (examples send this automatically if `ACCEPT_LANGUAGE` is defined).

## Example requests

- curl (raw):
  ```bash
  curl -sS -X POST "$CURLLM_API_HOST/api/execute" \
    -H 'Content-Type: application/json' \
    -d '{"url":"https://example.com","data":"extract all links"}' | jq .
  ```

- Node.js: see `examples/node_api_example.js`
- PHP: see `examples/php_api_example.php`
