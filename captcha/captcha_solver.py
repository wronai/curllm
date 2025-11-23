#!/usr/bin/env python3
"""
Advanced CAPTCHA Solver for curllm
Handles sliding puzzles, image recognition, and audio CAPTCHAs
"""

import asyncio
import base64
import io
import json
import logging
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List

import cv2
import numpy as np
from PIL import Image, ImageEnhance
from playwright.async_api import Page, Frame, ElementHandle
import requests

# For audio CAPTCHA
try:
    import speech_recognition as sr
    from pydub import AudioSegment
    AUDIO_SUPPORT = True
except ImportError:
    AUDIO_SUPPORT = False

# For advanced OCR
try:
    import pytesseract
    import easyocr
    OCR_SUPPORT = True
except ImportError:
    OCR_SUPPORT = False

# For 2captcha integration
try:
    from twocaptcha import TwoCaptcha
    TWOCAPTCHA_SUPPORT = True
except ImportError:
    TWOCAPTCHA_SUPPORT = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CaptchaType(Enum):
    """Types of CAPTCHAs we can handle"""
    SLIDING_PUZZLE = "sliding_puzzle"
    IMAGE_SELECTION = "image_selection"
    TEXT_RECOGNITION = "text_recognition"
    AUDIO = "audio"
    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    HCAPTCHA = "hcaptcha"
    FUNCAPTCHA = "funcaptcha"
    GEETEST = "geetest"


@dataclass
class CaptchaConfig:
    """Configuration for CAPTCHA solving"""
    use_2captcha: bool = False
    api_key_2captcha: str = ""
    use_local_solver: bool = True
    max_retries: int = 3
    timeout: int = 30
    screenshot_dir: Path = Path("./captcha_screenshots")
    debug_mode: bool = False


