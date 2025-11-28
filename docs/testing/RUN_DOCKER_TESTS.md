# Running Docker Tests - Quick Guide

## 🚀 Quick Start

### Option 1: Run All Tests (Recommended)

```bash
make test-docker
```

This will:
1. Build Docker images
2. Start test web server with 10 test pages
3. Start mock Ollama server
4. Run all integration tests
5. Generate HTML test report

### Option 2: Step by Step

```bash
# 1. Build test environment
make test-docker-build

# 2. Run tests
make test-docker-run

# 3. View results
open test_results/report.html
```

### Option 3: Manual Docker Compose

```bash
# Start all services
docker-compose -f docker-compose.test.yml up

# Run tests only
docker-compose -f docker-compose.test.yml run curllm-test

# Stop all services
docker-compose -f docker-compose.test.yml down
```

---

## 📄 Test Pages

### View Test Pages Locally

```bash
make test-pages
```

Then visit: `http://localhost:8080/01_simple_form.html`

### Available Test Pages (10)

1. **01_simple_form.html** - Basic contact form
2. **02_product_list.html** - Product catalog
3. **03_login_form.html** - Login page
4. **04_registration.html** - Multi-field registration
5. **05_search_results.html** - Search results page
6. **06_data_table.html** - Data table extraction
7. **07_newsletter.html** - Newsletter subscription
8. **08_multi_step_form.html** - Multi-step form wizard
9. **09_ecommerce_cart.html** - Shopping cart
10. **10_feedback_form.html** - Feedback form with rating

---

## 🧪 Integration Tests (10)

### Test Suite

All tests use **LLM-DSL Bridge** to communicate with Streamware components via JSON/YAML:

1. **test_01_simple_form.py** - Form filling via LLM-DSL
2. **test_02_product_extraction.py** - Data extraction
3. **test_03_to_10.py** - Comprehensive test suite:
   - Login automation
   - Registration forms
   - Search results
   - Table extraction
   - Newsletter subscription
   - Multi-step forms
   - Shopping cart
   - Feedback forms

### LLM-DSL Communication Example

```python
# LLM sends JSON command
command = {
    "action": "analyze_form",
    "components": [
        {"type": "dom-snapshot", "params": {"include_values": True}},
        {"type": "field-mapper", "params": {"strategy": "fuzzy"}}
    ]
}

# Bridge executes Streamware components
result = bridge.execute_llm_command(command)
```

---

## 📊 Test Results

### HTML Report

After running tests, view the report:

```bash
open test_results/report.html
# or
firefox test_results/report.html
```

### Console Output

Tests provide detailed output including:
- Component execution trace
- LLM-DSL commands sent
- Validation results
- Screenshots (in `./screenshots/`)

---

## 🔧 Architecture

### Docker Services

```
┌──────────────────┐
│ test-webserver   │  Nginx serving 10 test HTML pages
│ (port 8080)      │
└──────────────────┘

┌──────────────────┐
│ mock-ollama      │  Mock Ollama server for LLM responses
│ (port 11434)     │  Returns pre-defined JSON/YAML commands
└──────────────────┘

┌──────────────────┐
│ curllm-test      │  Test runner with Playwright
│                  │  Executes 10 integration tests
│                  │  Uses LLM-DSL Bridge
└──────────────────┘
```

### LLM-DSL Flow

```
Test → LLM Command (JSON/YAML) → LLMDSLBridge → Streamware Components → Browser Actions
```

---

## 🐛 Debugging

### View Logs

```bash
# All logs
docker-compose -f docker-compose.test.yml logs

# Specific service
docker-compose -f docker-compose.test.yml logs curllm-test
docker-compose -f docker-compose.test.yml logs mock-ollama
```

### Run Single Test

```bash
docker-compose -f docker-compose.test.yml run curllm-test \
    pytest tests/integration/test_01_simple_form.py -v
```

### Interactive Shell

```bash
docker-compose -f docker-compose.test.yml run curllm-test bash
```

---

## 📝 Environment Variables

### Test Configuration

- `CURLLM_TEST_BASE_URL` - Test pages URL (default: `http://test-webserver`)
- `CURLLM_OLLAMA_HOST` - Mock Ollama URL (default: `http://mock-ollama:11434`)
- `CURLLM_HEADLESS` - Run headless (default: `true`)
- `CURLLM_TEST_MODE` - Enable test mode (default: `true`)

### Customize

```bash
# Run tests with custom Ollama host
CURLLM_OLLAMA_HOST=http://localhost:11434 make test-docker
```

---

## 🎯 What Gets Tested

### Form Filling
- ✅ Simple contact forms
- ✅ Multi-field registration
- ✅ Login forms
- ✅ Multi-step wizards
- ✅ Checkboxes and radio buttons
- ✅ Dropdown selects

### Data Extraction
- ✅ Product listings
- ✅ Search results
- ✅ Data tables
- ✅ Shopping carts

### LLM-DSL Communication
- ✅ JSON command parsing
- ✅ YAML command parsing
- ✅ Component chaining
- ✅ Action planning
- ✅ State validation
- ✅ Field mapping

### Components Tested
- ✅ dom-snapshot (with value fix)
- ✅ dom-analyze
- ✅ field-mapper
- ✅ action-plan
- ✅ action-validate
- ✅ dom-validate
- ✅ decision-tree

---

## 🔄 Cleanup

```bash
# Stop and remove containers
docker-compose -f docker-compose.test.yml down

# Remove volumes
docker-compose -f docker-compose.test.yml down -v

# Clean test results
rm -rf test_results/* screenshots/*
```

---

## 📚 Additional Resources

- **Main Documentation**: `STREAMWARE_ARCHITECTURE.md`
- **DSL Guide**: `REFACTORING_DSL_COMPLETE.md`
- **Bug Analysis**: `DOM_FIX_ANALYSIS.md`
- **YAML Flows**: `YAML_FLOWS.md`

---

## ✅ Expected Results

After running `make test-docker`, you should see:

```
✓ 10 test pages served on http://test-webserver
✓ Mock Ollama responding on http://mock-ollama:11434
✓ All 10+ integration tests passing
✓ HTML report generated in test_results/
✓ Screenshots saved in screenshots/
```

---

**Ready to test!** Run `make test-docker` to start. 🚀
