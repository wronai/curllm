#!/usr/bin/env python3
"""
Bulk Form Filler Web Application

A Flask-based web service for submitting data to multiple forms simultaneously.
Features:
- Multi-URL form submission
- Two-stage processing (field detection + form filling)
- LLM-powered field mapping
- Real-time progress streaming
"""

import asyncio
import json
import logging
import os
import re
import sys
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
MAX_CONCURRENT_FORMS = int(os.getenv("MAX_CONCURRENT_FORMS", "3"))
FORM_TIMEOUT = int(os.getenv("FORM_TIMEOUT", "60"))


@dataclass
class FormField:
    """Detected form field"""
    name: str
    field_type: str  # text, email, textarea, select, checkbox, radio
    label: str = ""
    placeholder: str = ""
    required: bool = False
    options: List[str] = field(default_factory=list)


@dataclass
class FormResult:
    """Result from a single form submission"""
    url: str
    success: bool
    fields_detected: List[Dict[str, Any]] = field(default_factory=list)
    fields_filled: Dict[str, str] = field(default_factory=dict)
    submitted: bool = False
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    site_name: str = ""
    
    def __post_init__(self):
        if not self.site_name and self.url:
            self.site_name = urlparse(self.url).hostname or "Unknown"


@dataclass
class BulkFormResult:
    """Result from bulk form submission"""
    total: int
    successful: int
    failed: int
    results: List[FormResult]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class BulkFormFiller:
    """
    Multi-URL form filling engine using curllm.
    
    Workflow:
    1. Detect form fields on each page
    2. Map user data to detected fields using LLM
    3. Fill and submit forms
    """
    
    def __init__(self, llm_provider: Optional[str] = None):
        llm_config = LLMConfig(provider=llm_provider) if llm_provider else None
        self.executor = CurllmExecutor(llm_config=llm_config)
    
    async def detect_fields(self, url: str) -> FormResult:
        """
        Detect form fields on a page.
        """
        try:
            logger.info(f"Detecting fields on: {url}")
            
            instruction = """
Wykryj wszystkie pola formularza na tej stronie.
Dla każdego pola podaj:
- name: nazwa pola (atrybut name lub id)
- type: typ pola (text, email, tel, textarea, select, checkbox, radio)
- label: etykieta pola
- placeholder: tekst placeholder
- required: czy pole jest wymagane

Zwróć w formacie JSON:
{
    "fields": [
        {"name": "email", "type": "email", "label": "Email", "required": true},
        {"name": "message", "type": "textarea", "label": "Wiadomość", "required": true}
    ],
    "form_action": "url formularza lub null",
    "form_type": "contact|login|register|search|newsletter|other"
}
"""
            
            result = await self.executor.execute_workflow(
                instruction=instruction,
                url=url,
                stealth_mode=True,
                visual_mode=False,
            )
            
            if result.get("success"):
                data = result.get("result", {})
                fields = data.get("fields", []) if isinstance(data, dict) else []
                return FormResult(
                    url=url,
                    success=True,
                    fields_detected=fields,
                )
            else:
                return FormResult(
                    url=url,
                    success=False,
                    error=result.get("error") or result.get("reason", "Unknown error"),
                )
                
        except Exception as e:
            logger.error(f"Field detection failed for {url}: {e}")
            return FormResult(
                url=url,
                success=False,
                error=str(e),
            )
    
    async def fill_form(
        self,
        url: str,
        form_data: Dict[str, str],
        field_mapping_prompt: str = "",
        submit: bool = True
    ) -> FormResult:
        """
        Fill and optionally submit a form.
        
        Args:
            url: Form URL
            form_data: Data to fill (field_name -> value)
            field_mapping_prompt: Additional prompt for field mapping
            submit: Whether to submit the form
        """
        try:
            logger.info(f"Filling form on: {url}")
            
            # Build instruction
            data_str = "\n".join([f"- {k}: {v}" for k, v in form_data.items()])
            
            instruction = f"""
Wypełnij formularz na tej stronie następującymi danymi:
{data_str}

{field_mapping_prompt}

Dopasuj podane dane do odpowiednich pól formularza.
{"Po wypełnieniu kliknij przycisk submit/wyślij." if submit else "NIE wysyłaj formularza."}

Zwróć w formacie JSON:
{{
    "filled_fields": {{"nazwa_pola": "wpisana_wartość"}},
    "submitted": true/false,
    "confirmation": "tekst potwierdzenia lub null"
}}
"""
            
            result = await self.executor.execute_workflow(
                instruction=instruction,
                url=url,
                stealth_mode=True,
                visual_mode=False,
            )
            
            if result.get("success"):
                data = result.get("result", {})
                return FormResult(
                    url=url,
                    success=True,
                    fields_filled=data.get("filled_fields", {}) if isinstance(data, dict) else {},
                    submitted=data.get("submitted", False) if isinstance(data, dict) else False,
                )
            else:
                return FormResult(
                    url=url,
                    success=False,
                    error=result.get("error") or result.get("reason", "Unknown error"),
                )
                
        except Exception as e:
            logger.error(f"Form filling failed for {url}: {e}")
            return FormResult(
                url=url,
                success=False,
                error=str(e),
            )
    
    async def bulk_fill(
        self,
        urls: List[str],
        form_data: Dict[str, str],
        field_mapping_prompt: str = "",
        submit: bool = True
    ) -> BulkFormResult:
        """
        Fill forms on multiple URLs.
        """
        results = []
        successful = 0
        failed = 0
        
        for url in urls:
            result = await self.fill_form(url, form_data, field_mapping_prompt, submit)
            results.append(result)
            if result.success and result.submitted:
                successful += 1
            else:
                failed += 1
        
        return BulkFormResult(
            total=len(urls),
            successful=successful,
            failed=failed,
            results=results,
        )


