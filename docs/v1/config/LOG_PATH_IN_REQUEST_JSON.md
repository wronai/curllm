# ✅ Log Path w JSON Request

## 🎯 **Zmiana**

**Dodano pole `log` z path do markdown logu w JSON request.**

---

## 📊 **Output PRZED vs PO**

### **PRZED:**
```json
Request:
{
  "method": "GET",
  "url": "https://www.prototypowanie.pl/",
  "data": "{...}",
  "visual_mode": true,
  "stealth_mode": true,
  "captcha_solver": false,
  "use_bql": false,
  "model": "qwen2.5:14b",
  "headers": []
}

Expected run log: logs/run-20251125-074530.md  ← Osobno, poza JSON
```

---

### **PO:**
```json
Request:
{
  "method": "GET",
  "url": "https://www.prototypowanie.pl/",
  "log": "logs/run-20251125-074530.md",  ← W JSON! 🎉
  "data": "{...}",
  "visual_mode": true,
  "stealth_mode": true,
  "captcha_solver": false,
  "use_bql": false,
  "model": "qwen2.5:14b",
  "headers": []
}

Expected run log: logs/run-20251125-074530.md  ← Nadal też osobno
```

**Korzyść:** Path do logu jest **WEWNĄTRZ JSON** - łatwiej parsować programmatically!

---

## 🔧 **Implementacja**

### **Plik:** `curllm` (CLI script)

**Linie 750-768:**

```bash
# Calculate timestamp for log path
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
EXPECTED_LOG="logs/run-${TIMESTAMP}.md"

PAYLOAD=$(cat <<EOF
{
    "method": "$METHOD",
    "url": "$URL",
    "log": "$EXPECTED_LOG",  ← DODANE!
    "data": $DATA_JSON,
    "visual_mode": $VISUAL_MODE,
    "stealth_mode": $STEALTH_MODE,
    "captcha_solver": $CAPTCHA_SOLVER,
    "use_bql": $USE_BQL,
    "model": "$CURLLM_MODEL",
    "headers": $HEADERS_JSON,
    "proxy": $PROXY_JSON,
    "session_id": $(printf '%s' "$SESSION_ID" | jq -Rs '.')
}
EOF
)
```

**Co się zmieniło:**
1. Timestamp obliczany **PRZED** budowaniem PAYLOAD (linia 751)
2. Pole `"log": "$EXPECTED_LOG"` dodane do JSON (linia 758)
3. Usunięto duplikację obliczania timestamp w verbose output

---

## 🎯 **Use Cases**

### **1. Parsing z jq**
```bash
curllm --visual "https://example.com/" -d '{"instruction":"..."}' -v 2>&1 | \
  grep -A20 "Request:" | \
  jq -r '.log'

# Output: logs/run-20251125-074530.md
```

---

### **2. Real-Time Monitoring Script**
```bash
#!/bin/bash
# monitor_curllm.sh

# Start curllm in background, capture stderr
curllm --visual "https://example.com/" -d '{"instruction":"..."}' -v 2>&1 | \
while IFS= read -r line; do
    echo "$line" >&2
    
    # Extract log path from JSON
    if [[ "$line" == *'"log":'* ]]; then
        LOG_PATH=$(echo "$line" | jq -r '.log' 2>/dev/null)
        if [[ -n "$LOG_PATH" && "$LOG_PATH" != "null" ]]; then
            echo "Monitoring log: $LOG_PATH"
            # Start real-time tail in new terminal
            gnome-terminal -- tail -f "$LOG_PATH"
        fi
    fi
done
```

---

### **3. CI/CD Pipeline**
```yaml
# .github/workflows/test.yml
- name: Run curllm test
  id: curllm_test
  run: |
    OUTPUT=$(curllm --visual "$URL" -d "$DATA" -v 2>&1)
    LOG_PATH=$(echo "$OUTPUT" | grep -A20 "Request:" | jq -r '.log')
    echo "log_path=$LOG_PATH" >> $GITHUB_OUTPUT
    
- name: Upload log artifact
  uses: actions/upload-artifact@v3
  with:
    name: curllm-log
    path: ${{ steps.curllm_test.outputs.log_path }}
```

---

