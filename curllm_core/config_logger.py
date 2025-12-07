"""
Configuration Logger - Centralized config mapping and logging

This module provides a single source of truth for all configuration variables,
their mappings to environment variables, and utilities for logging them.

Reusable across different contexts: executor, tests, CLI, etc.
"""

from typing import Dict, Any, Optional, List
from .config import config


def get_all_config_variables() -> Dict[str, Any]:
    """
    Get all configuration variables with their env names and current values.
    
    Returns:
        Dict mapping env variable names to their current values
    """
    # Core configuration
    config_map = {
        # Core
        "CURLLM_MODEL": config.ollama_model,
        "CURLLM_OLLAMA_HOST": config.ollama_host,
        "CURLLM_BROWSERLESS": config.use_browserless,
        "BROWSERLESS_URL": config.browserless_url,
        "CURLLM_MAX_STEPS": config.max_steps,
        "CURLLM_SCREENSHOT_DIR": str(config.screenshot_dir),
        "CURLLM_DEBUG": config.enable_debug,
        "CURLLM_API_PORT": config.api_port,
        
        # LLM settings
        "CURLLM_NUM_CTX": config.num_ctx,
        "CURLLM_NUM_PREDICT": config.num_predict,
        "CURLLM_TEMPERATURE": config.temperature,
        "CURLLM_TOP_P": config.top_p,
        "CURLLM_LLM_TIMEOUT": config.llm_timeout,
        
        # Browser settings
        "CURLLM_HEADLESS": config.headless,
        "CURLLM_LOCALE": config.locale,
        "CURLLM_TIMEZONE": config.timezone_id,
        "CURLLM_PROXY": config.proxy or "None",
        
        # Validation
        "CURLLM_VALIDATION": config.validation_enabled,
        
        # Hierarchical planner
        "CURLLM_HIERARCHICAL_PLANNER_CHARS": config.hierarchical_planner_chars,
        
        # Vision-based form analysis
        "CURLLM_VISION_FORM_ANALYSIS": config.vision_form_analysis,
        "CURLLM_VISION_MODEL": config.vision_model,
        "CURLLM_VISION_CONFIDENCE_THRESHOLD": config.vision_confidence_threshold,
        "CURLLM_VISION_DETECT_HONEYPOTS": config.vision_detect_honeypots,
        
        # LLM-guided per-field form filling
        "CURLLM_LLM_FIELD_FILLER_ENABLED": config.llm_field_filler_enabled,
        "CURLLM_LLM_FIELD_MAX_ATTEMPTS": config.llm_field_max_attempts,
        "CURLLM_LLM_FIELD_TIMEOUT_MS": config.llm_field_timeout_ms,
        
        # Extraction orchestrators
        "CURLLM_EXTRACTION_ORCHESTRATOR": config.extraction_orchestrator_enabled,
        "CURLLM_EXTRACTION_ORCHESTRATOR_TIMEOUT": config.extraction_orchestrator_timeout,
        "CURLLM_BQL_EXTRACTION_ORCHESTRATOR": config.bql_extraction_orchestrator_enabled,
        "CURLLM_BQL_EXTRACTION_ORCHESTRATOR_TIMEOUT": config.bql_extraction_orchestrator_timeout,
        "CURLLM_SEMANTIC_QUERY": config.semantic_query_enabled,
        "CURLLM_SEMANTIC_QUERY_TIMEOUT": config.semantic_query_timeout,
        "CURLLM_ITERATIVE_EXTRACTOR": config.iterative_extractor_enabled,
        "CURLLM_ITERATIVE_EXTRACTOR_MAX_ITEMS": config.iterative_extractor_max_items,
        "CURLLM_PROGRESSIVE_CONTEXT": config.progressive_context_enabled,
        "CURLLM_PROGRESSIVE_CONTEXT_INITIAL_SIZE": config.progressive_context_initial_size,
        "CURLLM_LLM_GUIDED_EXTRACTOR": config.llm_guided_extractor_enabled,
        
        # DSL System
        "CURLLM_DSL_ENABLED": config.dsl_enabled,
        "CURLLM_DSL_DIR": config.dsl_directory,
        "CURLLM_DSL_KNOWLEDGE_DB": config.dsl_knowledge_db,
        "CURLLM_DSL_AUTO_SAVE": config.dsl_auto_save,
        "CURLLM_DSL_MAX_FALLBACKS": config.dsl_max_fallbacks,
    }
    
    return config_map


