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

from flask import Flask, Response, jsonify, render_template, request

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
            
            # Wrap user prompt with extraction-only instructions
            # Use JSON format to pass runtime params including no_form_fill
            extraction_task = f"""Przeanalizuj zawartość strony i pobierz dane produktów.

ZADANIE:
{prompt}

INSTRUKCJE:
- Odczytaj widoczną zawartość strony
- Zidentyfikuj produkty, ceny, opisy na stronie
- Zwróć dane w strukturze JSON
- Dla listy produktów - pobierz dane każdego produktu z listy
- NIE klikaj w przyciski ani linki
- Odpowiedz TYLKO danymi JSON
"""
            
            # Use JSON instruction format to pass no_form_fill runtime param
            extraction_instruction = json.dumps({
                "instruction": extraction_task,
                "params": {
                    "no_form_fill": True,
                    "no_click": True,
                    "fastpath": False,
                    "include_dom_html": True,
                }
            })
            
            result = await self.executor.execute_workflow(
                instruction=extraction_instruction,
                url=url,
                stealth_mode=stealth,
                visual_mode=False,
                use_bql=False,
            )
            
            # Check for form_fill false positive errors
            # curllm sometimes detects forms on pages and tries to fill them
            result_data = result.get("result")
            is_form_fill_error = False
            
            if isinstance(result_data, dict):
                # Check if this is a form_fill error (false positive on extraction)
                if "form_fill" in result_data or "form" in str(result_data).lower():
                    error_info = result_data.get("error", {})
                    if isinstance(error_info, dict) and error_info.get("type") == "form_fill_failed":
                        is_form_fill_error = True
                    elif result_data.get("form_fill", {}).get("submitted") is False:
                        is_form_fill_error = True
            
            if is_form_fill_error:
                # This was a form detection false positive - treat as extraction failure
                # and return empty data instead of error
                return ExtractionResult(
                    url=url,
                    success=False,
                    error="Strona zawiera formularze - ekstrakcja produktów nie powiodła się. Spróbuj podać URL bezpośrednio do strony produktu.",
                )
            
            if result.get("success"):
                return ExtractionResult(
                    url=url,
                    success=True,
                    data=result_data,
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
    
    async def extract_with_url_resolution(
        self,
        url: str,
        prompt: str,
        stealth: bool = True
    ) -> ExtractionResult:
        """
        Extract with smart URL resolution.
        
        If the original URL doesn't contain expected content,
        try to find the right page via search or category navigation.
        
        Args:
            url: Original URL
            prompt: Extraction prompt (used to determine expected content)
            stealth: Use stealth mode
            
        Returns:
            ExtractionResult with extracted data or error
        """
        try:
            from curllm_core.url_resolver import UrlResolver
            from curllm_core.browser_setup import setup_browser
            from curllm_core.stealth import apply_stealth
            
            logger.info(f"Smart extraction from: {url}")
            
            # Setup browser for URL resolution
            browser, context = await setup_browser(
                stealth_mode=stealth,
                headless=True,
            )
            
            try:
                page = await context.new_page()
                if stealth:
                    await apply_stealth(page)
                
                # Resolve URL to find correct page
                resolver = UrlResolver(page, self.executor.llm if hasattr(self.executor, 'llm') else None)
                resolved = await resolver.resolve(url, prompt)
                
                final_url = resolved.resolved_url
                resolution_info = {
                    "original_url": url,
                    "resolved_url": final_url,
                    "resolution_method": resolved.resolution_method,
                    "steps": resolved.steps_taken,
                }
                
                await page.close()
                await context.close()
                await browser.close()
                
            except Exception as e:
                logger.warning(f"URL resolution failed: {e}, using original URL")
                final_url = url
                resolution_info = {"error": str(e)}
                try:
                    await browser.close()
                except Exception:
                    pass
            
            # Now extract from the resolved URL
            result = await self.extract_from_url(final_url, prompt, stealth)
            
            # Add resolution info to result
            if result.data and isinstance(result.data, dict):
                result.data["_url_resolution"] = resolution_info
            elif result.success:
                result.data = {"_url_resolution": resolution_info, "data": result.data}
            
            # Update URL in result
            result.url = final_url
            if final_url != url:
                result.store_name = urlparse(final_url).hostname or result.store_name
            
            return result
            
        except Exception as e:
            logger.error(f"Smart extraction failed for {url}: {e}")
            return ExtractionResult(
                url=url,
                success=False,
                error=f"Smart extraction failed: {str(e)}",
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


@app.route("/api/smart-extract", methods=["POST"])
def api_smart_extract():
    """
    Smart extraction with URL resolution.
    
    If the URL doesn't contain expected content, automatically
    tries to find the right page via search or category navigation.
    
    Request body:
    {
        "url": "store_url",
        "prompt": "What to extract...",
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
        result = run_async(comp.extract_with_url_resolution(url, prompt, stealth))
        
        response_data = {
            "url": result.url,
            "store_name": result.store_name,
            "success": result.success,
            "data": result.data,
            "error": result.error,
            "timestamp": result.timestamp,
        }
        
        # Add resolution info if available
        if result.data and isinstance(result.data, dict):
            resolution = result.data.get("_url_resolution")
            if resolution:
                response_data["url_resolution"] = resolution
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Smart extraction failed: {e}")
        return jsonify({"error": str(e), "success": False}), 500


@app.route("/api/recompare", methods=["POST"])
def api_recompare():
    """
    Re-run comparison analysis on already extracted results.
    
    Request body:
    {
        "extraction_results": [...],
        "comparison_prompt": "..."
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        extraction_results = data.get("extraction_results", [])
        comparison_prompt = data.get("comparison_prompt", "")
        
        if not extraction_results:
            return jsonify({"error": "No extraction results provided"}), 400
        
        if not comparison_prompt:
            comparison_prompt = "Porównaj ceny i parametry produktów ze wszystkich sklepów. Wskaż najlepszą ofertę."
        
        # Convert dict results back to ExtractionResult objects
        results = []
        for r in extraction_results:
            results.append(ExtractionResult(
                url=r.get("url", ""),
                success=r.get("success", False),
                data=r.get("data"),
                error=r.get("error"),
            ))
        
        # Run comparison
        comp = get_comparator()
        comparison_result = run_async(comp.compare_results(results, comparison_prompt))
        
        return jsonify({
            "success": True,
            "comparison": {
                "analysis": comparison_result.analysis,
                "summary_table": comparison_result.summary_table,
                "best_price": comparison_result.best_price,
                "warnings": comparison_result.warnings,
                "timestamp": comparison_result.timestamp,
            },
        })
        
    except Exception as e:
        logger.error(f"Recompare failed: {e}")
        return jsonify({"error": str(e), "success": False}), 500


@app.route("/api/compare/stream", methods=["POST"])
def api_compare_stream():
    """
    Streaming API endpoint for price comparison with real-time logs.
    
    Uses Server-Sent Events (SSE) to stream progress updates.
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
            comparison_prompt = "Porównaj ceny i parametry produktów ze wszystkich sklepów. Wskaż najlepszą ofertę."
        
        def generate():
            """Generator for SSE streaming"""
            comp = get_comparator()
            extraction_results = []
            processed = 0
            
            # Stage 1: Extract from each URL
            yield f"data: {json.dumps({'type': 'stage', 'message': 'Etap 1: Ekstrakcja danych z poszczególnych sklepów...'})}\n\n"
            
            for i, url in enumerate(urls):
                store_name = urlparse(url).hostname or "Unknown"
                yield f"data: {json.dumps({'type': 'log', 'level': 'info', 'message': f'[{i+1}/{len(urls)}] Pobieram: {store_name}...'})}\n\n"
                
                try:
                    result = run_async(comp.extract_from_url(url, extraction_prompt, stealth))
                    extraction_results.append(result)
                    processed += 1
                    
                    yield f"data: {json.dumps({'type': 'progress', 'processed': processed, 'total': len(urls), 'store': store_name, 'success': result.success, 'error': result.error})}\n\n"
                    
                except Exception as e:
                    processed += 1
                    extraction_results.append(ExtractionResult(
                        url=url,
                        success=False,
                        error=str(e),
                    ))
                    yield f"data: {json.dumps({'type': 'progress', 'processed': processed, 'total': len(urls), 'store': store_name, 'success': False, 'error': str(e)})}\n\n"
            
            # Stage 2: Comparison
            yield f"data: {json.dumps({'type': 'stage', 'message': 'Etap 2: Analiza porównawcza z użyciem LLM...'})}\n\n"
            
            try:
                comparison_result = run_async(comp.compare_results(extraction_results, comparison_prompt))
                yield f"data: {json.dumps({'type': 'log', 'level': 'success', 'message': 'Analiza porównawcza zakończona'})}\n\n"
            except Exception as e:
                comparison_result = ComparisonResult(
                    analysis=f"Błąd analizy: {str(e)}",
                    summary_table=[],
                    warnings=[str(e)],
                )
                yield f"data: {json.dumps({'type': 'log', 'level': 'error', 'message': f'Błąd analizy: {str(e)}'})}\n\n"
            
            # Final result
            final_result = {
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
            
            yield f"data: {json.dumps({'type': 'result', 'data': final_result})}\n\n"
        
        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
            }
        )
        
    except Exception as e:
        logger.error(f"Streaming comparison failed: {e}")
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
