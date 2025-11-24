# Hierarchical Planner

**[📚 Documentation Index](INDEX.md)** | **[⬅️ Back to Main README](../README.md)**

---

## Overview

The Hierarchical Planner is an intelligent 3-level decision tree that reduces LLM token usage by **~87%** through iterative, context-aware data reduction.

### Problem

Traditional approach sent **53KB+ of DOM data** in a single request:
- 🐌 Slow: 40-60s per LLM request (gemma3:12b)
- 💸 Expensive: ~13,000 tokens per request
- ❌ Overwhelming: LLM struggles with large contexts

### Solution

Break communication into 3 interactive levels:

```
LEVEL 1 (STRATEGIC): ~2KB outline
├─ Question: "What's on the page? What details do you need?"
├─ Data: 2-level outline without field details
└─ LLM decides:
    ├─ decision: "use_form" | "extract_articles" | "complete"
    └─ need_details: ["forms[0].fields"] | null

LEVEL 2 (TACTICAL): ~5KB (only if LLM requested)
├─ Question: "What tool to call?"
├─ Data: EXACTLY what LLM requested in need_details
└─ Decision: tool_name="form.fill", args={...}

LEVEL 3 (EXECUTION): 0 KB (direct)
└─ Execute: form.fill(name="John Doe", email="john@example.com")

FAST PATH: If LLM sets need_details=null in Level 1
└─ Skip Level 2, parse args directly from instruction
```

---

## Configuration

### Environment Variables

```bash
# Enable/disable hierarchical planner (default: true)
CURLLM_HIERARCHICAL_PLANNER=true

# Auto-optimization threshold (default: 25000 chars)
# If page_context > this size, automatically use hierarchical planner
CURLLM_HIERARCHICAL_PLANNER_CHARS=25000

# LLM timeout for each request (default: 300s)
CURLLM_LLM_TIMEOUT=300
```

### Per-Request Override

```bash
# Disable for specific request
curllm -d '{
  "instruction": "Fill form...",
  "params": {
    "hierarchical_planner": false
  }
}'

# Adjust threshold per-request
export CURLLM_HIERARCHICAL_PLANNER_CHARS=30000
```

---

## How It Works

### 1. Automatic Activation

Hierarchical planner activates when:
- **Condition A**: `page_context` size > 25KB (configurable)
- **Condition B**: Instruction contains form keywords AND page has forms
- Keywords: "fill", "form", "submit", "wyślij", "contact"

### 2. Level 1: Strategic Decision

**What LLM receives:**
```json
{
  "title": "Contact • prototypowanie.pl",
  "url": "https://www.prototypowanie.pl/kontakt/",
  "page_type": "form",
  "form_outline": [{
    "id": "forminator-module-5635",
    "field_count": 5,
    "field_types": {"text": 2, "email": 1, "textarea": 1}
  }],
  "headings": ["Contact", "DevOps Engineer"]
}
```

**LLM responds:**
```json
{
  "decision": "use_form",
  "need_details": ["forms[0].fields"],
  "reason": "Need field names to map instruction values"
}
```

**Data reduction:** 51,024 → 2,156 chars (**95.8%** less!)

### 3. Level 2: Tactical Decision

**What LLM receives (only requested details):**
```json
{
  "forms": [{
    "id": "forminator-module-5635",
    "fields": [
      {"name": "name-1", "type": "text", "required": true},
      {"name": "email-1", "type": "email", "required": true},
      {"name": "phone-1", "type": "text"},
      {"name": "textarea-1", "type": "textarea", "required": true}
    ]
  }]
}
```

**LLM responds:**
```json
{
  "tool_name": "form.fill",
  "args": {
    "name": "John Doe",
    "email": "john@example.com",
    "message": "Hello"
  },
  "reason": "Filling contact form with user-provided values"
}
```

### 4. Level 3: Execution

System directly executes `form.fill()` with parsed args. No LLM involved.

---

## Interactive Behavior

### Scenario A: LLM Requests Details

```
📊 Level 1: LLM sees form_outline
   └─ "I need forms[0].fields to proceed"

📋 Level 2: System sends ONLY fields for form[0]
   └─ LLM: "Call form.fill(...)"

✅ Level 3: Execute form.fill
```

### Scenario B: LLM Has Enough Info

```
📊 Level 1: LLM sees form_outline
   └─ "I have enough info, need_details=null"

⚡ SKIP Level 2 entirely!

✅ Level 3: Parse instruction directly → form.fill
```

### Scenario C: Not a Form Task

```
📊 Level 1: LLM sees page summary
   └─ "This is an article list, not a form"

❌ Fallback to standard planner
```

---

## Benefits

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Data per request** | 53KB | 2KB + 5KB | **87% less** |
| **LLM time (qwen2.5:14b)** | 40-60s | 15-20s | **60% faster** |
| **Tokens per request** | ~13,000 | ~2,000 | **85% less** |
| **Cost per request** | $0.013 | $0.002 | **85% cheaper** |

