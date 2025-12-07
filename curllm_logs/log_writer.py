"""
Log Writer - Write logs to various formats
"""

import os
import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
from pathlib import Path

from .log_session import LogSession
from .log_entry import LogLevel


class LogWriter(ABC):
    """Abstract base class for log writers"""
    
    @abstractmethod
    def write(self, session: LogSession, output_path: str) -> str:
        """Write session to file and return path"""
        pass


class MarkdownLogWriter(LogWriter):
    """Write logs in Markdown format"""
    
    def __init__(self, include_raw_log: bool = True, include_images: bool = True):
        self.include_raw_log = include_raw_log
        self.include_images = include_images
    
    def write(self, session: LogSession, output_path: str) -> str:
        """Write session to Markdown file"""
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            self._write_header(f, session)
            self._write_command_section(f, session)
            self._write_environment_section(f, session)
            self._write_parsed_section(f, session)
            self._write_plan_section(f, session)
            self._write_steps_table(f, session)
            self._write_domains_section(f, session)
            self._write_screenshots_section(f, session)
            self._write_result_section(f, session)
            
            if self.include_raw_log:
                self._write_raw_log(f, session)
            
            self._write_json_section(f, session)
        
        return output_path
    
    def _write_header(self, f, session: LogSession):
        """Write document header"""
        status = "✅ SUCCESS" if session.result and session.result.success else "❌ FAILED"
        duration = session.result.duration_ms if session.result else 0
        
        f.write(f"# curllm Run Log ({session.session_id})\n\n")
        f.write(f"**Type:** {session.session_type}\n")
        f.write(f"**Status:** {status}\n")
        f.write(f"**Duration:** {duration}ms\n")
        f.write(f"**Started:** {session.start_time.strftime('%Y-%m-%d %H:%M:%S') if session.start_time else 'N/A'}\n\n")
        f.write("---\n\n")
    
    def _write_command_section(self, f, session: LogSession):
        """Write command section"""
        if not session.command:
            return
        
        f.write("## Command\n\n")
        
        # CLI format
        f.write("### CLI Command\n")
        f.write(f"```bash\n{session.command.cli_format}\n```\n\n")
        
        # Traditional format if available
        if session.command.traditional_format:
            f.write("### Traditional Format\n")
            f.write(f"```bash\n{session.command.traditional_format}\n```\n\n")
        
        # URL and instruction
        if session.command.target_url:
            f.write(f"- **URL:** {session.command.target_url}\n")
        if session.command.instruction:
            f.write(f"- **Instruction:** {session.command.instruction}\n")
        f.write("\n")
    
    def _write_environment_section(self, f, session: LogSession):
        """Write environment configuration"""
        if not session.environment:
            return
        
        env = session.environment
        f.write("## Environment\n\n")
        f.write(f"- **Model:** {env.model}\n")
        f.write(f"- **Ollama Host:** {env.ollama_host}\n")
        f.write(f"- **Headless:** {env.headless}\n")
        f.write(f"- **Stealth Mode:** {env.stealth_mode}\n")
        f.write(f"- **Visual Mode:** {env.visual_mode}\n")
        if env.proxy:
            f.write(f"- **Proxy:** {env.proxy}\n")
        f.write(f"- **Locale:** {env.locale}\n")
        f.write(f"- **Timezone:** {env.timezone}\n")
        f.write(f"- **Viewport:** {env.viewport_width}x{env.viewport_height}\n")
        f.write("\n")
    
    def _write_parsed_section(self, f, session: LogSession):
        """Write parsed command info"""
        if not session.command:
            return
        
        cmd = session.command
        f.write("## Parsed\n\n")
        f.write(f"- **Domain:** {cmd.target_domain or 'N/A'}\n")
        f.write(f"- **Goal:** {cmd.goal or 'N/A'}\n")
        f.write(f"- **Confidence:** {cmd.parse_confidence:.0%}\n")
        
        # Form data
        if cmd.email or cmd.name or cmd.phone or cmd.message:
            f.write("\n### Form Data\n")
            if cmd.email:
                f.write(f"- **Email:** {cmd.email}\n")
            if cmd.name:
                f.write(f"- **Name:** {cmd.name}\n")
            if cmd.phone:
                f.write(f"- **Phone:** {cmd.phone}\n")
            if cmd.message:
                f.write(f"- **Message:** {cmd.message[:100]}{'...' if len(cmd.message or '') > 100 else ''}\n")
        f.write("\n")
    
    def _write_plan_section(self, f, session: LogSession):
        """Write execution plan"""
        if not session.plan_steps and not session.steps:
            return
        
        f.write("## Plan\n\n")
        
        # Use steps if available, otherwise plan_steps
        if session.steps:
            for step in session.steps:
                status_icon = {
                    "completed": "✅",
                    "failed": "❌",
                    "skipped": "⏭️",
                    "pending": "⏳",
                    "running": "▶️",
                }.get(step.status, "⏳")
                f.write(f"{step.index + 1}. {status_icon} {step.step_type}: {step.description}\n")
        else:
            for i, step in enumerate(session.plan_steps):
                f.write(f"{i + 1}. ⏳ {step}\n")
        f.write("\n")
    
    def _write_steps_table(self, f, session: LogSession):
        """Write steps execution table"""
        if not session.steps:
            return
        
        f.write("## Step Execution\n\n")
        f.write("| # | Step | Duration | Method | Confidence | Status |\n")
        f.write("|---|------|----------|--------|------------|--------|\n")
        
        for step in session.steps:
            status_icon = "✅" if step.status == "completed" else "❌" if step.status == "failed" else "⏳"
            method = step.method or "-"
            confidence = f"{step.selector_confidence:.0%}" if step.selector_confidence > 0 else "-"
            f.write(f"| {step.index + 1} | {step.step_type} | {step.duration_ms}ms | {method} | {confidence} | {status_icon} |\n")
        f.write("\n")
        
        # Detailed step info
        f.write("### Step Details\n\n")
        for step in session.steps:
            if step.selector_used or step.error_message:
                f.write(f"**Step {step.index + 1}: {step.step_type}**\n")
                if step.selector_used:
                    f.write(f"- Selector: `{step.selector_used}`\n")
                if step.error_message:
                    f.write(f"- Error: {step.error_message}\n")
                f.write("\n")
    
    def _write_domains_section(self, f, session: LogSession):
        """Write visited domains"""
        if not session.domains_visited and not session.urls_visited:
            return
        
        f.write("## Navigation\n\n")
        
        if session.domains_visited:
            f.write("### Domains Visited\n")
            for domain in session.domains_visited:
                f.write(f"- {domain}\n")
            f.write("\n")
        
        if session.urls_visited:
            f.write("### URLs Visited\n")
            for url in session.urls_visited:
                f.write(f"- {url}\n")
            f.write("\n")
        
        # Final URL
        if session.result and session.result.final_url:
            f.write(f"**Final URL:** `{session.result.final_url}`\n\n")
    
    def _write_screenshots_section(self, f, session: LogSession):
        """Write screenshots with images"""
        if not session.screenshots:
            return
        
        f.write("## Screenshots\n\n")
        
        for i, screenshot in enumerate(session.screenshots):
            # Handle both string paths and ScreenshotInfo objects
            if hasattr(screenshot, 'path'):
                # ScreenshotInfo object
                path = screenshot.path
                description = getattr(screenshot, 'description', f'Screenshot {i + 1}')
                step_type = getattr(screenshot, 'step_type', '')
                step_index = getattr(screenshot, 'step_index', i)
            else:
                # String path
                path = screenshot
                description = f'Screenshot {i + 1}'
                step_type = ''
                step_index = i
            
            # Make path relative to log file
            try:
                rel_path = os.path.relpath(path, session.log_dir)
            except (ValueError, TypeError):
                rel_path = path
            
            f.write(f"### {description}\n")
            if step_type:
                f.write(f"**Step {step_index}:** {step_type}\n\n")
            
            if self.include_images:
                f.write(f"![{description}]({rel_path})\n\n")
            else:
                f.write(f"- **Path:** `{path}`\n\n")
    
    def _write_result_section(self, f, session: LogSession):
        """Write execution result"""
        if not session.result:
            return
        
        result = session.result
        f.write("## Result\n\n")
        
        status = "✅ SUCCESS" if result.success else "❌ FAILED"
        f.write(f"**Status:** {status}\n")
        f.write(f"**Duration:** {result.duration_ms}ms\n")
        f.write(f"**Steps:** {result.steps_completed}/{result.steps_total} completed")
        if result.steps_failed > 0:
            f.write(f" ({result.steps_failed} failed)")
        f.write("\n\n")
        
        if result.error_message:
            f.write("### Error\n")
            f.write(f"```\n{result.error_message}\n```\n\n")
        
        if result.extracted_data:
            f.write("### Extracted Data\n")
            f.write(f"```json\n{json.dumps(result.extracted_data, indent=2, ensure_ascii=False)}\n```\n\n")
    
    def _write_raw_log(self, f, session: LogSession):
        """Write raw execution log"""
        if not session.entries:
            return
        
        f.write("## Execution Log\n\n")
        f.write("```\n")
        
        for entry in session.entries:
            f.write(entry.format() + "\n")
        
        f.write("```\n\n")
    
    def _write_json_section(self, f, session: LogSession):
        """Write full JSON representation"""
        f.write("## Full Session Data\n\n")
        f.write("<details>\n<summary>Click to expand JSON</summary>\n\n")
        f.write("```json\n")
        f.write(session.to_json())
        f.write("\n```\n\n")
        f.write("</details>\n")