# Global filler instance
filler = None


def get_filler() -> BulkFormFiller:
    """Get or create global filler instance"""
    global filler
    if filler is None:
        llm_provider = os.getenv("LLM_PROVIDER")
        filler = BulkFormFiller(llm_provider=llm_provider)
    return filler


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
    """Main page with form filler interface"""
    return render_template("index.html")


@app.route("/health")
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "bulk-form-filler"})


@app.route("/api/detect", methods=["POST"])
def api_detect():
    """
    Detect form fields on a URL.
    
    Request body:
    {
        "url": "form_page_url"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        url = data.get("url", "")
        
        if not url:
            return jsonify({"error": "No URL provided"}), 400
        
        f = get_filler()
        result = run_async(f.detect_fields(url))
        
        return jsonify({
            "url": result.url,
            "site_name": result.site_name,
            "success": result.success,
            "fields": result.fields_detected,
            "error": result.error,
        })
        
    except Exception as e:
        logger.error(f"Detection failed: {e}")
        return jsonify({"error": str(e), "success": False}), 500


@app.route("/api/fill", methods=["POST"])
def api_fill():
    """
    Fill a single form.
    
    Request body:
    {
        "url": "form_page_url",
        "data": {"field1": "value1", "field2": "value2"},
        "mapping_prompt": "Optional prompt for field mapping",
        "submit": true
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        url = data.get("url", "")
        form_data = data.get("data", {})
        mapping_prompt = data.get("mapping_prompt", "")
        submit = data.get("submit", True)
        
        if not url:
            return jsonify({"error": "No URL provided"}), 400
        
        if not form_data:
            return jsonify({"error": "No form data provided"}), 400
        
        f = get_filler()
        result = run_async(f.fill_form(url, form_data, mapping_prompt, submit))
        
        return jsonify({
            "url": result.url,
            "site_name": result.site_name,
            "success": result.success,
            "fields_filled": result.fields_filled,
            "submitted": result.submitted,
            "error": result.error,
        })
        
    except Exception as e:
        logger.error(f"Form filling failed: {e}")
        return jsonify({"error": str(e), "success": False}), 500


@app.route("/api/bulk/stream", methods=["POST"])
def api_bulk_stream():
    """
    Streaming API for bulk form filling with real-time logs.
    
    Request body:
    {
        "urls": ["url1", "url2", ...],
        "data": {"field1": "value1", "field2": "value2"},
        "mapping_prompt": "Optional prompt for field mapping",
        "submit": true
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        urls = data.get("urls", [])
        form_data = data.get("data", {})
        mapping_prompt = data.get("mapping_prompt", "")
        submit = data.get("submit", True)
        
        if not urls:
            return jsonify({"error": "No URLs provided"}), 400
        
        if not form_data:
            return jsonify({"error": "No form data provided"}), 400
        
        def generate():
            """Generator for SSE streaming"""
            f = get_filler()
            results = []
            processed = 0
            successful = 0
            failed = 0
            
            yield f"data: {json.dumps({'type': 'stage', 'message': f'Rozpoczynam wypełnianie {len(urls)} formularzy...'})}\n\n"
            
            for i, url in enumerate(urls):
                site_name = urlparse(url).hostname or "Unknown"
                yield f"data: {json.dumps({'type': 'log', 'level': 'info', 'message': f'[{i+1}/{len(urls)}] Wypełniam: {site_name}...'})}\n\n"
                
                try:
                    result = run_async(f.fill_form(url, form_data, mapping_prompt, submit))
                    results.append(result)
                    processed += 1
                    
                    if result.success and result.submitted:
                        successful += 1
                        yield f"data: {json.dumps({'type': 'progress', 'processed': processed, 'total': len(urls), 'site': site_name, 'success': True, 'submitted': True})}\n\n"
                    else:
                        failed += 1
                        yield f"data: {json.dumps({'type': 'progress', 'processed': processed, 'total': len(urls), 'site': site_name, 'success': result.success, 'submitted': result.submitted, 'error': result.error})}\n\n"
                    
                except Exception as e:
                    processed += 1
                    failed += 1
                    results.append(FormResult(
                        url=url,
                        success=False,
                        error=str(e),
                    ))
                    yield f"data: {json.dumps({'type': 'progress', 'processed': processed, 'total': len(urls), 'site': site_name, 'success': False, 'error': str(e)})}\n\n"
            
            # Summary
            yield f"data: {json.dumps({'type': 'log', 'level': 'success' if failed == 0 else 'warning', 'message': f'Zakończono: {successful} sukces, {failed} błędów'})}\n\n"
            
            # Final result
            final_result = {
                "success": True,
                "total": len(urls),
                "successful": successful,
                "failed": failed,
                "results": [
                    {
                        "url": r.url,
                        "site_name": r.site_name,
                        "success": r.success,
                        "fields_filled": r.fields_filled,
                        "submitted": r.submitted,
                        "error": r.error,
                        "timestamp": r.timestamp,
                    }
                    for r in results
                ],
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
        logger.error(f"Bulk form filling failed: {e}")
        return jsonify({"error": str(e), "success": False}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8081"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║           📝 Bulk Form Filler - curllm                       ║
║══════════════════════════════════════════════════════════════║
║  Web Interface: http://localhost:{port}                        ║
║  API Fill:      http://localhost:{port}/api/fill               ║
║  API Bulk:      http://localhost:{port}/api/bulk/stream        ║
║  Health Check:  http://localhost:{port}/health                 ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    app.run(host="0.0.0.0", port=port, debug=debug)