### Additional Benefits

- ✅ **Interactivity**: LLM decides what details it needs
- ✅ **Intelligent skipping**: Level 2 bypassed when possible
- ✅ **Better decisions**: LLM not overwhelmed by data
- ✅ **Automatic fallback**: Seamless switch to standard planner

---

## Example Usage

### Basic Form Filling

```bash
curllm --model qwen2.5:14b \
  "https://example.com/contact" \
  -d '{"instruction":"Fill contact form: name=John Doe, email=john@example.com"}'
```

**Log output:**
```
🎯 Using hierarchical planner (3-level decision tree)
   Original context: 51,024 chars (threshold: 25,000)
📊 Level 1 (Strategic): 1,247 chars prompt, 2,156 chars context (95.8% reduction)
✓ Strategic decision: use_form
   LLM requests details: ["forms[0].fields"]
📋 Level 2 (Tactical): 1,543 chars
✓ Tactical decision: form.fill
✓ Hierarchical planner generated action
```

### With Fast Path

```bash
# LLM skips Level 2 when it has enough info
curllm --model qwen2.5:14b \
  "https://example.com/simple-form" \
  -d '{"instruction":"Fill form: name=John, email=john@example.com"}'
```

**Log output:**
```
🎯 Using hierarchical planner (3-level decision tree)
📊 Level 1 (Strategic): 1,247 chars prompt
✓ Strategic decision: use_form
   LLM has enough info, proceeding without Level 2
⚡ Skipping Level 2 - LLM has sufficient info
```

---

## Implementation Details

### Key Functions

**`should_use_hierarchical_planner(instruction, page_context)`**
- Checks if context size exceeds threshold
- Detects form-related keywords in instruction
- Returns `True` if optimization should be applied

**`extract_strategic_context(page_context)`**
- Creates 2-level JSON outline
- Strips `fields` from forms, replaces with `form_outline`
- Includes field type counts: `{"text": 2, "email": 1}`

**`extract_requested_details(page_context, need_details)`**
- Parses LLM's requested paths: `["forms[0].fields", "interactive"]`
- Returns ONLY the requested subset of data
- Supports: `forms[N].fields`, `interactive`, `headings`

**`hierarchical_plan(instruction, page_context, llm, run_logger)`**
- Orchestrates 3-level flow
- Handles LLM responses with error recovery
- Supports fast path when `need_details=null`

---

## Troubleshooting

### Hierarchical Planner Not Activating

**Check logs for:**
```
🎯 Using hierarchical planner (3-level decision tree)
```

**If missing:**
1. Context too small: `page_context < 25KB`
   - Lower threshold: `export CURLLM_HIERARCHICAL_PLANNER_CHARS=10000`

2. No form keywords in instruction
   - Add: "fill", "form", "submit", "contact"

3. Disabled in config
   - Check: `CURLLM_HIERARCHICAL_PLANNER=true`

### LLM Not Responding with JSON

**Issue:** Strategic/Tactical response not valid JSON

**Solution:**
- Use better model: `qwen2.5:14b` or `llama3.2:latest`
- Increase timeout: `CURLLM_LLM_TIMEOUT=600`
- Check logs for parse errors

### Slow Performance Despite Optimization

**Check:**
1. Model is loaded: `./curllm --status-services`
2. GPU available: Check `GPU Status` output
3. Timeout not too short: `CURLLM_LLM_TIMEOUT >= 300`

---

## Advanced Configuration

### Custom Detail Paths

Extend `extract_requested_details()` to support new paths:

```python
# In hierarchical_planner.py
elif path == "custom_data":
    result["custom_data"] = page_context.get("custom_data", [])
```

### Model-Specific Prompts

Different models may need adjusted prompts. Edit `generate_strategic_prompt()`:

```python
# For smaller models
prompt = f"""Simple question: Is this a form page? Reply: yes/no"""

# For larger models
prompt = f"""Analyze this page and determine..."""
```

---

## Performance Tuning

### Threshold Selection

| Use Case | Recommended Threshold |
|----------|----------------------|
| **Forms only** | 20,000 chars |
| **Mixed content** | 25,000 chars (default) |
| **Always optimize** | 10,000 chars |
| **Disable auto** | 999,999 chars |

### Model Selection

| Model | Best For | Avg Speed |
|-------|----------|-----------|
| `qwen2.5:7b` | Fast, simple forms | 10-15s |
| `qwen2.5:14b` | **Recommended** | 15-20s |
| `llama3.2:11b` | Complex decisions | 20-25s |
| `qwen3:30b` | High accuracy | 30-40s |

---

## Related Documentation

- [Form Filling](FORM_FILLING.md) - How form filling works
- [Environment Configuration](Environment.md) - All environment variables
- [API Reference](API.md) - REST API endpoints
- [Troubleshooting](Troubleshooting.md) - Common issues

---

**[📚 Documentation Index](INDEX.md)** | **[⬆️ Back to Top](#hierarchical-planner)** | **[Main README](../README.md)**
