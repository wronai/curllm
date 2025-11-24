import logging
import inspect
from typing import Any

# optional browser_use agent
try:
    from browser_use import Agent as BrowserUseAgent  # type: ignore
except Exception:
    BrowserUseAgent = None


class LocalAgent:
    def __init__(self, browser, llm: Any, max_steps: int, visual_mode: bool, task: str | None = None):
        self.browser = browser
        self.llm = llm
        self.max_steps = max_steps
        self.visual_mode = visual_mode
        self.task = task


def create_agent(browser_context, llm: Any, instruction: str, max_steps: int, visual_mode: bool):
    if BrowserUseAgent is not None:
        try:
            params = inspect.signature(BrowserUseAgent.__init__).parameters
            kwargs = {
                "browser": browser_context,
                "llm": llm,
                "max_steps": max_steps,
                "visual_mode": visual_mode,
            }
            if "task" in params:
                kwargs["task"] = instruction
            return BrowserUseAgent(**kwargs)
        except Exception as e:
            logging.getLogger(__name__).warning(
                f"browser_use.Agent init failed: {e}. Falling back to LocalAgent."
            )
    return LocalAgent(browser_context, llm, max_steps, visual_mode, task=instruction)