class SlidingPuzzleSolver:
    """Solver for sliding puzzle CAPTCHAs like on Allegro"""
    
    def __init__(self, config: CaptchaConfig):
        self.config = config
        self.config.screenshot_dir.mkdir(exist_ok=True)
        
    async def solve(self, page: Page, frame: Optional[Frame] = None) -> bool:
        """
        Solve sliding puzzle CAPTCHA
        Returns True if solved successfully
        """
        context = frame if frame else page
        
        try:
            # Step 1: Find the puzzle elements
            logger.info("Looking for sliding puzzle elements...")
            
            # Common selectors for sliding puzzles
            puzzle_selectors = [
                'canvas',  # Often rendered on canvas
                '[class*="slide"]',
                '[class*="puzzle"]',
                '[class*="captcha-puzzle"]',
                'div[style*="background-image"]'
            ]
            
            puzzle_element = None
            for selector in puzzle_selectors:
                try:
                    puzzle_element = await context.wait_for_selector(selector, timeout=5000)
                    if puzzle_element:
                        logger.info(f"Found puzzle element with selector: {selector}")
                        break
                except:
                    continue
                    
            if not puzzle_element:
                logger.error("Could not find puzzle element")
                return False
            
            # Step 2: Take screenshot of the puzzle
            timestamp = int(time.time())
            screenshot_path = self.config.screenshot_dir / f"puzzle_{timestamp}.png"
            await puzzle_element.screenshot(path=str(screenshot_path))
            logger.info(f"Saved puzzle screenshot: {screenshot_path}")
            
            # Step 3: Analyze the puzzle
            solution = await self.analyze_puzzle(screenshot_path)
            
            if not solution:
                logger.warning("Could not analyze puzzle locally, trying alternative methods...")
                return await self.solve_with_2captcha(context, screenshot_path)
            
            # Step 4: Execute the solution
            return await self.execute_sliding_solution(context, puzzle_element, solution)
            
        except Exception as e:
            logger.error(f"Error solving sliding puzzle: {e}")
            return False
    
    async def analyze_puzzle(self, image_path: Path) -> Optional[Dict[str, Any]]:
        """
        Analyze sliding puzzle image to find the correct position
        Uses computer vision to detect the gap and the piece
        """
        try:
            # Load image
            img = cv2.imread(str(image_path))
            if img is None:
                return None
                
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Edge detection to find the puzzle piece and gap
            edges = cv2.Canny(gray, 50, 150)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Sort contours by area to find the main elements
            contours = sorted(contours, key=cv2.contourArea, reverse=True)[:2]
            
            if len(contours) >= 2:
                # Assume first contour is background, second is the piece
                piece_contour = contours[1]
                x, y, w, h = cv2.boundingRect(piece_contour)
                
                # Use template matching to find where piece should go
                template = gray[y:y+h, x:x+w]
                result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                
                # Calculate distance to slide
                slide_distance = max_loc[0] - x
                
                logger.info(f"Detected slide distance: {slide_distance}px")
                
                return {
                    'type': 'slide',
                    'distance': slide_distance,
                    'start_x': x,
                    'start_y': y,
                    'target_x': max_loc[0],
                    'target_y': max_loc[1]
                }
                
        except Exception as e:
            logger.error(f"Error analyzing puzzle: {e}")
            
        return None
    
    async def execute_sliding_solution(
        self, 
        context: Any, 
        element: ElementHandle,
        solution: Dict[str, Any]
    ) -> bool:
        """Execute the sliding action to solve the puzzle"""
        try:
            # Get element bounding box
            box = await element.bounding_box()
            if not box:
                return False
                
            # Find the slider handle
            slider_selectors = [
                '[class*="slider"]',
                '[class*="handle"]',
                '[class*="drag"]',
                'div[draggable="true"]'
            ]
            
            slider = None
            for selector in slider_selectors:
                try:
                    slider = await context.wait_for_selector(selector, timeout=2000)
                    if slider:
                        break
                except:
                    continue
                    
            if not slider:
                logger.error("Could not find slider handle")
                return False
            
            # Get slider position
            slider_box = await slider.bounding_box()
            if not slider_box:
                return False
                
            # Calculate drag parameters
            start_x = slider_box['x'] + slider_box['width'] / 2
            start_y = slider_box['y'] + slider_box['height'] / 2
            end_x = start_x + solution['distance']
            end_y = start_y
            
            logger.info(f"Dragging from ({start_x}, {start_y}) to ({end_x}, {end_y})")
            
            # Perform the drag with human-like movement
            await self.human_like_drag(
                context,
                start_x, start_y,
                end_x, end_y
            )
            
            # Wait for verification
            await asyncio.sleep(2)
            
            # Check if solved
            error_selectors = [
                '[class*="error"]',
                '[class*="fail"]',
                'text="Spróbuj ponownie"'
            ]
            
            for selector in error_selectors:
                try:
                    error = await context.wait_for_selector(selector, timeout=1000)
                    if error:
                        logger.warning("Puzzle solution failed")
                        return False
                except:
                    pass
                    
            logger.info("Puzzle appears to be solved!")
            return True
            
        except Exception as e:
            logger.error(f"Error executing solution: {e}")
            return False
    
    async def human_like_drag(
        self,
        page: Any,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        steps: int = 20
    ):
        """
        Perform human-like drag operation with bezier curve movement
        """
        # Move to start position
        await page.mouse.move(start_x, start_y)
        await asyncio.sleep(0.1)
        
        # Press mouse button
        await page.mouse.down()
        await asyncio.sleep(0.1)
        
        # Generate bezier curve points for natural movement
        points = self.generate_bezier_points(
            start_x, start_y,
            end_x, end_y,
            steps
        )
        
        # Move along the curve
        for x, y in points:
            await page.mouse.move(x, y)
            await asyncio.sleep(0.01 + np.random.random() * 0.02)
        
        # Small overshoot and correction (human-like)
        overshoot_x = end_x + np.random.randint(-5, 5)
        await page.mouse.move(overshoot_x, end_y)
        await asyncio.sleep(0.05)
        await page.mouse.move(end_x, end_y)
        
        # Release mouse button
        await asyncio.sleep(0.1)
        await page.mouse.up()
    
    def generate_bezier_points(
        self,
        x0: float, y0: float,
        x3: float, y3: float,
        num_points: int
    ) -> List[Tuple[float, float]]:
        """Generate points along a bezier curve for natural movement"""
        # Control points for bezier curve
        x1 = x0 + (x3 - x0) * 0.3 + np.random.randint(-20, 20)
        y1 = y0 + np.random.randint(-10, 10)
        x2 = x0 + (x3 - x0) * 0.7 + np.random.randint(-20, 20)
        y2 = y3 + np.random.randint(-10, 10)
        
        points = []
        for i in range(num_points):
            t = i / (num_points - 1)
            # Bezier curve formula
            x = (1-t)**3 * x0 + 3*(1-t)**2*t * x1 + 3*(1-t)*t**2 * x2 + t**3 * x3
            y = (1-t)**3 * y0 + 3*(1-t)**2*t * y1 + 3*(1-t)*t**2 * y2 + t**3 * y3
            points.append((x, y))
            
        return points
    
    async def solve_with_2captcha(
        self,
        context: Any,
        image_path: Path
    ) -> bool:
        """Fallback to 2captcha service if local solving fails"""
        if not TWOCAPTCHA_SUPPORT or not self.config.use_2captcha:
            logger.warning("2captcha not available or not configured")
            return False
            
        try:
            solver = TwoCaptcha(self.config.api_key_2captcha)
            
            # Send image to 2captcha
            with open(image_path, 'rb') as f:
                result = solver.coordinates(
                    f.read(),
                    lang='pl',
                    hint_text='Przesuń element układanki w odpowiednie miejsce'
                )
                
            if result and 'code' in result:
                # Parse coordinates from result
                coords = result['code'].split(',')
                if len(coords) >= 2:
                    target_x = int(coords[0])
                    target_y = int(coords[1])
                    
                    # Find current position and calculate distance
                    # This would need to be adapted based on the specific CAPTCHA
                    solution = {
                        'type': 'slide',
                        'distance': target_x,
                        'target_x': target_x,
                        'target_y': target_y
                    }
                    
                    # Get the puzzle element again
                    puzzle_element = await context.wait_for_selector('canvas', timeout=5000)
                    return await self.execute_sliding_solution(context, puzzle_element, solution)
                    
        except Exception as e:
            logger.error(f"2captcha solving failed: {e}")
            
        return False


