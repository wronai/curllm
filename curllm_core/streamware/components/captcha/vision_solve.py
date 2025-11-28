"""
Visual CAPTCHA Solver - Uses local vision LLM to solve CAPTCHAs.

No external API required - uses Ollama with vision model (llava, minicpm-v, qwen2-vl).
"""
import os
import base64
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime


# Default vision model - can be overridden via env
VISION_MODEL = os.getenv("CURLLM_VISION_MODEL", "llava:7b")


async def solve_captcha_visual(
    page,
    captcha_info: Dict[str, Any],
    screenshot_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Solve CAPTCHA using visual LLM analysis.
    
    Supports:
    - hCaptcha / reCAPTCHA checkbox (click verification)
    - Image selection CAPTCHAs (select matching images)
    - Text CAPTCHAs (read distorted text)
    - Slider CAPTCHAs (drag to position)
    
    Args:
        page: Playwright page
        captcha_info: Info from detect_captcha()
        screenshot_path: Optional pre-taken screenshot
        
    Returns:
        {success: bool, method: str, actions_taken: [], error: str|None}
    """
    result = {
        "success": False,
        "method": "vision_llm",
        "actions_taken": [],
        "error": None,
        "model": VISION_MODEL
    }
    
    try:
        # Get or create screenshot
        if not screenshot_path:
            Path("screenshots").mkdir(exist_ok=True)
            screenshot_path = f"screenshots/captcha_solve_{datetime.now().timestamp():.0f}.png"
            await page.screenshot(path=screenshot_path)
        
        result["screenshot"] = screenshot_path
        
        captcha_type = str(captcha_info.get("type", "unknown")).lower()
        
        # Route to appropriate solver
        if "hcaptcha" in captcha_type or "recaptcha" in captcha_type:
            return await _solve_checkbox_captcha(page, screenshot_path, result)
        elif "slider" in captcha_type:
            return await _solve_slider_captcha(page, screenshot_path, captcha_info, result)
        elif "image" in captcha_type:
            return await _solve_image_captcha(page, screenshot_path, result)
        else:
            # Try generic approach
            return await _solve_generic_captcha(page, screenshot_path, result)
            
    except Exception as e:
        result["error"] = str(e)
        return result


async def _get_vision_llm():
    """Get vision-capable LLM instance."""
    from curllm_core.llm import SimpleOllama
    
    ollama_host = os.getenv("CURLLM_OLLAMA_HOST", "http://localhost:11434")
    
    return SimpleOllama(
        base_url=ollama_host,
        model=VISION_MODEL,
        num_ctx=4096,
        num_predict=512,
        temperature=0.1,
        top_p=0.9,
        timeout=60
    )


async def _solve_checkbox_captcha(
    page,
    screenshot_path: str,
    result: Dict
) -> Dict[str, Any]:
    """
    Solve checkbox-style CAPTCHA (hCaptcha, reCAPTCHA v2).
    
    Strategy:
    1. Ask vision LLM to find the checkbox location
    2. Click the checkbox
    3. If challenge appears, handle image selection
    """
    result["captcha_type"] = "checkbox"
    
    llm = await _get_vision_llm()
    
    # Ask LLM to find checkbox
    prompt = """Look at this webpage screenshot. There is a CAPTCHA checkbox widget.
Find the checkbox that needs to be clicked to verify "I'm not a robot" or similar.

Describe the EXACT location of the checkbox:
- Is it in an iframe?
- What text is near it? (e.g., "I am human", "Jestem człowiekiem", "I'm not a robot")
- Approximate position: top/middle/bottom of page? left/center/right?

Output JSON:
{"found": true/false, "checkbox_text": "text near checkbox", "position": "description", "in_iframe": true/false}

JSON:"""

    try:
        response = await llm.ainvoke_with_image(prompt, screenshot_path)
        llm_response = response.get("text", "")
        result["llm_analysis"] = llm_response[:500]
        
        # Try to click hCaptcha checkbox
        # hCaptcha checkbox is inside iframe
        iframe_selectors = [
            'iframe[src*="hcaptcha"]',
            'iframe[title*="hCaptcha"]',
            'iframe[src*="recaptcha"]',
            '.h-captcha iframe',
            '.g-recaptcha iframe'
        ]
        
        clicked = False
        for sel in iframe_selectors:
            try:
                iframe = page.frame_locator(sel)
                # Try common checkbox selectors inside iframe
                checkbox = iframe.locator('#checkbox, [role="checkbox"], .check')
                if await checkbox.count() > 0:
                    await checkbox.first.click(timeout=5000)
                    clicked = True
                    result["actions_taken"].append(f"Clicked checkbox in {sel}")
                    break
            except Exception:
                continue
        
        if not clicked:
            # Try direct click on hcaptcha div
            try:
                hcaptcha_div = page.locator('.h-captcha, [data-hcaptcha-widget-id]')
                if await hcaptcha_div.count() > 0:
                    await hcaptcha_div.first.click(timeout=5000)
                    clicked = True
                    result["actions_taken"].append("Clicked hCaptcha div directly")
            except Exception:
                pass
        
        if clicked:
            await page.wait_for_timeout(2000)  # Wait for challenge
            
            # Check if challenge appeared (image selection)
            challenge_screenshot = f"screenshots/captcha_challenge_{datetime.now().timestamp():.0f}.png"
            await page.screenshot(path=challenge_screenshot)
            
            # Check for image grid challenge
            challenge_result = await _check_for_challenge(page, challenge_screenshot, llm)
            if challenge_result.get("has_challenge"):
                result["challenge_detected"] = True
                # Handle image selection challenge
                selection_result = await _solve_image_selection(
                    page, challenge_screenshot, challenge_result, llm, result
                )
                return selection_result
            else:
                # Checkbox was enough
                result["success"] = True
                result["actions_taken"].append("Checkbox verification completed")
        else:
            result["error"] = "Could not find/click CAPTCHA checkbox"
            
    except Exception as e:
        result["error"] = f"Checkbox solve failed: {e}"
    
    return result


async def _check_for_challenge(page, screenshot_path: str, llm) -> Dict:
    """Check if a CAPTCHA challenge (image grid) appeared."""
    prompt = """Look at this screenshot. Is there a CAPTCHA challenge visible?

A CAPTCHA challenge typically shows:
- A grid of 9 or 16 images
- Instructions like "Select all images with..." or "Click on..."
- Categories like: traffic lights, crosswalks, bicycles, buses, cars, etc.

Output JSON:
{"has_challenge": true/false, "challenge_type": "image_grid/text/none", "instruction": "what to select if visible", "grid_size": "3x3 or 4x4 or none"}

JSON:"""

    try:
        response = await llm.ainvoke_with_image(prompt, screenshot_path)
        text = response.get("text", "")
        
        # Parse response
        import re
        import json
        match = re.search(r'\{[^}]+\}', text)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    
    return {"has_challenge": False}


async def _solve_image_selection(
    page,
    screenshot_path: str,
    challenge_info: Dict,
    llm,
    result: Dict
) -> Dict[str, Any]:
    """Solve image grid selection challenge using vision LLM."""
    
    instruction = challenge_info.get("instruction", "")
    grid_size = challenge_info.get("grid_size", "3x3")
    
    prompt = f"""Look at this CAPTCHA image grid challenge.

Instructions from CAPTCHA: "{instruction}"
Grid size: {grid_size}

Analyze each image in the grid. Number them 1-9 (or 1-16) from left to right, top to bottom.
Which images match the instruction "{instruction}"?

Output JSON array of image numbers to click:
{{"images_to_click": [1, 4, 7], "confidence": 0.8, "reasoning": "brief explanation"}}

JSON:"""

    try:
        response = await llm.ainvoke_with_image(prompt, screenshot_path)
        text = response.get("text", "")
        result["llm_selection_response"] = text[:500]
        
        import re
        import json
        match = re.search(r'\{[^}]+\}', text, re.DOTALL)
        if match:
            selection = json.loads(match.group())
            images_to_click = selection.get("images_to_click", [])
            
            if images_to_click:
                # Find challenge iframe and click images
                challenge_frame = page.frame_locator('iframe[src*="hcaptcha"][src*="challenge"]')
                
                for img_num in images_to_click:
                    try:
                        # hCaptcha uses data-index or nth-child
                        img_selector = f'.task-image:nth-child({img_num}), [data-index="{img_num-1}"]'
                        await challenge_frame.locator(img_selector).click(timeout=3000)
                        result["actions_taken"].append(f"Clicked image {img_num}")
                        await page.wait_for_timeout(300)
                    except Exception as e:
                        result["actions_taken"].append(f"Failed to click image {img_num}: {e}")
                
                # Click verify/submit button
                try:
                    verify_btn = challenge_frame.locator('button.verify-button, [type="submit"]')
                    await verify_btn.click(timeout=5000)
                    result["actions_taken"].append("Clicked verify button")
                    await page.wait_for_timeout(2000)
                    result["success"] = True
                except Exception as e:
                    result["error"] = f"Could not click verify: {e}"
                    
    except Exception as e:
        result["error"] = f"Image selection failed: {e}"
    
    return result


async def _solve_slider_captcha(
    page,
    screenshot_path: str,
    captcha_info: Dict,
    result: Dict
) -> Dict[str, Any]:
    """Solve slider CAPTCHA using vision LLM guidance."""
    result["captcha_type"] = "slider"
    
    llm = await _get_vision_llm()
    
    prompt = """Look at this slider CAPTCHA. 
    
There should be:
1. A puzzle piece that needs to slide into a gap
2. A track/slider at the bottom

Analyze the image and tell me:
- How far (in percentage 0-100%) should the slider move?
- Where is the gap located?

Output JSON:
{"slide_percentage": 75, "gap_position": "right side", "confidence": 0.8}

JSON:"""

    try:
        response = await llm.ainvoke_with_image(prompt, screenshot_path)
        text = response.get("text", "")
        result["llm_analysis"] = text[:500]
        
        import re
        import json
        match = re.search(r'\{[^}]+\}', text)
        if match:
            analysis = json.loads(match.group())
            slide_pct = analysis.get("slide_percentage", 50)
            
            # Find slider element
            slider_selectors = [
                '[class*="slider"] [class*="handle"]',
                '[class*="slider"] [class*="btn"]',
                '[class*="drag"]',
                '.slider-button'
            ]
            
            for sel in slider_selectors:
                try:
                    slider = page.locator(sel).first
                    if await slider.count() > 0:
                        bbox = await slider.bounding_box()
                        if bbox:
                            # Calculate slide distance
                            track_width = 300  # Approximate
                            slide_distance = int(track_width * slide_pct / 100)
                            
                            # Perform drag
                            await slider.hover()
                            await page.mouse.down()
                            await page.mouse.move(
                                bbox['x'] + slide_distance,
                                bbox['y'] + bbox['height'] / 2,
                                steps=20
                            )
                            await page.mouse.up()
                            
                            result["actions_taken"].append(f"Slid {slide_pct}% ({slide_distance}px)")
                            result["success"] = True
                            break
                except Exception as e:
                    continue
                    
    except Exception as e:
        result["error"] = f"Slider solve failed: {e}"
    
    return result


async def _solve_image_captcha(
    page,
    screenshot_path: str,
    result: Dict
) -> Dict[str, Any]:
    """Solve image/text CAPTCHA by reading distorted text."""
    result["captcha_type"] = "image_text"
    
    llm = await _get_vision_llm()
    
    prompt = """Look at this CAPTCHA image. 
Read the distorted text/numbers shown in the CAPTCHA.

The text may be:
- Warped, rotated, or have lines through it
- A mix of letters and numbers
- Case-sensitive

Output the CAPTCHA text EXACTLY as shown:
{"captcha_text": "Ab3Kx9", "confidence": 0.9}

JSON:"""

    try:
        response = await llm.ainvoke_with_image(prompt, screenshot_path)
        text = response.get("text", "")
        result["llm_analysis"] = text[:500]
        
        import re
        import json
        match = re.search(r'\{[^}]+\}', text)
        if match:
            analysis = json.loads(match.group())
            captcha_text = analysis.get("captcha_text", "")
            
            if captcha_text:
                # Find input field for CAPTCHA
                input_selectors = [
                    'input[name*="captcha"]',
                    'input[id*="captcha"]',
                    'input[placeholder*="captcha" i]',
                    '.captcha-input input'
                ]
                
                for sel in input_selectors:
                    try:
                        inp = page.locator(sel).first
                        if await inp.count() > 0:
                            await inp.fill(captcha_text)
                            result["actions_taken"].append(f"Entered: {captcha_text}")
                            result["captcha_text"] = captcha_text
                            result["success"] = True
                            break
                    except Exception:
                        continue
                        
    except Exception as e:
        result["error"] = f"Image text solve failed: {e}"
    
    return result


async def _solve_generic_captcha(
    page,
    screenshot_path: str,
    result: Dict
) -> Dict[str, Any]:
    """Generic CAPTCHA solving - ask LLM what to do."""
    result["captcha_type"] = "generic"
    
    llm = await _get_vision_llm()
    
    prompt = """Look at this webpage screenshot with a CAPTCHA.

Analyze what type of CAPTCHA this is and how to solve it:
1. Is it a checkbox to click?
2. Is it an image grid to select from?
3. Is it distorted text to read?
4. Is it a slider puzzle?

Provide step-by-step instructions to solve it:
{"captcha_type": "checkbox/image_grid/text/slider/unknown", 
 "steps": ["step 1", "step 2"],
 "elements_to_interact": ["selector or description"]}

JSON:"""

    try:
        response = await llm.ainvoke_with_image(prompt, screenshot_path)
        text = response.get("text", "")
        result["llm_analysis"] = text[:1000]
        
        # For now, just return the analysis
        result["requires_manual"] = True
        result["error"] = "Generic CAPTCHA - manual solving may be required"
        
    except Exception as e:
        result["error"] = f"Generic solve failed: {e}"
    
    return result
