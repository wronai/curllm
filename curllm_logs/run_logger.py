"""
Run Logger - Markdown run logger for step-by-step diagnostics

Provides a unified interface for logging execution runs with:
- Table of Contents generation
- Image embedding
- Form summaries
- Step-by-step logging
- Configuration logging

Migrated from curllm_core.logger for better modularity.
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


class RunLogger:
    """
    Markdown run logger for step-by-step diagnostics (with TOC and images).
    
    Usage:
        logger = RunLogger(
            instruction="Fill contact form",
            url="https://example.com/contact",
            command_line='curllm "https://example.com/contact" -d "Fill form"'
        )
        
        logger.log_heading("Step 1: Navigation")
        logger.log_text("Navigated to contact page")
        logger.log_image("screenshots/step1.png", "Contact page")
        
        logger.log_heading("Step 2: Form Fill")
        logger.log_form_summary({
            'fields': {'email': 'input[name=email]'},
            'values': {'email': 'test@example.com'},
            'validation': {'email': {'found': True, 'isEmpty': False}}
        })
    """
    
    def __init__(
        self,
        instruction: str,
        url: Optional[str],
        command_line: Optional[str] = None,
        log_dir: str = "./logs",
        session_id: Optional[str] = None
    ):
        """
        Initialize the run logger.
        
        Args:
            instruction: The instruction being executed
            url: Target URL
            command_line: Full CLI command
            log_dir: Directory for log files
            session_id: Optional session ID (auto-generated if not provided)
        """
        self.session_id = session_id or datetime.now().strftime('%Y%m%d-%H%M%S')
        self.dir = Path(log_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / f'run-{self.session_id}.md'
        
        # Internal TOC state
        self._toc_placeholder = "<!-- TOC_PLACEHOLDER -->"
        self._toc: List[tuple] = []  # (title, anchor)
        
        with open(self.path, 'w', encoding='utf-8') as f:
            f.write(f"# curllm Run Log ({self.session_id})\n\n")
            # Quick navigation (will be updated dynamically)
            f.write("## Navigation\n\n")
            f.write(self._toc_placeholder + "\n\n")
            # Command line, metadata
            if command_line:
                f.write(f"```bash\n{command_line}\n```\n\n")
            if url:
                f.write(f"- **URL**: {url}\n")
            if instruction:
                f.write(f"- **Instruction**: {instruction}\n\n")

    def _write(self, text: str):
        """Append text to log file"""
        with open(self.path, 'a', encoding='utf-8') as f:
            f.write(text)

    def log_heading(self, text: str):
        """
        Log a section heading with TOC entry.
        
        Args:
            text: Heading text
        """
        anchor = self._slugify(text)
        self._write("\n---\n\n")
        self._write(f"## {text}\n\n")
        # Update TOC
        try:
            self._toc.append((text, anchor))
            self._update_toc()
        except Exception:
            pass

    def log_text(self, text: str):
        """Log a paragraph of text"""
        self._write(f"{text}\n\n")

    def log_kv(self, key: str, value: str):
        """Log a key-value pair"""
        self._write(f"- {key}: {value}\n")

    def log_code(self, lang: str, code: str):
        """Log a code block"""
        self._write(f"```{lang}\n{code}\n```\n\n")

    def log_image(self, image_path: str, alt: str = ""):
        """
        Log an image with relative path handling.
        
        Args:
            image_path: Path to the image file
            alt: Alt text for the image
        """
        try:
            img = Path(image_path)
            # Compute path relative to the logs directory
            rel = os.path.relpath(img.resolve(), start=self.dir.resolve())
            safe_alt = alt or img.name
            self._write(f"![{safe_alt}]({rel})\n\n")
        except Exception:
            self.log_text(f"Screenshot: {image_path}")

    def log_table(self, headers: List[str], rows: List[List[str]], title: str = ""):
        """
        Log a Markdown table.
        
        Args:
            headers: List of column headers
            rows: List of rows, each row is a list of cell values
            title: Optional title above the table
        """
        if title:
            self._write(f"### {title}\n\n")
        
        if not headers or not rows:
            return
        
        # Calculate column widths for alignment
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    col_widths[i] = max(col_widths[i], len(str(cell)))
        
        # Header row
        header_line = "| " + " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers)) + " |"
        self._write(header_line + "\n")
        
        # Separator row
        sep_line = "|" + "|".join("-" * (w + 2) for w in col_widths) + "|"
        self._write(sep_line + "\n")
        
        # Data rows
        for row in rows:
            padded_row = list(row) + [""] * (len(headers) - len(row))
            row_line = "| " + " | ".join(str(c).ljust(col_widths[i]) for i, c in enumerate(padded_row[:len(headers)])) + " |"
            self._write(row_line + "\n")
        
        self._write("\n")

    def log_form_summary(self, form_data: Dict[str, Any]):
        """
        Log a formatted summary table for form filling operations.
        
        Args:
            form_data: Dictionary with form field information
                Expected keys: 'fields', 'values', 'selectors', 'validation', 'result'
        """
        fields = form_data.get('fields', {})
        values = form_data.get('values', {})
        validation = form_data.get('validation', {})
        
        if fields or values:
            headers = ["Field", "Value", "Selector", "Status"]
            rows = []
            
            all_fields = set(fields.keys()) | set(values.keys()) | set(validation.keys())
            for field in sorted(all_fields):
                value = values.get(field, "")
                selector = fields.get(field, "")
                val_info = validation.get(field, {})
                
                # Determine status
                if val_info.get('found'):
                    if val_info.get('checked') is not None:
                        status = "✅ CHECKED" if val_info.get('isChecked') else "❌ UNCHECKED"
                    elif val_info.get('isEmpty'):
                        status = "❌ EMPTY"
                    else:
                        status = "✅ FILLED"
                elif value:
                    status = "⏳ PENDING"
                else:
                    status = "⏭️ SKIPPED"
                
                # Add required marker
                if val_info.get('required'):
                    status += " [REQ]"
                
                # Truncate long values
                display_value = str(value)[:30] + ("..." if len(str(value)) > 30 else "")
                display_selector = str(selector)[:40] + ("..." if len(str(selector)) > 40 else "")
                
                rows.append([field, display_value, display_selector, status])
            
            self.log_table(headers, rows, "📝 Form Fields Summary")
        
        # Result summary
        result = form_data.get('result', {})
        if result:
            submitted = result.get('submitted', False)
            errors = result.get('errors')
            
            status_emoji = "✅" if submitted else "❌"
            status_text = "SUBMITTED" if submitted else "NOT SUBMITTED"
            
            self._write(f"**Result:** {status_emoji} {status_text}\n")
            if errors:
                self._write(f"**Errors:** {errors}\n")
            self._write("\n")

    def log_step_result(
        self,
        step_index: int,
        step_type: str,
        success: bool,
        duration_ms: int,
        details: Optional[str] = None
    ):
        """
        Log a step execution result.
        
        Args:
            step_index: Step number
            step_type: Type of step
            success: Whether step succeeded
            duration_ms: Execution time in ms
            details: Optional details/error message
        """
        status = "✅" if success else "❌"
        self._write(f"**Step {step_index + 1}:** {status} {step_type} ({duration_ms}ms)\n")
        if details:
            self._write(f"  - {details}\n")
        self._write("\n")

    def log_json(self, data: Any, title: str = "Data"):
        """Log JSON data"""
        import json
        self._write(f"### {title}\n\n")
        self._write(f"```json\n{json.dumps(data, indent=2, ensure_ascii=False)}\n```\n\n")

    def log_success(self, message: str):
        """Log a success message"""
        self._write(f"✅ **SUCCESS:** {message}\n\n")

    def log_error(self, message: str):
        """Log an error message"""
        self._write(f"❌ **ERROR:** {message}\n\n")

    def log_warning(self, message: str):
        """Log a warning message"""
        self._write(f"⚠️ **WARNING:** {message}\n\n")

    def finalize(self, success: bool, duration_ms: int = 0, error: Optional[str] = None):
        """
        Finalize the log with summary.
        
        Args:
            success: Whether execution succeeded
            duration_ms: Total execution time
            error: Error message if failed
        """
        self._write("\n---\n\n")
        self._write("## Summary\n\n")
        
        status = "✅ SUCCESS" if success else "❌ FAILED"
        self._write(f"**Status:** {status}\n")
        self._write(f"**Duration:** {duration_ms}ms\n")
        
        if error:
            self._write(f"\n**Error:** {error}\n")
        
        self._write("\n")

    # --- Helpers ---
    def _slugify(self, text: str) -> str:
        """Convert text to URL-safe slug"""
        s = text.strip().lower()
        s = re.sub(r"[^a-z0-9\s-]", "", s)
        s = re.sub(r"\s+", "-", s)
        return s

    def _update_toc(self):
        """Update table of contents in the log file"""
        try:
            with open(self.path, 'r', encoding='utf-8') as fr:
                content = fr.read()
            if self._toc:
                items = [f"- [{title}](#{self._slugify(title)})" for title, _ in self._toc]
                toc_md = "\n".join(items)
            else:
                toc_md = "(no sections yet)"
            content = content.replace(self._toc_placeholder, toc_md)
            with open(self.path, 'w', encoding='utf-8') as fw:
                fw.write(content)
        except Exception:
            pass

    @property
    def log_path(self) -> str:
        """Get the path to the log file"""
        return str(self.path)


# Convenience function
def create_run_logger(
    instruction: str,
    url: Optional[str] = None,
    command_line: Optional[str] = None,
    log_dir: str = "./logs"
) -> RunLogger:
    """Create a new run logger instance"""
    return RunLogger(
        instruction=instruction,
        url=url,
        command_line=command_line,
        log_dir=log_dir
    )