class AudioCaptchaSolver:
    """Solver for audio CAPTCHAs"""
    
    def __init__(self, config: CaptchaConfig):
        self.config = config
        self.recognizer = sr.Recognizer() if AUDIO_SUPPORT else None
        
    async def solve(self, page: Page) -> Optional[str]:
        """
        Solve audio CAPTCHA
        Returns the transcribed text or None if failed
        """
        if not AUDIO_SUPPORT:
            logger.error("Audio support not available (install speech_recognition and pydub)")
            return None
            
        try:
            # Click audio challenge button
            audio_button_selectors = [
                '[title*="audio"]',
                '[aria-label*="audio"]',
                'button:has-text("Audio")',
                '[class*="audio-button"]'
            ]
            
            for selector in audio_button_selectors:
                try:
                    button = await page.wait_for_selector(selector, timeout=2000)
                    if button:
                        await button.click()
                        await asyncio.sleep(2)
                        break
                except:
                    continue
                    
            # Find audio element
            audio_element = await page.wait_for_selector('audio', timeout=5000)
            if not audio_element:
                logger.error("No audio element found")
                return None
                
            # Get audio source
            audio_src = await audio_element.get_attribute('src')
            if not audio_src:
                logger.error("No audio source found")
                return None
                
            # Download audio file
            if audio_src.startswith('data:'):
                # Base64 encoded audio
                audio_data = base64.b64decode(audio_src.split(',')[1])
            else:
                # URL
                response = requests.get(audio_src)
                audio_data = response.content
                
            # Save audio file
            audio_path = self.config.screenshot_dir / f"captcha_audio_{int(time.time())}.mp3"
            with open(audio_path, 'wb') as f:
                f.write(audio_data)
                
            # Convert to WAV for speech recognition
            audio = AudioSegment.from_file(audio_path)
            wav_path = audio_path.with_suffix('.wav')
            audio.export(wav_path, format='wav')
            
            # Recognize speech
            with sr.AudioFile(str(wav_path)) as source:
                audio_data = self.recognizer.record(source)
                
                # Try multiple recognition engines
                text = None
                
                # Google Speech Recognition
                try:
                    text = self.recognizer.recognize_google(
                        audio_data,
                        language='pl-PL'  # Polish language
                    )
                    logger.info(f"Google recognized: {text}")
                except:
                    pass
                    
                # If Google fails, try Sphinx (offline)
                if not text:
                    try:
                        text = self.recognizer.recognize_sphinx(audio_data)
                        logger.info(f"Sphinx recognized: {text}")
                    except:
                        pass
                        
                return text
                
        except Exception as e:
            logger.error(f"Error solving audio CAPTCHA: {e}")
            return None


