# Remote Proxy Tutorial (PL/EN)

This guide shows how to run HTTP proxy servers on an external host and use them locally in curllm.

---

## PL: Zewnętrzny host proxy + lokalne użycie w curllm

### Wymagania na hoście zdalnym
- Linux z Python 3.11+
- Dostęp SSH (np. `user@host`)
- Otwarty firewall na porty proxy (np. 3128, 3129)
  - Przykład (UFW):
    ```bash
    sudo ufw allow 3128/tcp
    sudo ufw allow 3129/tcp
    sudo ufw reload
    ```

### Opcja A: Automatycznie przez curlx (spawn)
Na maszynie lokalnej (z uruchomionym API curllm):
```bash
# Instalacja curlx (dev)
pip install -e ./curlx_pkg

# Uruchom proxy.py na zdalnym hoście i zarejestruj w API curllm
curlx spawn --host user@203.0.113.10 --ports 3128,3129 --server http://localhost:8000
```
- curlx:
  - instaluje `proxy.py` na hoście zdalnym (przez SSH),
  - startuje serwery proxy na wskazanych portach,
  - rejestruje je w `/api/proxy/register`.
- Logi/PID na hoście zdalnym:
  - logi: `/tmp/proxy_<port>.log`
  - PID: `/tmp/proxy_<port>.pid`

Stop (zdalnie):
```bash
ssh user@203.0.113.10 "pkill -f 'python.*-m proxy' || true"
```

### Opcja B: Ręcznie (SSH)
Na hoście zdalnym:
```bash
python3 -m pip install --user -q proxy.py
nohup python3 -m proxy --hostname 0.0.0.0 --port 3128 >/tmp/proxy_3128.log 2>&1 & echo $! > /tmp/proxy_3128.pid
nohup python3 -m proxy --hostname 0.0.0.0 --port 3129 >/tmp/proxy_3129.log 2>&1 & echo $! > /tmp/proxy_3129.pid
```
Na maszynie lokalnej: rejestracja proxy w curllm:
```bash
curl -s -X POST "http://localhost:8000/api/proxy/register" \
  -H 'Content-Type: application/json' \
  -d '{"proxies":["http://203.0.113.10:3128","http://203.0.113.10:3129"]}'
# lub
curlx register --host 203.0.113.10 --ports 3128,3129 --server http://localhost:8000
```

### Walidacja i użycie
- Health-check (opcjonalny prune):
  ```bash
  curl -s -X POST "http://localhost:8000/api/proxy/health" -H 'Content-Type: application/json' \
    -d '{"url":"http://example.com","timeout":4,"limit":10,"prune":false}' | jq .

  curl -s -X POST "http://localhost:8000/api/proxy/health" -H 'Content-Type: application/json' \
    -d '{"url":"http://example.com","timeout":4,"prune":true}' | jq .
  ```
- Użycie z curllm (rotacja rejestru):
  ```bash
  curllm --proxy rotate:registry "https://example.com" -d "extract links"
  ```
- Użycie z curllm (rotacja publiczna — wymagana lista lub fallback):
  ```bash
  # Zalecane: własna lista (file/URL/CSV)
  export CURLLM_PUBLIC_PROXY_LIST="file:///abs/path/proxies.txt"
  curllm --proxy rotate:public "https://example.com" -d "extract links"
  ```

### Walidacja przez Docker
- Jednokontenerowe E2E:
  ```bash
  make test-curlx-e2e
  ```
  Co robi:
  - buduje obraz testowy,
  - uruchamia API curllm,
  - startuje 2 serwery proxy (`proxy.py`) w kontenerze,
  - rejestruje proxy przez `curlx`,
  - sprawdza `/api/proxy/list`,
  - uruchamia `curllm --proxy rotate:registry` i `--proxy rotate:public` (fallback do registry).

- docker-compose (API + zdalny proxy service):
  ```bash
  make test-curlx-compose
  ```
  Co robi:
  - uruchamia `api` i `remote-proxy` w jednej sieci Dockera,
  - rejestruje `remote-proxy:3128,3129`,
  - waliduje `/api/proxy/health`,
  - uruchamia curllm z rotacją registry/public.

### Rozwiązywanie problemów
- Brak połączenia: sprawdź firewall/ufw, routing i NAT (otwarte porty TCP na hoście zdalnym).
- Timeout na health-check: zwiększ `timeout`, sprawdź, czy `proxy.py` działa i czy porty nasłuchują (`ss -ltn`).
- `rotate:public` bywa niestabilne na globalnej liście — preferuj własną listę proxy lub rejestr + prune.

---

## EN: External proxy host + local usage in curllm

### Requirements on remote host
- Linux with Python 3.11+
- SSH access (e.g., `user@host`)
- Open firewall for proxy ports (e.g., 3128, 3129)

### Option A: curlx (spawn)
Local machine (with curllm API running):
```bash
pip install -e ./curlx_pkg
curlx spawn --host user@203.0.113.10 --ports 3128,3129 --server http://localhost:8000
```
- Installs `proxy.py` remotely, starts proxies, registers them in curllm.

### Option B: Manual (SSH)
Remote host:
```bash
python3 -m pip install --user -q proxy.py
nohup python3 -m proxy --hostname 0.0.0.0 --port 3128 >/tmp/proxy_3128.log 2>&1 & echo $! > /tmp/proxy_3128.pid
nohup python3 -m proxy --hostname 0.0.0.0 --port 3129 >/tmp/proxy_3129.log 2>&1 & echo $! > /tmp/proxy_3129.pid
```
Local registration:
```bash
curl -s -X POST "http://localhost:8000/api/proxy/register" \
  -H 'Content-Type: application/json' \
  -d '{"proxies":["http://203.0.113.10:3128","http://203.0.113.10:3129"]}'
```

### Validation and usage
- Health-check / prune, then:
  ```bash
  curllm --proxy rotate:registry "https://example.com" -d "extract links"
  ```
- Public rotation (provide list or rely on fallback sources):
  ```bash
  export CURLLM_PUBLIC_PROXY_LIST="file:///abs/path/proxies.txt"
  curllm --proxy rotate:public "https://example.com" -d "extract links"
  ```

### Docker validation
- Single-container:
  ```bash
  make test-curlx-e2e
  ```
- docker-compose:
  ```bash
  make test-curlx-compose
  ```

### Troubleshooting
- Ensure remote ports are reachable, firewall open, and `proxy.py` keeps running.
- Prefer registry + pruning or your curated public list for stability.
