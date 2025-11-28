#!/usr/bin/env python3
import os
from datetime import datetime
from pathlib import Path

class RunLogger:
    """Markdown run logger for step-by-step diagnostics (with TOC and images)."""
    def __init__(self, instruction: str, url: str | None, command_line: str | None = None):
        ts = datetime.now().strftime('%Y%m%d-%H%M%S')
        self.dir = Path('./logs')
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / f'run-{ts}.md'
        # Internal TOC state
        self._toc_placeholder = "<!-- TOC_PLACEHOLDER -->"
        self._toc: list[tuple[str, str]] = []  # (title, anchor)
        with open(self.path, 'w', encoding='utf-8') as f:
            f.write(f"# curllm Run Log ({ts})\n\n")
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
        with open(self.path, 'a', encoding='utf-8') as f:
            f.write(text)

    def log_heading(self, text: str):
        # Derive anchor from text (GitHub-style slug)
        anchor = self._slugify(text)
        # Append horizontal rule for readability between sections
        self._write("\n---\n\n")
        self._write(f"## {text}\n\n")
        # Update TOC
        try:
            self._toc.append((text, anchor))
            self._update_toc()
        except Exception:
            pass

    def log_text(self, text: str):
        self._write(f"{text}\n\n")

    def log_kv(self, key: str, value: str):
        self._write(f"- {key}: {value}\n")

    def log_code(self, lang: str, code: str):
        self._write(f"```{lang}\n{code}\n```\n\n")

    def log_image(self, image_path: str, alt: str = ""):
        try:
            img = Path(image_path)
            # Compute path relative to the logs directory so Markdown renders correctly
            rel = os.path.relpath(img.resolve(), start=self.dir.resolve())
            safe_alt = alt or img.name
            self._write(f"![{safe_alt}]({rel})\n\n")
        except Exception:
            # Fallback to plain text if relative resolution fails
            self.log_text(f"Screenshot: {image_path}")

    def log_table(self, headers: list[str], rows: list[list[str]], title: str = ""):
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
            # Pad row if shorter than headers
            padded_row = list(row) + [""] * (len(headers) - len(row))
            row_line = "| " + " | ".join(str(c).ljust(col_widths[i]) for i, c in enumerate(padded_row[:len(headers)])) + " |"
            self._write(row_line + "\n")
        
        self._write("\n")

    def log_form_summary(self, form_data: dict):
        """
        Log a formatted summary table for form filling operations.
        
        Args:
            form_data: Dictionary with form field information
                Expected keys: 'fields', 'values', 'selectors', 'validation', 'result'
        """
        # Form Fields Table
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

    # --- Helpers ---
    def _slugify(self, text: str) -> str:
        s = text.strip().lower()
        import re
        s = re.sub(r"[^a-z0-9\s-]", "", s)
        s = re.sub(r"\s+", "-", s)
        return s

    def _update_toc(self):
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
            # Non-fatal: skip TOC update
            pass
