#!/usr/bin/env python3
"""
Price Comparator Web Application

A Flask-based web service for comparing prices and products across multiple online stores.
Features:
- Multi-URL parallel extraction
- Two-stage processing (individual extraction + comparative analysis)
- HTML table results with LLM-powered comparisons
"""

import asyncio
import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from flask import Flask, jsonify, render_template, request

# Add parent directory to path to import curllm_core
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from curllm_core.executor import CurllmExecutor
from curllm_core.llm_config import LLMConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder="templates", static_folder="static")

# Configuration
MAX_CONCURRENT_URLS = int(os.getenv("MAX_CONCURRENT_URLS", "5"))
EXTRACTION_TIMEOUT = int(os.getenv("EXTRACTION_TIMEOUT", "120"))


@dataclass
class ExtractionResult:
    """Result from a single URL extraction"""
    url: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    store_name: str = ""
    
    def __post_init__(self):
        if not self.store_name and self.url:
            self.store_name = urlparse(self.url).hostname or "Unknown"


@dataclass
class ComparisonResult:
    """Result from comparative analysis"""
    analysis: str
    summary_table: List[Dict[str, Any]]
    best_price: Optional[Dict[str, Any]] = None
    warnings: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class PriceComparator:
    """
    Multi-URL price comparison engine using curllm.
    
    Workflow:
    1. Extract product data from each URL in parallel
    2. Aggregate and normalize results
    3. Run comparative analysis with LLM
    """
    
    def __init__(self, llm_provider: Optional[str] = None):
        """
        Initialize comparator.
        
        Args:
            llm_provider: Optional LLM provider string (e.g., "openai/gpt-4o-mini")
        """
        llm_config = LLMConfig(provider=llm_provider) if llm_provider else None
        self.executor = CurllmExecutor(llm_config=llm_config)
        self.thread_pool = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_URLS)
    
    async def extract_from_url(
        self,
        url: str,
        prompt: str,
        stealth: bool = True
    ) -> ExtractionResult:
        """
        Extract product data from a single URL.
        
        Args:
            url: Target URL
            prompt: Extraction prompt
            stealth: Use stealth mode
            
        Returns:
            ExtractionResult with extracted data or error
        """
        try:
            logger.info(f"Extracting from: {url}")
            
            result = await self.executor.execute_workflow(
                instruction=prompt,
                url=url,
                stealth_mode=stealth,
                visual_mode=False,
                use_bql=False,
            )
            
            if result.get("success"):
                return ExtractionResult(
                    url=url,
                    success=True,
                    data=result.get("result"),
                )
            else:
                return ExtractionResult(
                    url=url,
                    success=False,
                    error=result.get("error") or result.get("reason", "Unknown error"),
                )
                
        except Exception as e:
            logger.error(f"Extraction failed for {url}: {e}")
            return ExtractionResult(
                url=url,
                success=False,
                error=str(e),
            )
    
    async def extract_from_multiple_urls(
        self,
        urls: List[str],
        prompt: str,
        stealth: bool = True
    ) -> List[ExtractionResult]:
        """
        Extract product data from multiple URLs concurrently.
        
        Args:
            urls: List of target URLs
            prompt: Extraction prompt applied to all URLs
            stealth: Use stealth mode
            
        Returns:
            List of ExtractionResult objects
        """
        tasks = [
            self.extract_from_url(url, prompt, stealth)
            for url in urls
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        extraction_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                extraction_results.append(ExtractionResult(
                    url=urls[i],
                    success=False,
                    error=str(result),
                ))
            else:
                extraction_results.append(result)
        
        return extraction_results
    
    async def compare_results(
        self,
        extraction_results: List[ExtractionResult],
        comparison_prompt: str
    ) -> ComparisonResult:
        """
        Run comparative analysis on extracted results using LLM.
        
        Args:
            extraction_results: List of extraction results to compare
            comparison_prompt: Prompt describing what to compare
            
        Returns:
            ComparisonResult with analysis and summary table
        """
        # Prepare data for LLM
        successful_results = [r for r in extraction_results if r.success]
        
        if not successful_results:
            return ComparisonResult(
                analysis="Nie udało się pobrać danych z żadnego ze sklepów.",
                summary_table=[],
                warnings=["Wszystkie ekstrakcje zakończyły się błędem"],
            )
        
        # Build context for LLM comparison
        context_parts = []
        for result in successful_results:
            context_parts.append(f"""
=== Sklep: {result.store_name} ===
URL: {result.url}
Dane produktu:
{json.dumps(result.data, indent=2, ensure_ascii=False)}
""")
        
        full_context = "\n".join(context_parts)
        
        # Prepare comparison instruction
        comparison_instruction = f"""
Analizujesz dane o produktach z wielu sklepów internetowych.

KONTEKST DANYCH:
{full_context}

ZADANIE:
{comparison_prompt}

Odpowiedz w formacie JSON z następującą strukturą:
{{
    "analysis": "Szczegółowa analiza porównawcza (tekst)",
    "summary_table": [
        {{
            "store": "nazwa sklepu",
            "product_name": "nazwa produktu",
            "price": "cena",
            "currency": "waluta",
            "availability": "dostępność",
            "rating": "ocena",
            "key_features": ["cecha1", "cecha2"],
            "pros": ["zaleta1"],
            "cons": ["wada1"],
            "url": "url produktu"
        }}
    ],
    "best_price": {{
        "store": "nazwa sklepu z najlepszą ceną",
        "price": "najlepsza cena",
        "url": "url"
    }},
    "recommendations": "Rekomendacje zakupowe"
}}
"""
        
        try:
            # Use LLM for comparison
            from curllm_core.llm_factory import setup_llm
            
            llm = setup_llm()
            response = await llm.ainvoke(comparison_instruction)
            
            # Parse response
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Try to extract JSON from response
            try:
                # Find JSON in response
                import re
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    comparison_data = json.loads(json_match.group())
                else:
                    comparison_data = {
                        "analysis": response_text,
                        "summary_table": []
                    }
            except json.JSONDecodeError:
                comparison_data = {
                    "analysis": response_text,
                    "summary_table": []
                }
            
            return ComparisonResult(
                analysis=comparison_data.get("analysis", ""),
                summary_table=comparison_data.get("summary_table", []),
                best_price=comparison_data.get("best_price"),
                warnings=[],
            )
            
        except Exception as e:
            logger.error(f"Comparison analysis failed: {e}")
            return ComparisonResult(
                analysis=f"Błąd analizy porównawczej: {str(e)}",
                summary_table=[],
                warnings=[str(e)],
            )
    
    async def full_comparison(
        self,
        urls: List[str],
        extraction_prompt: str,
        comparison_prompt: str,
        stealth: bool = True
    ) -> Dict[str, Any]:
        """
        Perform full price comparison workflow.
        
        Args:
            urls: List of product URLs to compare
            extraction_prompt: Prompt for extracting data from each URL
            comparison_prompt: Prompt for comparative analysis
            stealth: Use stealth mode for extraction
            
        Returns:
            Complete comparison result with extraction data and analysis
        """
        # Stage 1: Extract from all URLs
        extraction_results = await self.extract_from_multiple_urls(
            urls, extraction_prompt, stealth
        )
        
        # Stage 2: Compare extracted results
        comparison_result = await self.compare_results(
            extraction_results, comparison_prompt
        )
        
        return {
            "success": True,
            "extraction_results": [
                {
                    "url": r.url,
                    "store_name": r.store_name,
                    "success": r.success,
                    "data": r.data,
                    "error": r.error,
                    "timestamp": r.timestamp,
                }
                for r in extraction_results
            ],
            "comparison": {
                "analysis": comparison_result.analysis,
                "summary_table": comparison_result.summary_table,
                "best_price": comparison_result.best_price,
                "warnings": comparison_result.warnings,
                "timestamp": comparison_result.timestamp,
            },
            "timestamp": datetime.now().isoformat(),
        }


# Global comparator instance
comparator = None


def get_comparator() -> PriceComparator:
    """Get or create global comparator instance"""
    global comparator
    if comparator is None:
        llm_provider = os.getenv("LLM_PROVIDER")
        comparator = PriceComparator(llm_provider=llm_provider)
    return comparator


def run_async(coro):
    """Run async coroutine in sync context"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# Flask Routes

@app.route("/")
def index():
    """Main page with comparison form"""
    return render_template("index.html")


@app.route("/health")
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "price-comparator"})


@app.route("/api/compare", methods=["POST"])
def api_compare():
    """
    API endpoint for price comparison.
    
    Request body:
    {
        "urls": ["url1", "url2", ...],
        "extraction_prompt": "Extract product name, price, specifications...",
        "comparison_prompt": "Compare prices and features across all stores...",
        "stealth": true
    }
    
    Returns comparison results in JSON format.
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        urls = data.get("urls", [])
        extraction_prompt = data.get("extraction_prompt", "")
        comparison_prompt = data.get("comparison_prompt", "")
        stealth = data.get("stealth", True)
        
        if not urls:
            return jsonify({"error": "No URLs provided"}), 400
        
        if not extraction_prompt:
            return jsonify({"error": "No extraction prompt provided"}), 400
        
        if not comparison_prompt:
            # Default comparison prompt
            comparison_prompt = "Porównaj ceny i parametry produktów ze wszystkich sklepów. Wskaż najlepszą ofertę."
        
        # Run comparison
        comp = get_comparator()
        result = run_async(comp.full_comparison(
            urls=urls,
            extraction_prompt=extraction_prompt,
            comparison_prompt=comparison_prompt,
            stealth=stealth,
        ))
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Comparison failed: {e}")
        return jsonify({"error": str(e), "success": False}), 500


@app.route("/api/extract", methods=["POST"])
def api_extract():
    """
    API endpoint for single URL extraction.
    
    Request body:
    {
        "url": "product_url",
        "prompt": "Extract product data...",
        "stealth": true
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        url = data.get("url", "")
        prompt = data.get("prompt", "")
        stealth = data.get("stealth", True)
        
        if not url:
            return jsonify({"error": "No URL provided"}), 400
        
        if not prompt:
            return jsonify({"error": "No prompt provided"}), 400
        
        comp = get_comparator()
        result = run_async(comp.extract_from_url(url, prompt, stealth))
        
        return jsonify({
            "url": result.url,
            "store_name": result.store_name,
            "success": result.success,
            "data": result.data,
            "error": result.error,
            "timestamp": result.timestamp,
        })
        
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return jsonify({"error": str(e), "success": False}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║           🏷️  Price Comparator - curllm                       ║
║══════════════════════════════════════════════════════════════║
║  Web Interface: http://localhost:{port}                        ║
║  API Endpoint:  http://localhost:{port}/api/compare            ║
║  Health Check:  http://localhost:{port}/health                 ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    app.run(host="0.0.0.0", port=port, debug=debug)