class JSONLogWriter(LogWriter):
    """Write logs in JSON format"""
    
    def write(self, session: LogSession, output_path: str) -> str:
        """Write session to JSON file"""
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(session.to_json())
        
        return output_path


class HTMLLogWriter(LogWriter):
    """Write logs in HTML format with styling"""
    
    def write(self, session: LogSession, output_path: str) -> str:
        """Write session to HTML file"""
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        
        # First generate markdown
        md_writer = MarkdownLogWriter()
        md_content = []
        
        # Convert to HTML using a simple approach
        status = "SUCCESS" if session.result and session.result.success else "FAILED"
        status_color = "#22c55e" if status == "SUCCESS" else "#ef4444"
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>curllm Log - {session.session_id}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 2rem; background: #0d1117; color: #c9d1d9; }}
        h1, h2, h3 {{ color: #58a6ff; }}
        .status {{ display: inline-block; padding: 0.25rem 0.75rem; border-radius: 9999px; font-weight: bold; background: {status_color}; color: white; }}
        code {{ background: #161b22; padding: 0.2rem 0.5rem; border-radius: 4px; }}
        pre {{ background: #161b22; padding: 1rem; border-radius: 8px; overflow-x: auto; }}
        table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
        th, td {{ border: 1px solid #30363d; padding: 0.5rem 1rem; text-align: left; }}
        th {{ background: #161b22; }}
        img {{ max-width: 100%; border-radius: 8px; }}
        .step-success {{ color: #22c55e; }}
        .step-failed {{ color: #ef4444; }}
    </style>
</head>
<body>
    <h1>curllm Run Log</h1>
    <p><strong>Session:</strong> {session.session_id}</p>
    <p><strong>Status:</strong> <span class="status">{status}</span></p>
    <p><strong>Duration:</strong> {session.result.duration_ms if session.result else 0}ms</p>
    
    <h2>Command</h2>
    <pre><code>{session.command.cli_format if session.command else 'N/A'}</code></pre>
    
    <h2>Steps</h2>
    <table>
        <tr><th>#</th><th>Step</th><th>Duration</th><th>Status</th></tr>
"""
        
        for step in session.steps:
            status_class = "step-success" if step.status == "completed" else "step-failed" if step.status == "failed" else ""
            status_icon = "✅" if step.status == "completed" else "❌" if step.status == "failed" else "⏳"
            html += f'        <tr class="{status_class}"><td>{step.index + 1}</td><td>{step.step_type}</td><td>{step.duration_ms}ms</td><td>{status_icon}</td></tr>\n'
        
        html += """    </table>
</body>
</html>
"""
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        
        return output_path