def get_runtime_config_map() -> Dict[str, str]:
    """
    Get mapping of runtime parameter names to their env variable names.
    
    Used for logging runtime flags that can be overridden per-request.
    
    Returns:
        Dict mapping runtime param names to env variable names
    """
    return {
        "include_dom_html": "CURLLM_INCLUDE_DOM_HTML",
        "dom_max_chars": "CURLLM_DOM_MAX_CHARS",
        "dom_max_cap": "CURLLM_DOM_MAX_CAP",
        "smart_click": "CURLLM_SMART_CLICK",
        "action_timeout_ms": "CURLLM_ACTION_TIMEOUT_MS",
        "wait_after_click_ms": "CURLLM_WAIT_AFTER_CLICK_MS",
        "wait_after_nav_ms": "CURLLM_WAIT_AFTER_NAV_MS",
        "no_click": "CURLLM_NO_CLICK",
        "scroll_load": "CURLLM_SCROLL_LOAD",
        "fastpath": "CURLLM_FASTPATH",
        "refine_instruction": "CURLLM_REFINE_INSTRUCTION",
        "use_external_slider_solver": "CURLLM_USE_EXTERNAL_SLIDER_SOLVER",
        "stall_limit": "CURLLM_STALL_LIMIT",
        "planner_growth_per_step": "CURLLM_PLANNER_GROWTH_PER_STEP",
        "planner_max_cap": "CURLLM_PLANNER_MAX_CAP",
        "planner_base_chars": "CURLLM_PLANNER_BASE_CHARS",
        "store_results": "CURLLM_STORE_RESULTS",
        "result_key": "CURLLM_RESULT_KEY",
        "diff_mode": "CURLLM_DIFF_MODE",
        "diff_fields": "CURLLM_DIFF_FIELDS",
        "keep_history": "CURLLM_KEEP_HISTORY",
        "include_prev_results": "CURLLM_INCLUDE_PREV_RESULTS",
        "runtime_preset": "CURLLM_RUNTIME_PRESET",
    }


def log_all_config(run_logger, visual_mode: bool, stealth_mode: bool, use_bql: bool, runtime: Optional[Dict[str, Any]] = None) -> None:
    """
    Log all configuration variables to run logger.
    
    This is the centralized function for logging config at the start of a run.
    
    Args:
        run_logger: Logger instance with log_kv method
        visual_mode: Whether visual mode is enabled
        stealth_mode: Whether stealth mode is enabled
        use_bql: Whether BQL is being used
        runtime: Optional runtime parameters dict
    """
    # Log core config
    config_vars = get_all_config_variables()
    
    # Log mode flags first (most important)
    run_logger.log_kv("CURLLM_MODEL", config_vars["CURLLM_MODEL"])
    run_logger.log_kv("CURLLM_OLLAMA_HOST", config_vars["CURLLM_OLLAMA_HOST"])
    run_logger.log_kv("VISUAL_MODE", str(visual_mode))
    run_logger.log_kv("STEALTH_MODE", str(stealth_mode))
    run_logger.log_kv("USE_BQL", str(use_bql))
    
    # Log LLM field filler config (important for debugging)
    run_logger.log_kv("CURLLM_LLM_FIELD_FILLER_ENABLED", str(config_vars["CURLLM_LLM_FIELD_FILLER_ENABLED"]))
    run_logger.log_kv("CURLLM_LLM_FIELD_MAX_ATTEMPTS", str(config_vars["CURLLM_LLM_FIELD_MAX_ATTEMPTS"]))
    run_logger.log_kv("CURLLM_LLM_FIELD_TIMEOUT_MS", str(config_vars["CURLLM_LLM_FIELD_TIMEOUT_MS"]))
    
    # Log runtime flags if provided
    if runtime:
        runtime_map = get_runtime_config_map()
        for param_name, env_name in runtime_map.items():
            if param_name in runtime:
                run_logger.log_kv(env_name, str(runtime.get(param_name)))
    
    # Log remaining core config (alphabetically for consistency)
    core_keys = [
        "CURLLM_BROWSERLESS",
        "BROWSERLESS_URL",
        "CURLLM_MAX_STEPS",
        "CURLLM_SCREENSHOT_DIR",
        "CURLLM_DEBUG",
        "CURLLM_API_PORT",
        "CURLLM_NUM_CTX",
        "CURLLM_NUM_PREDICT",
        "CURLLM_TEMPERATURE",
        "CURLLM_TOP_P",
        "CURLLM_LLM_TIMEOUT",
        "CURLLM_HEADLESS",
        "CURLLM_LOCALE",
        "CURLLM_TIMEZONE",
        "CURLLM_PROXY",
        "CURLLM_VALIDATION",
        "CURLLM_HIERARCHICAL_PLANNER_CHARS",
        "CURLLM_VISION_FORM_ANALYSIS",
        "CURLLM_VISION_MODEL",
        "CURLLM_VISION_CONFIDENCE_THRESHOLD",
        "CURLLM_VISION_DETECT_HONEYPOTS",
        "CURLLM_EXTRACTION_ORCHESTRATOR",
        "CURLLM_EXTRACTION_ORCHESTRATOR_TIMEOUT",
        "CURLLM_BQL_EXTRACTION_ORCHESTRATOR",
        "CURLLM_BQL_EXTRACTION_ORCHESTRATOR_TIMEOUT",
        "CURLLM_SEMANTIC_QUERY",
        "CURLLM_SEMANTIC_QUERY_TIMEOUT",
        "CURLLM_ITERATIVE_EXTRACTOR",
        "CURLLM_ITERATIVE_EXTRACTOR_MAX_ITEMS",
        "CURLLM_PROGRESSIVE_CONTEXT",
        "CURLLM_PROGRESSIVE_CONTEXT_INITIAL_SIZE",
        "CURLLM_LLM_GUIDED_EXTRACTOR",
    ]
    
    for key in core_keys:
        if key in config_vars:
            run_logger.log_kv(key, str(config_vars[key]))


