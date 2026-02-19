# Refactoring TODO

## Code Quality Issues

### Large Files (>500 lines)
| File | Lines | Priority |
|------|-------|----------|
| `url_resolution/resolver.py` | 1131 | Medium |
| `dsl/executor.py` | 1101 | Low (has v2) |
| `iterative_extractor.py` | 1052 | Low (deprecated) |
| `form_fill.py` | 1000 | Low (has v2) |
| `dom/helpers.py` | 819 | Medium |
| `validation/task_validator.py` | 806 | Medium |

### Long Functions (>100 lines)
| Function | Lines | Action |
|----------|-------|--------|
| `form_fill.py::deterministic_form_fill` | 925 | Use v2 instead |
| `form/orchestrator.py::orchestrate_form_fill` | 542 | Use v2 instead |
| `execution/executor.py::execute_workflow` | 444 | Split into phases |
| `running/runner.py::run_task` | 413 | Split into steps |
| `llm_planner.py::generate_action` | 334 | Extract helpers |
| `result_evaluator.py::evaluate_run_success` | 308 | Simplify logic |

## Completed Refactoring

### v1 → v2 Migration
- [x] `form_fill.py` → `form_fill_llm.py`
- [x] `orchestrators/form.py` → `orchestrators/form_llm.py`
- [x] `orchestrators/auth.py` → `orchestrators/auth_llm.py`
- [x] `orchestrators/social.py` → `orchestrators/social_llm.py`
- [x] `orchestrators/ecommerce.py` → `orchestrators/ecommerce_llm.py`
- [x] `extraction/extractor.py` → `extraction/extractor_llm.py`
- [x] `dsl/executor.py` → `dsl/executor_llm.py`
- [x] `hierarchical/planner.py` → `hierarchical/planner_llm.py`

### Deprecated Files (moved to deprecated/)
- `atomic_query.py`
- `cli_orchestrator.py`
- `extraction_registry.py`
- `hierarchical_planner_v2.py`
- `hybrid_selector_ranker.py`
- `llm_form_orchestrator.py`
- `llm_transparent_orchestrator.py`
- `prompt_dsl.py`

## Future Work

### High Priority (DONE ✅)
1. ~~Add more integration tests for v2 modules~~ ✅ (36 tests)
2. ~~Update CLI to support `--v1` flag~~ ✅ (v2 is default)
3. ~~Document v2 API in detail~~ ✅ (MIGRATION_V2.md)

### Medium Priority
1. Split large executor.py into phases
2. Consolidate form-related modules
3. Improve error handling consistency

### Low Priority
1. Reduce cognitive complexity in legacy modules
2. Add type hints to all public APIs
3. Improve logging consistency
