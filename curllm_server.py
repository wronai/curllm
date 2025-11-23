#!/usr/bin/env python3
"""
curllm_server.py - API Server for Browser Automation with Local LLM
Supports visual analysis, CAPTCHA solving, and stealth mode
"""

import asyncio
import base64
import json
import logging
import os
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from flask import Flask, request, jsonify
from flask_cors import CORS
import aiohttp

# Browser automation imports
from browser_use import Agent, Browser
from browser_use.browser.context import BrowserContext
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from playwright.async_api import async_playwright
from PIL import Image
import cv2
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# ============================================================================
# Configuration
# ============================================================================

@dataclass
class Config:
    """Application configuration"""
    ollama_host: str = os.getenv("CURLLM_OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = os.getenv("CURLLM_MODEL", "qwen2.5:7b")
    browserless_url: str = os.getenv("BROWSERLESS_URL", "ws://localhost:3000")
    use_browserless: bool = os.getenv("CURLLM_BROWSERLESS", "false").lower() == "true"
    max_steps: int = 20
    screenshot_dir: Path = Path("/tmp/curllm_screenshots")
    enable_debug: bool = os.getenv("CURLLM_DEBUG", "false").lower() == "true"
    
    def __post_init__(self):
        self.screenshot_dir.mkdir(exist_ok=True)

config = Config()

# ============================================================================
# Core Execution Engine
# ============================================================================

class CurllmExecutor:
    """Main browser automation executor with LLM support"""
    
    def __init__(self):
        self.llm = self._setup_llm()
        self.vision_analyzer = VisionAnalyzer()
        self.captcha_solver = CaptchaSolver()
        self.stealth_config = StealthConfig()
        
    def _setup_llm(self) -> OllamaLLM:
        """Initialize Ollama LLM"""
        return OllamaLLM(
            base_url=config.ollama_host,
            model=config.ollama_model,
            temperature=0.3,
            top_p=0.9,
            num_predict=512,
            num_ctx=8192
        )
    
    async def execute_workflow(
        self,
        instruction: str,
        url: Optional[str] = None,
        visual_mode: bool = False,
        stealth_mode: bool = False,
        captcha_solver: bool = False,
        use_bql: bool = False,
        headers: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Execute browser automation workflow"""
        
        try:
            # Parse instruction if BQL mode
            if use_bql:
                instruction = self._parse_bql(instruction)
            
            # Setup browser context
            browser_context = await self._setup_browser(stealth_mode)
            
            # Create agent
            agent = Agent(
                browser=browser_context,
                llm=self.llm,
                max_steps=config.max_steps,
                visual_mode=visual_mode
            )
            
            # Execute main task
            result = await self._execute_task(
                agent=agent,
                instruction=instruction,
                url=url,
                visual_mode=visual_mode,
                captcha_solver=captcha_solver
            )
            
            # Cleanup
            await browser_context.close()
            
            return {
                "success": True,
                "result": result.get("data"),
                "steps_taken": result.get("steps", 0),
                "screenshots": result.get("screenshots", []),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _setup_browser(self, stealth_mode: bool):
        """Setup browser with optional stealth mode"""
        if config.use_browserless:
            return await self._setup_browserless()
        else:
            return await self._setup_playwright(stealth_mode)
    
    async def _setup_playwright(self, stealth_mode: bool):
        """Setup Playwright browser"""
        playwright = await async_playwright().start()
        
        launch_args = {
            "headless": True,
            "args": ["--no-sandbox", "--disable-dev-shm-usage"]
        }
        
        if stealth_mode:
            launch_args["args"].extend(self.stealth_config.get_chrome_args())
        
        browser = await playwright.chromium.launch(**launch_args)
        
        context_args = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": self.stealth_config.get_user_agent() if stealth_mode else None
        }
        
        context = await browser.new_context(**context_args)
        
        if stealth_mode:
            await self.stealth_config.apply_to_context(context)
        
        return context
    
    async def _setup_browserless(self):
        """Setup Browserless browser connection"""
        # Connect to Browserless WebSocket endpoint
        import websockets
        ws = await websockets.connect(config.browserless_url)
        # Return wrapped context (simplified for example)
        return BrowserlessContext(ws)
    
    async def _execute_task(
        self,
        agent,
        instruction: str,
        url: Optional[str],
        visual_mode: bool,
        captcha_solver: bool
    ) -> Dict:
        """Execute the main browser task"""
        
        result = {
            "data": None,
            "steps": 0,
            "screenshots": []
        }
        
        # Navigate to URL if provided
        if url:
            page = await agent.browser.new_page()
            await page.goto(url)
        else:
            page = await agent.browser.new_page()
        
        # Main execution loop
        for step in range(config.max_steps):
            result["steps"] = step + 1
            
            # Take screenshot if visual mode
            if visual_mode:
                screenshot_path = await self._take_screenshot(page, step)
                result["screenshots"].append(screenshot_path)
                
                # Analyze visual state
                visual_analysis = await self.vision_analyzer.analyze(screenshot_path)
                
                # Check for CAPTCHA
                if captcha_solver and visual_analysis.get("has_captcha"):
                    await self._handle_captcha(page, screenshot_path)
            
            # Get page context
            page_context = await self._extract_page_context(page)
            
            # Generate next action using LLM
            action = await self._generate_action(
                instruction=instruction,
                page_context=page_context,
                step=step
            )
            
            # Execute action
            if action["type"] == "complete":
                result["data"] = action.get("extracted_data", page_context)
                break
            
            await self._execute_action(page, action)
            
            # Check for honeypots
            if await self._detect_honeypot(page):
                logger.warning("Honeypot detected, skipping field")
        
        await page.close()
        return result
    
    async def _take_screenshot(self, page, step: int) -> str:
        """Take and save screenshot"""
        filename = config.screenshot_dir / f"step_{step}_{datetime.now().timestamp()}.png"
        await page.screenshot(path=str(filename))
        return str(filename)
    
    async def _extract_page_context(self, page) -> Dict:
        """Extract page context for LLM"""
        return await page.evaluate("""
            () => {
                return {
                    title: document.title,
                    url: window.location.href,
                    text: document.body.innerText.substring(0, 5000),
                    forms: Array.from(document.forms).map(f => ({
                        id: f.id,
                        action: f.action,
                        fields: Array.from(f.elements).map(e => ({
                            name: e.name,
                            type: e.type,
                            value: e.value,
                            visible: e.offsetParent !== null
                        }))
                    })),
                    links: Array.from(document.links).slice(0, 50).map(l => ({
                        href: l.href,
                        text: l.innerText
                    })),
                    buttons: Array.from(document.querySelectorAll('button')).map(b => ({
                        text: b.innerText,
                        onclick: b.onclick ? 'has handler' : null
                    }))
                };
            }
        """)
    
    async def _generate_action(self, instruction: str, page_context: Dict, step: int) -> Dict:
        """Generate next action using LLM"""
        
        prompt = PromptTemplate(
            input_variables=["instruction", "context", "step"],
            template="""You are a browser automation expert. Analyze the current page and determine the next action.

Instruction: {instruction}
Current Step: {step}
Page Context: {context}

Generate a JSON action:
{{
    "type": "click|fill|scroll|wait|complete",
    "selector": "CSS selector if applicable",
    "value": "value to fill if applicable",
    "extracted_data": "data if task is complete"
}}

Response (JSON only):"""
        )
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        
        response = await chain.ainvoke({
            "instruction": instruction,
            "context": json.dumps(page_context, indent=2)[:3000],
            "step": step
        })
        
        try:
            return json.loads(response["text"])
        except json.JSONDecodeError:
            # Fallback parsing
            return {"type": "wait"}
    
    async def _execute_action(self, page, action: Dict):
        """Execute browser action"""
        action_type = action.get("type")
        
        if action_type == "click":
            await page.click(action["selector"])
        elif action_type == "fill":
            await page.fill(action["selector"], action["value"])
        elif action_type == "scroll":
            await page.evaluate("window.scrollBy(0, 500)")
        elif action_type == "wait":
            await page.wait_for_timeout(1000)
    
    async def _detect_honeypot(self, page) -> bool:
        """Detect honeypot fields"""
        honeypots = await page.evaluate("""
            () => {
                const suspicious = [];
                const inputs = document.querySelectorAll('input, textarea');
                
                inputs.forEach(input => {
                    // Check if hidden
                    const style = window.getComputedStyle(input);
                    if (style.display === 'none' || 
                        style.visibility === 'hidden' ||
                        input.type === 'hidden' ||
                        style.opacity === '0' ||
                        input.offsetHeight === 0) {
                        suspicious.push(input.name || input.id);
                    }
                });
                
                return suspicious.length > 0;
            }
        """)
        return honeypots
    
    async def _handle_captcha(self, page, screenshot_path: str):
        """Handle CAPTCHA solving"""
        solution = await self.captcha_solver.solve(screenshot_path)
        if solution:
            # Find CAPTCHA input field
            await page.fill('input[name*="captcha"]', solution)
    
    def _parse_bql(self, query: str) -> str:
        """Parse BQL query to instruction"""
        # Simplified BQL parser
        if "query" in query and "{" in query:
            # Extract fields from BQL
            return f"Extract the following fields from the page: {query}"
        return query

# ============================================================================
# Vision Analysis
# ============================================================================

class VisionAnalyzer:
    """Visual analysis using CV and OCR"""
    
    async def analyze(self, image_path: str) -> Dict:
        """Analyze screenshot for elements"""
        img = cv2.imread(image_path)
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Detect buttons/forms using edge detection
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Check for CAPTCHA patterns
        has_captcha = self._detect_captcha_pattern(img)
        
        return {
            "has_captcha": has_captcha,
            "num_forms": len([c for c in contours if cv2.contourArea(c) > 5000]),
            "has_images": self._has_distorted_text(gray)
        }
    
    def _detect_captcha_pattern(self, img) -> bool:
        """Detect common CAPTCHA patterns"""
        # Look for distorted text patterns
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        
        # Check for noise patterns common in CAPTCHAs
        kernel = np.ones((2,2), np.uint8)
        erosion = cv2.erode(thresh, kernel, iterations=1)
        dilation = cv2.dilate(erosion, kernel, iterations=1)
        
        diff = cv2.absdiff(thresh, dilation)
        noise_level = np.sum(diff) / (img.shape[0] * img.shape[1])
        
        return noise_level > 30  # Threshold for CAPTCHA detection
    
    def _has_distorted_text(self, gray_img) -> bool:
        """Check for distorted text patterns"""
        # Apply FFT to detect periodic noise
        f_transform = np.fft.fft2(gray_img)
        f_shift = np.fft.fftshift(f_transform)
        magnitude_spectrum = np.abs(f_shift)
        
        # Check for high frequency components (noise)
        center = tuple(np.array(magnitude_spectrum.shape) // 2)
        high_freq = magnitude_spectrum[center[0]-10:center[0]+10, center[1]-10:center[1]+10]
        
        return np.mean(high_freq) > 100

# ============================================================================
# CAPTCHA Solver
# ============================================================================

class CaptchaSolver:
    """CAPTCHA solving integration"""
    
    def __init__(self):
        self.use_2captcha = os.getenv("CAPTCHA_API_KEY") is not None
        self.api_key = os.getenv("CAPTCHA_API_KEY", "")
    
    async def solve(self, image_path: str) -> Optional[str]:
        """Solve CAPTCHA from image"""
        if not self.use_2captcha:
            # Try local OCR first
            return await self._solve_local(image_path)
        
        # Use 2captcha service
        return await self._solve_2captcha(image_path)
    
    async def _solve_local(self, image_path: str) -> Optional[str]:
        """Local CAPTCHA solving using OCR"""
        try:
            import pytesseract
            
            # Preprocess image
            img = Image.open(image_path)
            img = img.convert('L')  # Grayscale
            
            # Apply filters to improve OCR
            img = img.point(lambda p: p > 128 and 255)
            
            # OCR
            text = pytesseract.image_to_string(img, config='--psm 8')
            return text.strip()
        except:
            return None
    
    async def _solve_2captcha(self, image_path: str) -> Optional[str]:
        """Solve using 2captcha API"""
        async with aiohttp.ClientSession() as session:
            # Upload image
            with open(image_path, 'rb') as f:
                data = {
                    'key': self.api_key,
                    'method': 'post'
                }
                files = {'file': f}
                
                async with session.post(
                    'http://2captcha.com/in.php',
                    data=data,
                    files=files
                ) as resp:
                    result = await resp.text()
                    if 'OK' in result:
                        captcha_id = result.split('|')[1]
                        
                        # Poll for result
                        await asyncio.sleep(20)
                        
                        async with session.get(
                            f'http://2captcha.com/res.php?key={self.api_key}&action=get&id={captcha_id}'
                        ) as resp2:
                            result = await resp2.text()
                            if 'OK' in result:
                                return result.split('|')[1]
        return None

# ============================================================================
# Stealth Configuration
# ============================================================================

class StealthConfig:
    """Anti-detection configuration"""
    
    def get_chrome_args(self) -> List[str]:
        """Get stealth Chrome arguments"""
        return [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-setuid-sandbox',
            '--no-first-run',
            '--no-default-browser-check',
            '--window-size=1920,1080',
            '--start-maximized',
            '--user-agent=' + self.get_user_agent()
        ]
    
    def get_user_agent(self) -> str:
        """Get realistic user agent"""
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    
    async def apply_to_context(self, context):
        """Apply stealth patches to browser context"""
        await context.add_init_script("""
            // Remove webdriver flag
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            
            // Override chrome detection
            window.chrome = {
                runtime: {}
            };
            
            // Mock permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)

# ============================================================================
# BrowserlessContext Wrapper
# ============================================================================

class BrowserlessContext:
    """Wrapper for Browserless WebSocket connection"""
    
    def __init__(self, websocket):
        self.ws = websocket
    
    async def new_page(self):
        """Create new page via Browserless"""
        # Send BQL query to create page
        await self.ws.send(json.dumps({
            "type": "newPage",
            "stealth": True
        }))
        # Return page wrapper
        return BrowserlessPage(self.ws)
    
    async def close(self):
        """Close connection"""
        await self.ws.close()

class BrowserlessPage:
    """Browserless page wrapper"""
    
    def __init__(self, websocket):
        self.ws = websocket
    
    async def goto(self, url: str):
        """Navigate to URL"""
        await self.ws.send(json.dumps({
            "type": "goto",
            "url": url
        }))
    
    async def click(self, selector: str):
        """Click element"""
        await self.ws.send(json.dumps({
            "type": "click",
            "selector": selector
        }))
    
    async def fill(self, selector: str, value: str):
        """Fill input field"""
        await self.ws.send(json.dumps({
            "type": "fill",
            "selector": selector,
            "value": value
        }))
    
    async def screenshot(self, path: str):
        """Take screenshot"""
        await self.ws.send(json.dumps({
            "type": "screenshot"
        }))
        # Wait for base64 response
        response = await self.ws.recv()
        data = json.loads(response)
        
        # Save to file
        with open(path, 'wb') as f:
            f.write(base64.b64decode(data['screenshot']))
    
    async def evaluate(self, script: str):
        """Execute JavaScript"""
        await self.ws.send(json.dumps({
            "type": "evaluate",
            "script": script
        }))
        response = await self.ws.recv()
        return json.loads(response).get('result')
    
    async def close(self):
        """Close page"""
        await self.ws.send(json.dumps({
            "type": "closePage"
        }))

# ============================================================================
# Flask API Endpoints
# ============================================================================

executor = CurllmExecutor()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "model": config.ollama_model,
        "ollama_host": config.ollama_host,
        "version": "1.0.0"
    })

