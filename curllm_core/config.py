#!/usr/bin/env python3
from dataclasses import dataclass
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    """Application configuration"""
    ollama_host: str = os.getenv("CURLLM_OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = os.getenv("CURLLM_MODEL", "qwen2.5:7b")
    browserless_url: str = os.getenv("BROWSERLESS_URL", "ws://localhost:3000")
    use_browserless: bool = os.getenv("CURLLM_BROWSERLESS", "false").lower() == "true"
    max_steps: int = int(os.getenv("CURLLM_MAX_STEPS", "20"))
    screenshot_dir: Path = Path(os.getenv("CURLLM_SCREENSHOT_DIR", "./screenshots"))
    enable_debug: bool = os.getenv("CURLLM_DEBUG", "false").lower() == "true"
    api_port: int = int(os.getenv("CURLLM_API_PORT", os.getenv("API_PORT", "8000")))
    num_ctx: int = int(os.getenv("CURLLM_NUM_CTX", "8192"))
    num_predict: int = int(os.getenv("CURLLM_NUM_PREDICT", "512"))
    temperature: float = float(os.getenv("CURLLM_TEMPERATURE", "0.3"))
    top_p: float = float(os.getenv("CURLLM_TOP_P", "0.9"))
    headless: bool = os.getenv("CURLLM_HEADLESS", "true").lower() == "true"
    locale: str = os.getenv("CURLLM_LOCALE", os.getenv("LOCALE", "pl-PL"))
    timezone_id: str = os.getenv("CURLLM_TIMEZONE", os.getenv("TIMEZONE", "Europe/Warsaw"))
    proxy: Optional[str] = (os.getenv("CURLLM_PROXY") or os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY") or None)
    validation_enabled: bool = os.getenv("CURLLM_VALIDATION", "true").lower() == "true"
    llm_timeout: int = int(os.getenv("CURLLM_LLM_TIMEOUT", "300"))
    hierarchical_planner_chars: int = int(os.getenv("CURLLM_HIERARCHICAL_PLANNER_CHARS", "25000"))
    
    # Vision-based form analysis
    vision_form_analysis: bool = os.getenv("CURLLM_VISION_FORM_ANALYSIS", "auto").lower() in ["true", "1", "yes", "auto"]
    vision_model: str = os.getenv("CURLLM_VISION_MODEL", "") or os.getenv("CURLLM_MODEL", "qwen2.5:7b")
    vision_confidence_threshold: float = float(os.getenv("CURLLM_VISION_CONFIDENCE_THRESHOLD", "0.7"))
    vision_detect_honeypots: bool = os.getenv("CURLLM_VISION_DETECT_HONEYPOTS", "true").lower() in ["true", "1", "yes"]
    
    # LLM-guided per-field form filling
    llm_field_filler_enabled: bool = os.getenv("CURLLM_LLM_FIELD_FILLER_ENABLED", "false").lower() in ["true", "1", "yes"]
    llm_field_max_attempts: int = int(os.getenv("CURLLM_LLM_FIELD_MAX_ATTEMPTS", "2"))
    llm_field_timeout_ms: int = int(os.getenv("CURLLM_LLM_FIELD_TIMEOUT_MS", "5000"))
    
    # LLM-based extraction orchestrator (similar to form orchestrator)
    extraction_orchestrator_enabled: bool = os.getenv("CURLLM_EXTRACTION_ORCHESTRATOR", "false").lower() in ["true", "1", "yes"]
    extraction_orchestrator_timeout: int = int(os.getenv("CURLLM_EXTRACTION_ORCHESTRATOR_TIMEOUT", "120"))
    
    # BQL-based extraction orchestrator (LLM generates BQL queries from DOM analysis)
    bql_extraction_orchestrator_enabled: bool = os.getenv("CURLLM_BQL_EXTRACTION_ORCHESTRATOR", "false").lower() in ["true", "1", "yes"]
    bql_extraction_orchestrator_timeout: int = int(os.getenv("CURLLM_BQL_EXTRACTION_ORCHESTRATOR_TIMEOUT", "120"))
    
    # Semantic Query Engine (Natural Language → Structured Query → Atomic Functions)
    semantic_query_enabled: bool = os.getenv("CURLLM_SEMANTIC_QUERY", "false").lower() in ["true", "1", "yes"]
    semantic_query_timeout: int = int(os.getenv("CURLLM_SEMANTIC_QUERY_TIMEOUT", "120"))
    
    # Iterative Extractor (Small atomic DOM queries instead of full DOM tree)
    iterative_extractor_enabled: bool = os.getenv("CURLLM_ITERATIVE_EXTRACTOR", "true").lower() in ["true", "1", "yes"]
    iterative_extractor_max_items: int = int(os.getenv("CURLLM_ITERATIVE_EXTRACTOR_MAX_ITEMS", "50"))
    
    # Progressive Context (Start small, expand only when needed)
    progressive_context_enabled: bool = os.getenv("CURLLM_PROGRESSIVE_CONTEXT", "true").lower() in ["true", "1", "yes"]
    progressive_context_initial_size: int = int(os.getenv("CURLLM_PROGRESSIVE_CONTEXT_INITIAL_SIZE", "5000"))
    
    # Planner context sizing (used by llm_planner.py)
    # CURLLM_PLANNER_BASE_CHARS - initial context size (also supports CURLLM_PLANNER_MAX_CHARS)
    planner_max_chars: int = int(os.getenv("CURLLM_PLANNER_MAX_CHARS", os.getenv("CURLLM_PLANNER_BASE_CHARS", "8000")))
    planner_growth_per_step: int = int(os.getenv("CURLLM_PLANNER_GROWTH_PER_STEP", "2000"))
    planner_max_cap: int = int(os.getenv("CURLLM_PLANNER_MAX_CAP", "20000"))
    stall_limit: int = int(os.getenv("CURLLM_STALL_LIMIT", "5"))
    
    # LLM-Guided Extractor (LLM makes decisions at each atomic step)
    llm_guided_extractor_enabled: bool = os.getenv("CURLLM_LLM_GUIDED_EXTRACTOR", "true").lower() in ["true", "1", "yes"]
    
    # Prompt format: "json" (default) or "dsl" (simplified Python-like syntax for smaller models)
    prompt_format: str = os.getenv("CURLLM_PROMPT_FORMAT", "json").lower()
    
    # Atomic actions: break complex tasks into simpler sub-tasks
    atomic_actions_enabled: bool = os.getenv("CURLLM_ATOMIC_ACTIONS", "true").lower() in ["true", "1", "yes"]
    
    # DSL System - Strategy-based extraction with knowledge base
    dsl_enabled: bool = os.getenv("CURLLM_DSL_ENABLED", "true").lower() in ["true", "1", "yes"]
    dsl_directory: str = os.getenv("CURLLM_DSL_DIR", "dsl")
    dsl_knowledge_db: str = os.getenv("CURLLM_DSL_KNOWLEDGE_DB", "dsl/knowledge.db")
    dsl_auto_save: bool = os.getenv("CURLLM_DSL_AUTO_SAVE", "true").lower() in ["true", "1", "yes"]
    dsl_max_fallbacks: int = int(os.getenv("CURLLM_DSL_MAX_FALLBACKS", "3"))

    def __post_init__(self):
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

config = Config()