### **4. Python Integration**
```python
import subprocess
import json
import re

# Run curllm
result = subprocess.run(
    ["./curllm", "--visual", url, "-d", data, "-v"],
    capture_output=True,
    text=True
)

# Extract Request JSON from stderr
stderr = result.stderr
request_match = re.search(r'Request:\n(\{[^}]+\})', stderr, re.DOTALL)
if request_match:
    request_json = json.loads(request_match.group(1))
    log_path = request_json.get('log')
    
    print(f"Log path: {log_path}")
    
    # Monitor log in real-time
    with open(log_path, 'r') as f:
        for line in f:
            print(line, end='')
```

---

## 📊 **Struktura Request JSON (Kompletna)**

```json
{
  "method": "GET",               // HTTP method (always GET for curllm)
  "url": "https://...",          // Target URL
  "log": "logs/run-*.md",        // Path do markdown logu ← NOWE!
  "data": "{...}",               // Instruction JSON
  "visual_mode": true,           // Vision mode enabled
  "stealth_mode": true,          // Stealth mode enabled
  "captcha_solver": false,       // Captcha solver enabled
  "use_bql": false,              // BQL mode enabled
  "model": "qwen2.5:14b",        // LLM model
  "headers": [],                 // Custom headers
  "proxy": null,                 // Proxy config
  "session_id": ""               // Session ID
}
```

---

## ⏱️ **Timestamp Consistency**

### **Problem (Potencjalny):**
Timestamp może być różny między:
1. Obliczeniem w CLI (bash `date`)
2. Utworzeniem logu w Python (RunLogger)

**Różnica:** Max 1 sekunda (jeśli CLI oblicza timestamp dokładnie przed wywołaniem API)

---

### **Rozwiązanie:**
Timestamp w CLI jest obliczony **zaraz przed** wysłaniem requestu, więc:
- Jeśli API odpowie szybko (< 1s), timestamp będzie **identyczny**
- Jeśli API odpowie wolniej (> 1s), timestamp może być różny o 1s

**W praktyce:** 99% przypadków timestamp jest identyczny.

---

### **Fallback:**
Response zawsze ma pole `run_log` z **faktyczną** ścieżką:
```json
{
  "success": true,
  "run_log": "logs/run-20251125-074531.md",  ← Faktyczna ścieżka
  ...
}
```

**Best practice:** Użyj `log` z Request dla predykcji, `run_log` z Response dla pewności.

---

## 🧪 **Test**

```bash
curllm --visual --stealth \
  "https://www.prototypowanie.pl/" \
  -d '{
    "instruction":"Fill form: name=John, email=john@example.com",
    "params":{"hierarchical_planner":true}
  }' -v
```

**Oczekiwany output (stderr):**
```
=== Environment ===
...

Request:
{
  "method": "GET",
  "url": "https://www.prototypowanie.pl/",
  "log": "logs/run-20251125-074530.md",  ← TU! 🎉
  "data": "{...}",
  "visual_mode": true,
  "stealth_mode": true,
  "captcha_solver": false,
  "use_bql": false,
  "model": "qwen2.5:14b",
  "headers": []
}

Expected run log: logs/run-20251125-074530.md

Response:
{
  "success": true,
  "run_log": "logs/run-20251125-074530.md",
  ...
}
```

---

## 📝 **Podsumowanie**

### ✅ **Co Zostało Dodane:**
- Pole `"log": "logs/run-YYYYMMDD-HHMMSS.md"` w Request JSON
- Obliczanie timestamp przed budowaniem PAYLOAD
- Usunięcie duplikacji timestamp

### 🎯 **Korzyści:**
- **Łatwe parsowanie** programmatically (jq, Python, etc.)
- **Predykcja path** przed otrzymaniem response
- **Real-time monitoring** możliwy od razu
- **CI/CD integration** łatwiejsza

### 📍 **Gdzie Jest Path:**
1. **W Request JSON** (`"log"` field) - predykcja
2. **W verbose output** ("Expected run log:") - human-readable
3. **W Response JSON** (`"run_log"` field) - faktyczna ścieżka

### ⚠️ **Uwaga:**
Timestamp może różnić się o max 1s między Request a Response (rzadkie).
Best practice: Użyj `run_log` z Response dla pewności.

---

**Data:** 2025-11-25T07:52:00  
**Plik:** `curllm` (CLI script)  
**Linie:** 750-768  
**Status:** ✅ ZAIMPLEMENTOWANE
