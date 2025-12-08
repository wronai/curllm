"""
Unified Extraction Pipeline Registry

Centralized tracking of all extraction attempts with full transparency.
NO HARD-CODED SELECTORS - everything is detected dynamically.

This module provides a clear audit trail of:
1. Which extractors were attempted
2. What patterns were detected
3. Why certain selectors were chosen
4. What the extraction results were
"""

from typing import Dict, List, Optional, Any
from enum import Enum
import json
from datetime import datetime


class ExtractorType(Enum):
    """Types of extractors in the pipeline"""
    LLM_GUIDED = "llm_guided"
    DYNAMIC_DETECTOR = "dynamic_detector"
    ITERATIVE = "iterative"
    BQL = "bql"
    ORCHESTRATOR = "orchestrator"
    FALLBACK = "fallback"


class ExtractorStatus(Enum):
    """Status of extraction attempt"""
    SUCCESS = "success"
    NO_DATA = "no_data"
    ERROR = "error"
    SKIPPED = "skipped"


class ExtractionAttempt:
    """
    Single extraction attempt with full metadata
    
    NO HARD-CODED SELECTORS!
    All selectors are dynamically detected and logged here.
    """
    
    def __init__(
        self,
        extractor_type: ExtractorType,
        instruction: str,
        page_url: str
    ):
        self.extractor_type = extractor_type
        self.instruction = instruction
        self.page_url = page_url
        self.timestamp = datetime.now().isoformat()
        self.status = ExtractorStatus.SKIPPED
        self.selectors_detected = []  # Dynamic selectors found
        self.selector_chosen = None   # Final selector chosen
        self.selection_reason = None  # Why this selector?
        self.score_breakdown = {}     # Scoring details
        self.products_found = 0
        self.products_filtered = 0
        self.error_message = None
        self.duration_ms = 0
        
    def add_detected_selector(
        self,
        selector: str,
        score: float,
        specificity: int,
        count: int,
        metadata: Dict[str, Any]
    ):
        """
        Log a dynamically detected selector candidate
        
        NO HARD-CODED! This tracks what was found in the DOM.
        """
        self.selectors_detected.append({
            "selector": selector,
            "score": score,
            "specificity": specificity,
            "count": count,
            "has_price": metadata.get("has_price", False),
            "has_link": metadata.get("has_link", False),
            "has_image": metadata.get("has_image", False),
            "sample_text": metadata.get("sample_text", "")[:100]
        })
    
    def set_chosen_selector(
        self,
        selector: str,
        reason: str,
        score_breakdown: Dict[str, float]
    ):
        """
        Mark which selector was chosen and why
        
        Provides transparency into selection logic.
        """
        self.selector_chosen = selector
        self.selection_reason = reason
        self.score_breakdown = score_breakdown
    
    def set_result(
        self,
        status: ExtractorStatus,
        products_found: int = 0,
        products_filtered: int = 0,
        error_message: str = None
    ):
        """Log extraction result"""
        self.status = status
        self.products_found = products_found
        self.products_filtered = products_filtered
        self.error_message = error_message
    
    def to_dict(self) -> Dict[str, Any]:
        """Export attempt as transparent log"""
        return {
            "extractor": self.extractor_type.value,
            "timestamp": self.timestamp,
            "status": self.status.value,
            "instruction": self.instruction,
            "page_url": self.page_url,
            "selectors_detected": self.selectors_detected,
            "selector_chosen": self.selector_chosen,
            "selection_reason": self.selection_reason,
            "score_breakdown": self.score_breakdown,
            "products_found": self.products_found,
            "products_filtered": self.products_filtered,
            "error": self.error_message,
            "duration_ms": self.duration_ms
        }


class ExtractionPipeline:
    """
    Unified extraction pipeline with full transparency
    
    Orchestrates multiple extractors and tracks everything:
    - Which extractors ran
    - What they detected
    - Why selections were made
    - What succeeded/failed
    
    NO HARD-CODED SELECTORS - everything is dynamic!
    """
    
    def __init__(self, instruction: str, page_url: str):
        self.instruction = instruction
        self.page_url = page_url
        self.attempts: List[ExtractionAttempt] = []
        self.final_result = None
        self.winner = None
    
    def start_attempt(self, extractor_type: ExtractorType) -> ExtractionAttempt:
        """Begin a new extraction attempt"""
        attempt = ExtractionAttempt(extractor_type, self.instruction, self.page_url)
        self.attempts.append(attempt)
        return attempt
    
    def set_winner(self, extractor_type: ExtractorType, products: List[Dict]):
        """Mark which extractor succeeded"""
        self.winner = extractor_type.value
        self.final_result = products
    
    def get_transparency_report(self) -> Dict[str, Any]:
        """
        Generate full transparency report
        
        Shows complete audit trail of:
        - All extractors attempted
        - All selectors dynamically detected
        - Scoring breakdowns
        - Why certain extractors succeeded/failed
        """
        return {
            "instruction": self.instruction,
            "page_url": self.page_url,
            "winner": self.winner,
            "products_count": len(self.final_result) if self.final_result else 0,
            "attempts": [attempt.to_dict() for attempt in self.attempts],
            "summary": self._generate_summary()
        }
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate summary statistics"""
        return {
            "total_attempts": len(self.attempts),
            "extractors_tried": [a.extractor_type.value for a in self.attempts],
            "successful": [
                a.extractor_type.value 
                for a in self.attempts 
                if a.status == ExtractorStatus.SUCCESS
            ],
            "total_selectors_detected": sum(
                len(a.selectors_detected) for a in self.attempts
            ),
            "unique_selectors": len(set(
                a.selector_chosen 
                for a in self.attempts 
                if a.selector_chosen
            ))
        }
    
    def print_transparency_log(self):
        """Print human-readable transparency log"""
        print("\n" + "="*60)
        print("🔍 EXTRACTION PIPELINE TRANSPARENCY REPORT")
        print("="*60)
        print(f"\n📝 Instruction: {self.instruction}")
        print(f"🌐 URL: {self.page_url}")
        print(f"🏆 Winner: {self.winner or 'None'}")
        print(f"📦 Products Found: {len(self.final_result) if self.final_result else 0}")
        
        print(f"\n\n📊 EXTRACTION ATTEMPTS ({len(self.attempts)} total):")
        for i, attempt in enumerate(self.attempts, 1):
            print(f"\n  {i}. {attempt.extractor_type.value.upper()}")
            print(f"     Status: {attempt.status.value}")
            
            if attempt.selectors_detected:
                print(f"     Selectors Detected: {len(attempt.selectors_detected)}")
                for sel in attempt.selectors_detected[:3]:  # Show top 3
                    print(f"       - {sel['selector']} (score: {sel['score']:.1f})")
            
            if attempt.selector_chosen:
                print(f"     ✅ Chosen: {attempt.selector_chosen}")
                print(f"     Reason: {attempt.selection_reason}")
            
            if attempt.products_found > 0:
                print(f"     📦 Found: {attempt.products_found} products")
                if attempt.products_filtered != attempt.products_found:
                    print(f"     💰 Filtered: {attempt.products_filtered} products")
            
            if attempt.error_message:
                print(f"     ❌ Error: {attempt.error_message}")
        
        print("\n" + "="*60 + "\n")