def get_config_summary() -> Dict[str, Any]:
    """
    Get a summary of current configuration for API responses or debugging.
    
    Returns:
        Dict with categorized configuration values
    """
    config_vars = get_all_config_variables()
    
    return {
        "core": {
            "model": config_vars["CURLLM_MODEL"],
            "ollama_host": config_vars["CURLLM_OLLAMA_HOST"],
            "max_steps": config_vars["CURLLM_MAX_STEPS"],
            "debug": config_vars["CURLLM_DEBUG"],
        },
        "llm": {
            "num_ctx": config_vars["CURLLM_NUM_CTX"],
            "num_predict": config_vars["CURLLM_NUM_PREDICT"],
            "temperature": config_vars["CURLLM_TEMPERATURE"],
            "top_p": config_vars["CURLLM_TOP_P"],
            "timeout": config_vars["CURLLM_LLM_TIMEOUT"],
        },
        "browser": {
            "headless": config_vars["CURLLM_HEADLESS"],
            "locale": config_vars["CURLLM_LOCALE"],
            "timezone": config_vars["CURLLM_TIMEZONE"],
            "proxy": config_vars["CURLLM_PROXY"],
        },
        "features": {
            "hierarchical_planner_chars": config_vars["CURLLM_HIERARCHICAL_PLANNER_CHARS"],
            "vision_form_analysis": config_vars["CURLLM_VISION_FORM_ANALYSIS"],
            "vision_model": config_vars["CURLLM_VISION_MODEL"],
            "llm_field_filler_enabled": config_vars["CURLLM_LLM_FIELD_FILLER_ENABLED"],
        }
    }


def format_config_for_cli() -> List[str]:
    """
    Format configuration for CLI output (e.g., --config flag).
    
    Returns:
        List of formatted strings for display
    """
    config_vars = get_all_config_variables()
    lines = []
    
    lines.append("=== Configuration ===")
    lines.append(f"Model: {config_vars['CURLLM_MODEL']}")
    lines.append(f"Ollama Host: {config_vars['CURLLM_OLLAMA_HOST']}")
    lines.append(f"Max Steps: {config_vars['CURLLM_MAX_STEPS']}")
    lines.append(f"Headless: {config_vars['CURLLM_HEADLESS']}")
    lines.append(f"Vision Form Analysis: {config_vars['CURLLM_VISION_FORM_ANALYSIS']}")
    lines.append(f"LLM Field Filler: {config_vars['CURLLM_LLM_FIELD_FILLER_ENABLED']}")
    lines.append(f"Hierarchical Planner Threshold: {config_vars['CURLLM_HIERARCHICAL_PLANNER_CHARS']} chars")
    
    return lines


def validate_config() -> List[str]:
    """
    Validate configuration and return list of warnings/errors.
    
    Returns:
        List of warning/error messages (empty if all OK)
    """
    warnings = []
    config_vars = get_all_config_variables()
    
    # Check if critical settings are misconfigured
    if config_vars["CURLLM_NUM_CTX"] < 4096:
        warnings.append("⚠️  CURLLM_NUM_CTX is low (<4096), may cause context overflow")
    
    if config_vars["CURLLM_MAX_STEPS"] < 5:
        warnings.append("⚠️  CURLLM_MAX_STEPS is very low (<5), tasks may not complete")
    
    if config_vars["CURLLM_LLM_TIMEOUT"] < 30:
        warnings.append("⚠️  CURLLM_LLM_TIMEOUT is very low (<30s), LLM calls may timeout")
    
    if config_vars["CURLLM_HIERARCHICAL_PLANNER_CHARS"] > 50000:
        warnings.append("⚠️  CURLLM_HIERARCHICAL_PLANNER_CHARS is high (>50k), may slow down")
    
    return warnings


# Export main functions
__all__ = [
    "get_all_config_variables",
    "get_runtime_config_map",
    "log_all_config",
    "get_config_summary",
    "format_config_for_cli",
    "validate_config",
]
