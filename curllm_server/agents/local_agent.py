"""Local Agent - Fallback agent when browser_use is unavailable"""


class LocalAgent:
    """Local browser automation agent"""
    
    def __init__(self, browser, llm, max_steps, visual_mode, task=None):
        self.browser = browser
        self.llm = llm
        self.max_steps = max_steps
        self.visual_mode = visual_mode
        self.task = task