@app.route('/api/execute', methods=['POST'])
def execute():
    """Main execution endpoint"""
    data = request.get_json()
    
    # Extract parameters
    instruction = data.get('data', '')
    url = data.get('url')
    visual_mode = data.get('visual_mode', False)
    stealth_mode = data.get('stealth_mode', False)
    captcha_solver = data.get('captcha_solver', False)
    use_bql = data.get('use_bql', False)
    headers = data.get('headers', {})
    
    # Run async task
    result = asyncio.run(
        executor.execute_workflow(
            instruction=instruction,
            url=url,
            visual_mode=visual_mode,
            stealth_mode=stealth_mode,
            captcha_solver=captcha_solver,
            use_bql=use_bql,
            headers=headers
        )
    )
    
    return jsonify(result)

@app.route('/api/models', methods=['GET'])
def list_models():
    """List available Ollama models"""
    try:
        import requests
        response = requests.get(f"{config.ollama_host}/api/tags")
        return jsonify(response.json())
    except:
        return jsonify({"error": "Failed to fetch models"}), 500

@app.route('/api/screenshot/<path:filename>', methods=['GET'])
def get_screenshot(filename):
    """Serve screenshot files"""
    from flask import send_file
    filepath = config.screenshot_dir / filename
    if filepath.exists():
        return send_file(str(filepath), mimetype='image/png')
    return jsonify({"error": "Screenshot not found"}), 404

# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == '__main__':
    # Check if Ollama is running
    import requests
    try:
        response = requests.get(f"{config.ollama_host}/api/tags")
        logger.info(f"✓ Connected to Ollama at {config.ollama_host}")
    except:
        logger.error(f"✗ Cannot connect to Ollama at {config.ollama_host}")
        logger.error("  Please start Ollama: ollama serve")
        sys.exit(1)
    
    # Start Flask server
    logger.info(f"Starting curllm API server on port 8000...")
    logger.info(f"Model: {config.ollama_model}")
    logger.info(f"Visual mode: Available")
    logger.info(f"Stealth mode: Available")
    logger.info(f"CAPTCHA solver: {'Enabled' if os.getenv('CAPTCHA_API_KEY') else 'Local OCR only'}")
    
    app.run(
        host='0.0.0.0',
        port=8000,
        debug=config.enable_debug
    )
