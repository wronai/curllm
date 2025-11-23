#!/usr/bin/env python3
from datetime import datetime
from pathlib import Path

class RunLogger:
    """Markdown run logger for step-by-step diagnostics"""
    def __init__(self, instruction: str, url: str | None):
        ts = datetime.now().strftime('%Y%m%d-%H%M%S')
        self.dir = Path('./logs')
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / f'run-{ts}.md'
        with open(self.path, 'w', encoding='utf-8') as f:
            f.write(f"# curllm Run Log ({ts})\n\n")
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
