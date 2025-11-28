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
