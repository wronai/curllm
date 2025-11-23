#!/usr/bin/env python3
from typing import Dict

class VisionAnalyzer:
    """Visual analysis using CV and OCR"""
    async def analyze(self, image_path: str) -> Dict:
        import cv2  # lazy import
        import numpy as np  # lazy import
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        has_captcha = self._detect_captcha_pattern(img)
        return {
            "has_captcha": has_captcha,
            "num_forms": len([c for c in contours if cv2.contourArea(c) > 5000]),
            "has_images": self._has_distorted_text(gray)
        }

    def _detect_captcha_pattern(self, img) -> bool:
        import cv2  # lazy import
        import numpy as np  # lazy import
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        kernel = np.ones((2,2), np.uint8)
        erosion = cv2.erode(thresh, kernel, iterations=1)
        dilation = cv2.dilate(erosion, kernel, iterations=1)
        diff = cv2.absdiff(thresh, dilation)
        noise_level = int(np.sum(diff)) / (img.shape[0] * img.shape[1])
        return noise_level > 30

    def _has_distorted_text(self, gray_img) -> bool:
        import numpy as np  # lazy import
        f_transform = np.fft.fft2(gray_img)
        f_shift = np.fft.fftshift(f_transform)
        magnitude_spectrum = abs(f_shift)
        center = tuple((magnitude_spectrum.shape[i] // 2 for i in (0,1)))
        high_freq = magnitude_spectrum[center[0]-10:center[0]+10, center[1]-10:center[1]+10]
        return float(high_freq.mean()) > 100
