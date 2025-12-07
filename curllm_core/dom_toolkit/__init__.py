"""
DOM Toolkit - Atomic DOM Analysis with Minimal LLM Usage

Architecture:
1. Analyzers (Pure JS) - Fast, deterministic DOM analysis
2. Statistics - Pattern detection and scoring without LLM
3. Orchestrator - LLM only for high-level decisions

Design Principles:
- LLM used ONLY for orchestration (what to extract, not how)
- Statistical analysis for selector discovery
- Small atomic queries instead of large context dumps
- Helper functions that work on pre-computed DOM snapshots
"""

from .analyzers import (
    DOMStructureAnalyzer,
    PatternDetector,
    SelectorGenerator,
    PriceDetector,
)
from .statistics import (
    FrequencyAnalyzer,
    ElementClusterer,
    CandidateScorer,
)
from .orchestrator import (
    ExtractionOrchestrator,
    AtomicLLMQuery,
)

__all__ = [
    # Analyzers (Zero LLM)
    'DOMStructureAnalyzer',
    'PatternDetector', 
    'SelectorGenerator',
    'PriceDetector',
    # Statistics (Zero LLM)
    'FrequencyAnalyzer',
    'ElementClusterer',
    'CandidateScorer',
    # Orchestrator (Minimal LLM)
    'ExtractionOrchestrator',
    'AtomicLLMQuery',
]
