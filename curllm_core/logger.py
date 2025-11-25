#!/usr/bin/env python3
import os
from datetime import datetime
from pathlib import Path

class RunLogger:
    """Markdown run logger for step-by-step diagnostics"""
    def __init__(self, instruction: str, url: str | None, command_line: str | None = None):
        ts = datetime.now().strftime('%Y%m%d-%H%M%S')
        self.dir = Path('./logs')
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / f'run-{ts}.md'
        with open(self.path, 'w', encoding='utf-8') as f:
            f.write(f"# curllm Run Log ({ts})\n\n")
            # Add command line at the top for easy copy-paste
            if command_line:
                f.write(f"```bash\n{command_line}\n```\n\n")
            if url:
                f.write(f"- URL: {url}\n")
            if instruction:
                f.write(f"- Instruction: {instruction}\n\n")

    def _write(self, text: str):
        with open(self.path, 'a', encoding='utf-8') as f:
            f.write(text)

    def log_heading(self, text: str):
        self._write(f"\n## {text}\n\n")

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