class CaptchaSolver:
    """Main CAPTCHA solver that orchestrates different solving methods"""
    
    def __init__(self, config: Optional[CaptchaConfig] = None):
        self.config = config or CaptchaConfig()
        self.sliding_solver = SlidingPuzzleSolver(self.config)
        self.audio_solver = AudioCaptchaSolver(self.config)
        
    async def detect_captcha_type(self, page: Page) -> Optional[CaptchaType]:
        """Detect what type of CAPTCHA is present on the page"""
        
        # Check for sliding puzzle
        sliding_indicators = [
            'text="Przesuń w prawo"',
            '[class*="slide-puzzle"]',
            'canvas[class*="captcha"]'
        ]
        
        for indicator in sliding_indicators:
            try:
                element = await page.wait_for_selector(indicator, timeout=1000)
                if element:
                    return CaptchaType.SLIDING_PUZZLE
            except:
                pass
                
        # Check for reCAPTCHA
        try:
            recaptcha = await page.wait_for_selector(
                'iframe[src*="recaptcha"]',
                timeout=1000
            )
            if recaptcha:
                return CaptchaType.RECAPTCHA_V2
        except:
            pass
            
        # Check for hCaptcha
        try:
            hcaptcha = await page.wait_for_selector(
                'iframe[src*="hcaptcha"]',
                timeout=1000
            )
            if hcaptcha:
                return CaptchaType.HCAPTCHA
        except:
            pass
            
        # Check for audio CAPTCHA
        try:
            audio = await page.wait_for_selector(
                'audio[src*="captcha"]',
                timeout=1000
            )
            if audio:
                return CaptchaType.AUDIO
        except:
            pass
            
        return None
    
    async def solve(
        self,
        page: Page,
        captcha_type: Optional[CaptchaType] = None
    ) -> bool:
        """
        Main method to solve CAPTCHA
        Auto-detects type if not specified
        """
        # Auto-detect if not specified
        if not captcha_type:
            captcha_type = await self.detect_captcha_type(page)
            
        if not captcha_type:
            logger.warning("Could not detect CAPTCHA type")
            return False
            
        logger.info(f"Detected CAPTCHA type: {captcha_type.value}")
        
        # Try to solve based on type
        for attempt in range(self.config.max_retries):
            logger.info(f"Attempt {attempt + 1}/{self.config.max_retries}")
            
            success = False
            
            if captcha_type == CaptchaType.SLIDING_PUZZLE:
                # Check if we're in an iframe
                frames = page.frames
                captcha_frame = None
                
                for frame in frames:
                    if 'captcha' in frame.url.lower():
                        captcha_frame = frame
                        break
                        
                success = await self.sliding_solver.solve(
                    page,
                    frame=captcha_frame
                )
                
            elif captcha_type == CaptchaType.AUDIO:
                solution = await self.audio_solver.solve(page)
                if solution:
                    # Find input field and enter solution
                    input_field = await page.wait_for_selector(
                        'input[type="text"]',
                        timeout=5000
                    )
                    if input_field:
                        await input_field.fill(solution)
                        # Find and click submit button
                        submit = await page.wait_for_selector(
                            'button[type="submit"]',
                            timeout=2000
                        )
                        if submit:
                            await submit.click()
                            success = True
                            
            elif captcha_type in [CaptchaType.RECAPTCHA_V2, CaptchaType.HCAPTCHA]:
                # These require 2captcha or similar service
                if self.config.use_2captcha:
                    success = await self.solve_with_service(page, captcha_type)
                else:
                    logger.warning(f"{captcha_type.value} requires 2captcha service")
                    
            if success:
                logger.info("CAPTCHA solved successfully!")
                return True
                
            # Wait before retry
            await asyncio.sleep(2)
            
        logger.error(f"Failed to solve CAPTCHA after {self.config.max_retries} attempts")
        return False
    
    async def solve_with_service(
        self,
        page: Page,
        captcha_type: CaptchaType
    ) -> bool:
        """Use 2captcha or similar service for complex CAPTCHAs"""
        if not TWOCAPTCHA_SUPPORT or not self.config.api_key_2captcha:
            return False
            
        try:
            solver = TwoCaptcha(self.config.api_key_2captcha)
            
            if captcha_type == CaptchaType.RECAPTCHA_V2:
                # Get site key
                site_key = await page.evaluate('''
                    () => {
                        const element = document.querySelector('[data-sitekey]');
                        return element ? element.getAttribute('data-sitekey') : null;
                    }
                ''')
                
                if site_key:
                    result = solver.recaptcha(
                        sitekey=site_key,
                        url=page.url
                    )
                    
                    if result and 'code' in result:
                        # Inject solution
                        await page.evaluate(f'''
                            (token) => {{
                                document.querySelector('#g-recaptcha-response').innerHTML = token;
                                if (typeof ___grecaptcha_cfg !== 'undefined') {{
                                    Object.entries(___grecaptcha_cfg.clients).forEach(([key, client]) => {{
                                        if (client.callback) {{
                                            client.callback(token);
                                        }}
                                    }});
                                }}
                            }}
                        ''', result['code'])
                        
                        return True
                        
        except Exception as e:
            logger.error(f"Service solving failed: {e}")
            
        return False


