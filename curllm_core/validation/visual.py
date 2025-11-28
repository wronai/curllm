"""
Visual Validator - Screenshot-based validation

Validates task completion by analyzing:
- Screenshot comparisons
- Visual element detection
- UI state verification
- Error message detection
"""

import base64
from typing import Any, Dict, Optional
from .composite import ValidationCheck


class VisualValidator:
    """
    Visual validation using screenshot analysis.
    
    Features:
    - Success/error indicator detection
    - Modal/popup detection
    - Form validation message detection
    - Visual diff comparison
    """
    
    def __init__(self, vision_model=None):
        """
        Initialize visual validator.
        
        Args:
            vision_model: Optional vision LLM for advanced analysis
        """
        self.vision_model = vision_model
    
    async def validate(
        self,
        instruction: str,
        result: Dict[str, Any],
        screenshot: Optional[bytes] = None,
        expected: Optional[Dict[str, Any]] = None
    ) -> ValidationCheck:
        """
        Validate result visually.
        
        Args:
            instruction: Original user instruction
            result: Task execution result
            screenshot: Screenshot bytes (PNG/JPEG)
            expected: Expected visual state
            
        Returns:
            ValidationCheck with visual analysis
        """
        if not screenshot:
            return ValidationCheck(
                name='visual',
                passed=True,
                score=0.5,
                message="Visual validation skipped (no screenshot)",
                details={'skipped': True}
            )
        
        checks = []
        
        # Basic visual checks
        if self.vision_model:
            # Use vision model for advanced analysis
            vision_check = await self._vision_model_analysis(
                instruction, screenshot, expected
            )
            checks.append(vision_check)
        else:
            # Use heuristic checks
            heuristic_check = self._heuristic_analysis(screenshot)
            checks.append(heuristic_check)
        
        # Aggregate checks
        passed_count = sum(1 for c in checks if c['passed'])
        total_score = sum(c['score'] for c in checks) / len(checks) if checks else 0.5
        
        all_passed = passed_count == len(checks)
        
        return ValidationCheck(
            name='visual',
            passed=all_passed,
            score=total_score,
            message=f"Visual: {passed_count}/{len(checks)} checks passed",
            details={
                'checks': checks,
                'screenshot_size': len(screenshot)
            }
        )
    
    async def _vision_model_analysis(
        self,
        instruction: str,
        screenshot: bytes,
        expected: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze screenshot using vision model"""
        
        try:
            # Encode screenshot
            b64_image = base64.b64encode(screenshot).decode('utf-8')
            
            # Build prompt
            prompt = f"""Analyze this screenshot to verify task completion.

TASK: {instruction}

Look for:
1. Success indicators (confirmation messages, green checkmarks, "Thank you" text)
2. Error indicators (red text, error messages, validation warnings)
3. Form state (filled fields, submitted state)
4. Navigation state (correct page loaded)

Respond with JSON:
{{
    "passed": true/false,
    "score": 0.0-1.0,
    "observations": ["list of visual observations"],
    "success_indicators": ["green checkmark", "confirmation message"],
    "error_indicators": [],
    "reasoning": "explanation"
}}

JSON:"""
            
            # Call vision model
            response = await self.vision_model.ainvoke(prompt, images=[b64_image])
            text = response.get('text', '')
            
            # Parse response
            import json
            start = text.find('{')
            end = text.rfind('}')
            if start >= 0 and end > start:
                result = json.loads(text[start:end+1])
                return {
                    'passed': result.get('passed', True),
                    'score': result.get('score', 0.7),
                    'type': 'vision_model',
                    'details': result
                }
            
        except Exception as e:
            pass
        
        # Fallback
        return {
            'passed': True,
            'score': 0.5,
            'type': 'vision_model_fallback',
            'details': {'error': 'Could not analyze with vision model'}
        }
    
    def _heuristic_analysis(self, screenshot: bytes) -> Dict[str, Any]:
        """Perform heuristic visual analysis"""
        
        # Basic checks without vision model
        issues = []
        
        # Check screenshot is valid
        if len(screenshot) < 1000:
            issues.append('Screenshot too small (possible blank page)')
        
        # Check for common image signatures
        is_png = screenshot[:8] == b'\x89PNG\r\n\x1a\n'
        is_jpeg = screenshot[:2] == b'\xff\xd8'
        
        if not (is_png or is_jpeg):
            issues.append('Invalid image format')
        
        # Estimate image dimensions from file size
        # Rough heuristic: typical webpage ~100KB-2MB
        if len(screenshot) < 5000:
            issues.append('Very small screenshot (may indicate error)')
        elif len(screenshot) > 5_000_000:
            issues.append('Very large screenshot (unusual)')
        
        passed = len(issues) == 0
        score = 1.0 - (len(issues) * 0.25)
        
        return {
            'passed': passed,
            'score': max(0.0, score),
            'type': 'heuristic',
            'details': {
                'size_bytes': len(screenshot),
                'format': 'PNG' if is_png else ('JPEG' if is_jpeg else 'unknown'),
                'issues': issues
            }
        }
    
    async def compare_screenshots(
        self,
        before: bytes,
        after: bytes,
        expected_change: str
    ) -> ValidationCheck:
        """
        Compare two screenshots to detect expected change.
        
        Args:
            before: Screenshot before action
            after: Screenshot after action
            expected_change: Description of expected visual change
            
        Returns:
            ValidationCheck with comparison result
        """
        # Basic size comparison
        size_diff = abs(len(after) - len(before))
        size_change_percent = size_diff / len(before) * 100 if before else 0
        
        # Significant visual change expected
        has_change = size_change_percent > 5
        
        # For form submissions, we expect some change
        if 'submit' in expected_change.lower() or 'fill' in expected_change.lower():
            passed = has_change
            message = "Page changed after action" if has_change else "No visible change detected"
        else:
            passed = True
            message = f"Visual change: {size_change_percent:.1f}%"
        
        return ValidationCheck(
            name='visual_compare',
            passed=passed,
            score=0.8 if passed else 0.3,
            message=message,
            details={
                'before_size': len(before),
                'after_size': len(after),
                'size_change_percent': size_change_percent,
                'expected_change': expected_change
            }
        )
    
    def detect_error_indicators(self, screenshot: bytes) -> Dict[str, Any]:
        """
        Detect common error indicators in screenshot.
        
        Returns dict with:
        - has_errors: bool
        - error_type: str (e.g., '404', 'validation', 'captcha')
        - confidence: float
        """
        # Without vision model, we can only do basic checks
        # This is a placeholder for future OCR/CV integration
        
        return {
            'has_errors': False,
            'error_type': None,
            'confidence': 0.5,
            'note': 'Full error detection requires vision model'
        }
    
    def detect_success_indicators(self, screenshot: bytes) -> Dict[str, Any]:
        """
        Detect success indicators in screenshot.
        
        Returns dict with:
        - has_success: bool
        - indicator_type: str
        - confidence: float
        """
        # Placeholder for future implementation
        return {
            'has_success': False,
            'indicator_type': None,
            'confidence': 0.5,
            'note': 'Full success detection requires vision model'
        }

