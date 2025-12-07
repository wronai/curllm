"""Vision Analyzer - Visual analysis using CV and OCR"""

from typing import Dict

import cv2
import numpy as np


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
        kernel = np.ones((2, 2), np.uint8)
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