# Integration with curllm
class CurllmCaptchaExtension:
    """Extension for curllm to handle CAPTCHAs automatically"""
    
    def __init__(self, api_key_2captcha: Optional[str] = None):
        config = CaptchaConfig(
            use_2captcha=bool(api_key_2captcha),
            api_key_2captcha=api_key_2captcha or "",
            debug_mode=True
        )
        self.solver = CaptchaSolver(config)
        
    async def handle_page(self, page: Page) -> bool:
        """
        Check page for CAPTCHA and solve if found
        Returns True if CAPTCHA was solved or not present
        """
        # Check for common CAPTCHA indicators
        captcha_indicators = [
            'text="Potwierdź, że jesteś człowiekiem"',
            'text="I\'m not a robot"',
            '[class*="captcha"]',
            'iframe[src*="captcha"]',
            'text="Verify you are human"'
        ]
        
        captcha_present = False
        for indicator in captcha_indicators:
            try:
                element = await page.wait_for_selector(indicator, timeout=2000)
                if element:
                    captcha_present = True
                    break
            except:
                pass
                
        if not captcha_present:
            logger.info("No CAPTCHA detected on page")
            return True
            
        logger.info("CAPTCHA detected, attempting to solve...")
        return await self.solver.solve(page)


# Example usage
async def main():
    """Example of using the CAPTCHA solver with Playwright"""
    from playwright.async_api import async_playwright
    
    # Configure solver
    config = CaptchaConfig(
        use_2captcha=False,  # Set to True and add API key if you have 2captcha account
        api_key_2captcha="YOUR_2CAPTCHA_API_KEY",
        debug_mode=True
    )
    
    solver = CaptchaSolver(config)
    
    async with async_playwright() as p:
        # Launch browser with stealth settings
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=site-per-process',
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        
        # Remove webdriver property
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        page = await context.new_page()
        
        # Navigate to Allegro
        await page.goto('https://allegro.pl')
        
        # Wait a bit for page to load
        await asyncio.sleep(2)
        
        # Check and solve CAPTCHA if present
        solved = await solver.solve(page)
        
        if solved:
            logger.info("Successfully passed CAPTCHA!")
            # Continue with automation...
            await asyncio.sleep(5)
        else:
            logger.error("Failed to solve CAPTCHA")
            
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
