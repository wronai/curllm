# ℹ️ Log Path Information w Request Output

## 🎯 **Problem**

**Request output** nie pokazywał ścieżki do pliku logu markdown:

```bash
Request:
{
  "method": "GET",
  "url": "https://www.prototypowanie.pl/",
  "data": "...",
  "visual_mode": true,
  ...
}
```

**Brakowało:**
```
Expected run log: logs/run-20251125-073900.md  ← Gdzie szukać logu!
```

---

## ✅ **Rozwiązanie - Dodano Path do Logu**

### **W `curllm` CLI (linie 769-776):**

**PRZED:**
```bash
if [ "$VERBOSE" = true ]; then
    { print_verbose_env; echo -e "${BLUE}Request:${NC}"; echo "$PAYLOAD" | jq .; } 1>&2
fi
```

**PO:**
```bash
if [ "$VERBOSE" = true ]; then
    TIMESTAMP=$(date +%Y%m%d-%H%M%S)
    EXPECTED_LOG="logs/run-${TIMESTAMP}.md"
    { 
        print_verbose_env
        echo -e "${BLUE}Request:${NC}"
        echo "$PAYLOAD" | jq .
        echo -e "${YELLOW}Expected run log:${NC} ${EXPECTED_LOG}"
    } 1>&2
fi
```

**Dodane:**
- Obliczenie timestampa (ten sam format co w `RunLogger`)
- Obliczenie ścieżki do oczekiwanego logu
- Wyświetlenie w kolorze żółtym (YELLOW)

---

## 📊 **Output Po Zmianie**

```bash
$ curllm --visual --stealth "https://example.com/" \
  -d '{"instruction":"Fill form..."}' -v

=== Environment ===
CURLLM_MODEL: qwen2.5:14b
CURLLM_OLLAMA_HOST: http://localhost:11434
...

Request:
{
  "method": "GET",
  "url": "https://example.com/",
  "data": "{\"instruction\":\"Fill form...\"}",
  "visual_mode": true,
  "stealth_mode": true,
  ...
}

Expected run log: logs/run-20251125-073945.md  ← NOWE! 🎉

Response:
{
  "success": true,
  "data": {...},
  "run_log": "logs/run-20251125-073945.md",  ← Potwierdzenie
  ...
}
```

---

## 🎯 **Korzyści**

### **1. Widoczność od Razu**
- Widzisz gdzie będzie log **PRZED** wykonaniem
- Możesz go otworzyć w edytorze i śledzić na bieżąco
- Nie musisz czekać na response

### **2. Debugging w Real-Time**
```bash
# Terminal 1: Uruchom task
curllm --visual "https://example.com/" -d '{"instruction":"..."}' -v

# Output pokazuje:
# Expected run log: logs/run-20251125-073945.md

# Terminal 2: Śledź log na żywo
tail -f logs/run-20251125-073945.md
```

**Real-time monitoring!** 🚀

---

### **3. Łatwe Porównywanie**
```bash
# Masz problem - widzisz w request:
Expected run log: logs/run-20251125-073945.md

# Możesz od razu otworzyć w edytorze przed zakończeniem taska
code logs/run-20251125-073945.md
```

---

### **4. Timestamp Consistency**
```python
# RunLogger w Python (logger.py linia 9)
ts = datetime.now().strftime('%Y%m%d-%H%M%S')
self.path = self.dir / f'run-{ts}.md'
```

```bash
# CLI w Bash (curllm linia 769)
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
EXPECTED_LOG="logs/run-${TIMESTAMP}.md"
```

**Ten sam format!** Różnica może być max 1 sekunda (jeśli CLI timestamp jest obliczony przed RunLogger).

---

## ⚠️ **Uwaga: API Server Musi Działać**

```bash
# Sprawdź status
$ curllm --status

=== curllm Service Status ===
✓ Ollama is running
✗ curllm API server is not running  ← PROBLEM!
  Run: curllm --start-services
✓ Model qwen2.5:14b is available
```

**Jeśli API nie działa:**
```
Error: Failed to connect to curllm API
```

**Rozwiązanie:**
```bash
curllm --start-services
```

---

## 📁 **Struktura Logów**

```
logs/
├── run-20251125-073324.md  ← Poprzedni run
├── run-20251125-073945.md  ← Obecny run (pokazany w request)
└── run-20251125-074112.md  ← Następny run
```

**Każdy run = osobny plik z timestamp**

---

## 🧪 **Test Po Zmianie**

### **1. Start Services**
```bash
curllm --start-services
```

**Output:**
```
Starting curllm services...
✓ Ollama is running
✓ curllm API is running
✓ Model qwen2.5:14b is available
```

---

### **2. Run z Verbose**
```bash
curllm --visual --stealth \
  "https://www.prototypowanie.pl/kontakt/" \
  -d '{
    "instruction":"Fill form: name=John Doe, email=john@example.com",
    "params":{"hierarchical_planner":true}
  }' -v
```

**Oczekiwany output (stderr):**
```
=== Environment ===
CURLLM_MODEL: qwen2.5:14b
...

Request:
{
  "method": "GET",
  "url": "https://www.prototypowanie.pl/kontakt/",
  "data": "{...}",
  "visual_mode": true,
  ...
}

Expected run log: logs/run-20251125-074530.md  ← TU! 🎉

Response:
{
  "success": true,
  "run_log": "logs/run-20251125-074530.md",  ← Potwierdzenie
  ...
}
```

---

### **3. Real-Time Monitoring**
```bash
# Terminal 1
curllm --visual "https://example.com/" -d '{"instruction":"..."}' -v

# Terminal 2 (skopiuj path z "Expected run log:")
tail -f logs/run-20251125-074530.md
```

**Widzisz log w czasie rzeczywistym!** 🔥

---

## 📝 **Gdzie Jest Path do Logu?**

### **1. W Request Output (verbose mode)**
```
Expected run log: logs/run-20251125-074530.md
```

### **2. W Response**
```json
{
  "run_log": "logs/run-20251125-074530.md",
  ...
}
```

### **3. W Run Log Config Section**
```
Run header (used config):
- CURLLM_MODEL: qwen2.5:14b
- CURLLM_OLLAMA_HOST: http://localhost:11434
...
```

---

## 🎉 **Podsumowanie**

### ✅ **Problem Rozwiązany:**
- **Request output** teraz pokazuje ścieżkę do logu markdown
- Pokazywane **PRZED** wykonaniem (Expected run log)
- Format: `logs/run-YYYYMMDD-HHMMSS.md`

### 📍 **Gdzie Zobaczysz:**
1. **W verbose output** (stderr) - przed requestem
2. **W response** (`run_log` field)
3. **W run log config** (jeśli verbose)

### 🚀 **Korzyści:**
- Real-time monitoring możliwy
- Łatwe debugowanie
- Wiesz gdzie szukać logu od razu

### ⚠️ **Wymaga:**
- API server musi działać (`curllm --start-services`)
- Verbose mode (`-v` flag)

---

**Data:** 2025-11-25T07:45:00  
**Plik:** `curllm` (CLI script)  
**Linie:** 769-776  
**Status:** ✅ ZAIMPLEMENTOWANE
