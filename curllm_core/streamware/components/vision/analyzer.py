"""
Vision Analyzer - Image analysis using CV and LLM.
"""
from typing import Dict, Any, Optional
from pathlib import Path


class VisionAnalyzer:
    """
    Visual analysis using OpenCV and optional LLM.
    
    Features:
    - CAPTCHA pattern detection
    - Form detection
    - Distorted text detection
    """
    
    def __init__(self, llm=None):
        """
        Initialize analyzer.
        
        Args:
            llm: Optional LLM client for vision analysis
        """
        self.llm = llm
    
    async def analyze(self, image_path: str) -> Dict[str, Any]:
        """
        Analyze image for various patterns.
        
        Args:
            image_path: Path to image file
            
        Returns:
            {has_captcha, num_forms, has_images, ...}
        """
        import cv2
        import numpy as np
        
        img = cv2.imread(image_path)
        if img is None:
            return {"error": f"Could not read image: {image_path}"}
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        has_captcha = self._detect_captcha_pattern(img)
        
        return {
            "has_captcha": has_captcha,
            "num_forms": len([c for c in contours if cv2.contourArea(c) > 5000]),
            "has_images": self._has_distorted_text(gray),
            "image_size": {"width": img.shape[1], "height": img.shape[0]}
        }
    
    def _detect_captcha_pattern(self, img) -> bool:
        """Detect CAPTCHA-like patterns in image."""
        import cv2
        import numpy as np
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        kernel = np.ones((2, 2), np.uint8)
        erosion = cv2.erode(thresh, kernel, iterations=1)
        dilation = cv2.dilate(erosion, kernel, iterations=1)
        diff = cv2.absdiff(thresh, dilation)
        noise_level = int(np.sum(diff)) / (img.shape[0] * img.shape[1])
        return noise_level > 30
    
    def _has_distorted_text(self, gray_img) -> bool:
        """Detect distorted text using FFT analysis."""
        import numpy as np
        
        f_transform = np.fft.fft2(gray_img)
        f_shift = np.fft.fftshift(f_transform)
        magnitude_spectrum = abs(f_shift)
        center = (magnitude_spectrum.shape[0] // 2, magnitude_spectrum.shape[1] // 2)
        high_freq = magnitude_spectrum[center[0]-10:center[0]+10, center[1]-10:center[1]+10]
        return float(high_freq.mean()) > 100
    
    async def analyze_with_llm(
        self,
        image_path: str,
        prompt: str = None
    ) -> Dict[str, Any]:
        """
        Analyze image using vision LLM.
        
        Args:
            image_path: Path to image
            prompt: Custom prompt (optional)
            
        Returns:
            LLM analysis result
        """
        if not self.llm:
            return {"error": "No LLM configured for vision analysis"}
        
        if not prompt:
            prompt = """Analyze this image and describe:
1. What type of page is this? (form, product listing, article, etc.)
2. Are there any CAPTCHA elements visible?
3. List any form fields you can see
4. Describe the main content

Output JSON:
{"page_type": "...", "has_captcha": true/false, "form_fields": [...], "description": "..."}

JSON:"""

        try:
            if hasattr(self.llm, 'ainvoke_with_image'):
                result = await self.llm.ainvoke_with_image(prompt, image_path)
                return {"text": result.get("text", ""), "success": True}
            else:
                return {"error": "LLM does not support vision"}
        except Exception as e:
            return {"error": str(e)}
    
    async def find_element(
        self,
        image_path: str,
        description: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find element location by description using vision LLM.
        
        Args:
            image_path: Path to screenshot
            description: What to find (e.g., "submit button", "email field")
            
        Returns:
            {found: bool, location: {x, y, width, height}, confidence: float}
        """
        if not self.llm:
            return None
        
        prompt = f"""Look at this screenshot and find: "{description}"

If you find it, describe its approximate location:
- Position: top/middle/bottom of page, left/center/right
- Size: small/medium/large
- Color/appearance

Output JSON:
{{"found": true/false, "position": "description", "confidence": 0.0-1.0}}

JSON:"""

        try:
            if hasattr(self.llm, 'ainvoke_with_image'):
                result = await self.llm.ainvoke_with_image(prompt, image_path)
                import json
                import re
                text = result.get("text", "")
                match = re.search(r'\{[^}]+\}', text)
                if match:
                    return json.loads(match.group())
        except Exception:
            pass
        
        return {"found": False, "confidence": 0}


async def analyze_image(
    image_path: str,
    llm=None
) -> Dict[str, Any]:
    """
    Convenience function to analyze an image.
    
    Args:
        image_path: Path to image
        llm: Optional LLM for vision analysis
        
    Returns:
        Analysis result
    """
    analyzer = VisionAnalyzer(llm=llm)
    
    # Basic CV analysis
    result = await analyzer.analyze(image_path)
    
    # Add LLM analysis if available
    if llm:
        llm_result = await analyzer.analyze_with_llm(image_path)
        result["llm_analysis"] = llm_result
    
    return result
