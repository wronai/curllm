# Quick Start: LLM Orchestrator

## 🚀 5 Minut do Działania

### 1. Restart Serwera

```bash
make stop && make clean && make start
```

### 2. Włącz LLM Orchestrator

```bash
echo "CURLLM_LLM_ORCHESTRATOR=true" >> .env
```

### 3. Test!

```bash
curllm --visual --stealth \
  "https://softreck.com/contact/" \
  -d '{
    "instruction":"Fill contact form: name=John Doe, email=john@example.com, message=Hello test"
  }' -v
```

### 4. Zobacz Logi

```
🤖 LLM Orchestrator mode enabled
📊 Detected: 5 fields, Form type: WPForms
🧠 Asking LLM for filling plan...
✅ LLM responded
📋 Plan has 5 operations

🤖 Executing plan:
   ▶️  Filling name (first): 'John'
   ▶️  Filling name (last): 'Doe'
   ▶️  Filling email: 'john@example.com'
   ▶️  Filling message: 'Hello test'
   ☑️  Checking checkbox: consent

✅ LLM Orchestrator succeeded
```

---

## ✅ Sprawdź Rezultat

Otwórz screenshot i zweryfikuj:

```bash
ls -lht screenshots/softreck.com/ | head -5
```

Powinno być:
- ✅ Name First: "John"
- ✅ Name Last: "Doe"  
- ✅ Email: "john@example.com"
- ✅ Message: "Hello test"
- ✅ GDPR: CHECKED

---

## 🎛️ Konfiguracja

### Tryb Hybrydowy (Domyślny)

```bash
# LLM orchestrator próbuje pierwszy
# Jeśli zawiedzie → fallback do deterministycznego
CURLLM_LLM_ORCHESTRATOR=true
```

### Tylko Deterministyczny

```bash
# Wyłącz LLM orchestrator
# CURLLM_LLM_ORCHESTRATOR=false
```

### Zaawansowane

```bash
# Użyj GPT-4 (lepszy JSON output)
CURLLM_USE_OPENAI=true
OPENAI_API_KEY=sk-...
CURLLM_OPENAI_MODEL=gpt-4-turbo-preview

# Logowanie decyzji
CURLLM_LOG_LLM_DECISIONS=true
```

---

## 🐛 Troubleshooting

### LLM nie odpowiada?

```bash
# Sprawdź Ollama
curl http://localhost:11434/api/tags

# Lista modeli
ollama list

# Restart Ollama
systemctl restart ollama  # lub docker restart ollama
```

### Pola nadal źle wypełnione?

```bash
# Zobacz detected fields w logu
grep "📊 Detected" logs/run-*.md

# Zobacz LLM plan
grep -A 20 "📋 Plan" logs/run-*.md
```

### Fallback do deterministycznego?

```
⚠️  LLM Orchestrator failed: ..., falling back
🔧 Using deterministic form fill (fallback)
```

**To OK!** System zawsze działa - jeśli LLM zawiedzie, użyje deterministycznego.

---

## 📊 Porównanie

| Tryb | Elastyczność | Szybkość | Koszty |
|------|--------------|----------|--------|
| **LLM Orchestrator** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 💰💰 |
| **Deterministyczny** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 💰 |
| **Hybrydowy** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 💰💰 |

**Rekomendacja: HYBRYDOWY** 🎯

---

## 📚 Więcej Informacji

- **Pełna dokumentacja:** `LLM_FORM_ORCHESTRATOR.md`
- **Przykłady integracji:** `INTEGRATION_EXAMPLE.md`
- **Test case:** `TEST_LLM_ORCHESTRATOR.md`

---

## ✨ Gotowe!

Masz teraz system, który:
- ✅ Automatycznie wykrywa pola formularza
- ✅ LLM decyduje jak je wypełnić
- ✅ Obsługuje split name fields
- ✅ Zawsze działa (fallback)
- ✅ Samodokumentujący się (reasoning)

**Enjoy form automation!** 🎉
