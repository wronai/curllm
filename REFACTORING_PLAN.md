# Curllm Core Refactoring Plan

## Current State
- **73 files** in `curllm_core/` root
- **6 components** already migrated to `streamware/components/`

## Existing Components (✅ Done)
| Component | Files | Description |
|-----------|-------|-------------|
| `navigation/` | actions.py | Click, fill, scroll, wait |
| `captcha/` | detect.py, solve.py, vision_solve.py | CAPTCHA detection & solving |
| `screenshot/` | capture.py | Page/element screenshots |
| `extraction/` | selector.py, extractor.py, container.py | Data extraction |
| `dom/` | analyze.py, context.py, query.py | DOM analysis |
| `form/` | detect.py, fill.py, submit.py, orchestrator.py | Form handling |

## Proposed New Components

### 1. `bql/` - Browser Query Language
**Files to migrate:**
- `bql.py` → `bql/engine.py`
- `bql_utils.py` → `bql/utils.py`
- `bql_extraction_orchestrator.py` → `bql/orchestrator.py`
- `semantic_query.py` → `bql/semantic.py`
- `prompt_dsl.py` → `bql/dsl.py`

### 2. `llm/` - LLM Integration
**Files to migrate:**
- `llm.py` → `llm/client.py`
- `llm_factory.py` → `llm/factory.py`
- `llm_planner.py` → `llm/planner.py`
- `llm_field_filler.py` → `llm/field_filler.py`
- `llm_filter_validator.py` → `llm/validator.py`
- `llm_container_validator.py` → `llm/container_validator.py`
- `llm_guided_extractor.py` → `llm/guided_extractor.py`
- `llm_form_orchestrator.py` → `llm/form_orchestrator.py`
- `llm_transparent_orchestrator.py` → `llm/transparent_orchestrator.py`
- `hierarchical_planner.py` → `llm/hierarchical_planner.py`
- `hierarchical_planner_v2.py` → `llm/hierarchical_planner_v2.py`

### 3. `vision/` - Visual Analysis
**Files to migrate:**
- `vision.py` → `vision/analyzer.py`
- `vision_form_analysis.py` → `vision/form_analysis.py`

### 4. `browser/` - Browser Management
**Files to migrate:**
- `browser_setup.py` → `browser/setup.py`
- `browserless.py` → `browser/browserless.py`
- `stealth.py` → `browser/stealth.py`
- `proxy.py` → `browser/proxy.py`
- `headers.py` → `browser/headers.py`

### 5. `page/` - Page Utilities
**Files to migrate:**
- `page_context.py` → `page/context.py`
- `page_utils.py` → `page/utils.py`
- `human_verify.py` → `page/verify.py`
- `dynamic_detector.py` → `page/dynamic.py`

### 6. `data/` - Data Processing
**Files to migrate:**
- `data_export.py` → `data/export.py`
- `extraction_registry.py` → `data/registry.py`
- `result_store.py` → `data/store.py`
- `result_evaluator.py` → `data/evaluator.py`
- `validation_utils.py` → `data/validation.py`
- `multi_criteria_filter.py` → `data/filter.py`

### 7. `task/` - Task Execution
**Files to migrate:**
- `executor.py` → `task/executor.py`
- `task_runner.py` → `task/runner.py`
- `instruction_parser.py` → `task/parser.py`
- `planner_progress.py` → `task/progress.py`
- `tool_retry.py` → `task/retry.py`

### 8. `error/` - Error Handling
**Files to migrate:**
- `error_handler.py` → `error/handler.py`
- `remediation.py` → `error/remediation.py`
- `diagnostics.py` → `error/diagnostics.py`

### 9. `config/` - Configuration
**Files to migrate:**
- `config.py` → `config/settings.py`
- `config_logger.py` → `config/logger.py`
- `runtime.py` → `config/runtime.py`
- `logger.py` → `config/run_logger.py`

## Files to Keep in Root (Core/Entry Points)
- `__init__.py` - Package init
- `server.py` - HTTP server
- `agent_factory.py` - Agent creation

## Files to Deprecate (Already Migrated)
- `actions.py` → wrapper to `navigation/`
- `captcha.py` → wrapper to `captcha/`
- `captcha_slider.py` → merged into `captcha/`
- `captcha_widget.py` → merged into `captcha/`
- `screenshots.py` → wrapper to `screenshot/`
- `dom_utils.py` → wrapper to `dom/`
- `form_detector.py` → wrapper to `form/`
- `form_fill.py` → wrapper to `form/`

## Migration Priority

### Phase 1 (High Priority)
1. `bql/` - Core query language
2. `llm/` - Central LLM integration

### Phase 2 (Medium Priority)
3. `browser/` - Browser management
4. `page/` - Page utilities
5. `vision/` - Visual analysis

### Phase 3 (Low Priority)
6. `data/` - Data processing
7. `task/` - Task execution
8. `error/` - Error handling
9. `config/` - Configuration

## Backward Compatibility
For each migrated file:
1. Keep original file as wrapper
2. Add deprecation warning
3. Re-export from new location
4. Update imports in dependent files

## Testing Strategy
After each component migration:
1. Run `curllm --visual <test-url>`
2. Verify imports work
3. Check for circular dependencies
