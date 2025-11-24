# curlx

Proxy helper for curllm. Register, list, and spawn HTTP proxies and expose them to curllm via its proxy registry.

## Install (local dev)

```bash
pip install -e ./curlx_pkg
```

## CLI

```bash
curlx register --host 203.0.113.10 --ports 3128,3129 --server http://localhost:8000
curlx list --server http://localhost:8000
curlx spawn --host ubuntu@203.0.113.10 --ports 3128,3129 --server http://localhost:8000
```

- `register` — dodaje proxy do rejestru curllm (`/api/proxy/register`).
- `list` — pokazuje listę (`/api/proxy/list`).
- `spawn` — na zdalnym hoście przez SSH instaluje `proxy.py` i uruchamia serwery proxy, następnie rejestruje je w curllm.

## Integracja z curllm

W curllm użyj rotacji z rejestru:

```bash
curllm --proxy rotate:registry "https://example.com" -d "extract links"
```

## Zmienne środowiskowe

- `CURLLM_API_HOST` — domyślny host API curllm (np. http://localhost:8000)
- `SSH_BIN` — polecenie SSH (domyślnie: ssh)
- `PY_BIN_REMOTE` — Python na hoście zdalnym (domyślnie: python3)

## Testy

```bash
pytest -q
```

## Licencja

Apache-2.0
