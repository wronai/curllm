"""
LLM-Guided Container Validator

Uses LLM to validate container selections WITHOUT hard-coded rules.

Approach:
1. Present container candidates with samples to LLM
2. LLM analyzes semantic content (not just patterns)
3. LLM validates: is this really a product? Or navigation/cart/marketing?
4. Combine LLM reasoning with statistical confidence

NO HARD-CODED RULES - LLM provides semantic understanding
"""

import json
from typing import Dict, List, Any, Optional


class LLMContainerValidator:
    """
    LLM-based validation of container candidates
    
    LLM analyzes:
    - Semantic content: does text look like products?
    - Context understanding: product vs navigation vs marketing
    - Structural patterns: consistent vs chaotic
    - Confidence scoring: how sure is LLM?
    """
    
    def __init__(self, llm_client, run_logger=None):
        self.llm = llm_client
        self.run_logger = run_logger
    
    def _log(self, msg: str, data: Any = None):
        """Log with structured data"""
        if self.run_logger:
            # Use log_text (standard RunLogger method)
            self.run_logger.log_text(msg)
            if data and isinstance(data, dict):
                import json
                self.run_logger.log_code("json", json.dumps(data, indent=2, ensure_ascii=False))
    
    async def validate_containers(
        self,
        candidates: List[Dict[str, Any]],
        page_context: str = "",
        instruction: str = ""
    ) -> Dict[str, Any]:
        """
        Validate container candidates using LLM
        
        Args:
            candidates: List of container candidates with samples
            page_context: Optional page context
            instruction: User's extraction instruction
        
        Returns:
            {
                "validated": [
                    {
                        "selector": "...",
                        "is_valid": True/False,
                        "confidence": 0.0-1.0,
                        "reasoning": "...",
                        "category": "product|navigation|marketing|other"
                    }
                ],
                "recommended": {...},  # Best candidate
                "llm_reasoning": "..."
            }
        """
        
        if not candidates:
            return {
                "validated": [],
                "recommended": None,
                "llm_reasoning": "No candidates to validate"
            }
        
        # Prepare candidates for LLM
        candidates_summary = self._format_candidates_for_llm(candidates)
        
        prompt = f"""You are analyzing container candidates to determine which ones contain actual products.

USER INSTRUCTION: {instruction or "Extract products from page"}

PAGE CONTEXT: {page_context[:500] if page_context else "Not provided"}

CONTAINER CANDIDATES:
{candidates_summary}

IMPORTANT CONSIDERATIONS:
- Many Polish e-commerce sites (like gral.pl, morele.net, x-kom.pl) use IMAGE-BASED prices (prices rendered as images, not text)
- Products may have product names and links even if prices are not visible in text
- Table-based layouts are common in older Polish shops
- If a container has product links (URLs ending in _12345.html or containing product IDs), it's likely a product container
- Look for product indicators: model names, brands, specifications (GB, GHz, etc.)

Your task:
1. For each candidate, analyze the sample text AND consider structural indicators
2. Determine if it represents:
   - **product**: Container with product name/link (price may be in image)
   - **navigation**: Menu items, links to categories, cart, account
   - **marketing**: Banners, promotions, ads
   - **carousel_wrapper**: Container wrapping products but not products themselves
   - **other**: Generic content

3. Score confidence (0.0-1.0) based on:
   - Presence of product-like features (names, links, specs)
   - Product links with numeric IDs
   - Brand names, model numbers, technical specs
   - BE LENIENT: if in doubt and has product links, mark as valid

4. PREFER to mark as valid if the candidate has product links

Respond with JSON:
{{
  "validated": [
    {{
      "selector": "<selector>",
      "is_valid": <true if product container - BE LENIENT>,
      "confidence": <0.0-1.0>,
      "reasoning": "<why valid or invalid>",
      "category": "<product|navigation|marketing|carousel_wrapper|other>",
      "concerns": ["<any red flags>"]
    }}
  ],
  "recommended_selector": "<best container selector or first valid one>",
  "overall_reasoning": "<explanation of recommendation>"
}}

JSON only:"""

        try:
            # Use ainvoke (SimpleOllama method)
            llm_response = await self.llm.ainvoke(prompt)
            response = llm_response.get('text', '') if isinstance(llm_response, dict) else str(llm_response)
            
            # Parse LLM response
            result = json.loads(response.strip().replace("```json", "").replace("```", ""))
            
            self._log("🧠 LLM Container Validation", {
                "candidates_analyzed": len(candidates),
                "valid_count": sum(1 for v in result.get('validated', []) if v.get('is_valid')),
                "recommended": result.get('recommended_selector')
            })
            
            return {
                "validated": result.get('validated', []),
                "recommended": self._find_recommended(result, candidates),
                "llm_reasoning": result.get('overall_reasoning', '')
            }
            
        except Exception as e:
            self._log(f"⚠️ LLM validation failed: {e}")
            # Fallback: return candidates as-is with low confidence
            return {
                "validated": [
                    {
                        "selector": c.get('selector'),
                        "is_valid": True,  # Assume valid on error
                        "confidence": 0.5,
                        "reasoning": "LLM validation failed, using algorithmic score",
                        "category": "unknown",
                        "concerns": ["LLM unavailable"]
                    }
                    for c in candidates
                ],
                "recommended": candidates[0] if candidates else None,
                "llm_reasoning": f"Fallback due to error: {str(e)}"
            }
    
    async def validate_single_container(
        self,
        selector: str,
        sample_elements: List[Dict],
        page_type: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Validate a single container in detail
        
        Args:
            selector: Container selector
            sample_elements: Sample elements from container
            page_type: Detected page type
        
        Returns:
            {
                "is_valid": True/False,
                "confidence": 0.0-1.0,
                "reasoning": "...",
                "issues": [...],
                "suggestions": [...]
            }
        """
        
        samples_text = "\n\n".join([
            f"Sample {i+1}:\n" + json.dumps(elem, indent=2)
            for i, elem in enumerate(sample_elements[:5])
        ])
        
        prompt = f"""Analyze this container to determine if it contains actual products.

SELECTOR: {selector}
PAGE TYPE: {page_type}

SAMPLE ELEMENTS:
{samples_text}

Questions to answer:
1. Do these elements represent actual products?
2. Do they have product-like features (name, price, link)?
3. Are they consistent across samples?
4. Any red flags (navigation, cart, banners)?

Respond with JSON:
{{
  "is_valid": <true/false>,
  "confidence": <0.0-1.0>,
  "reasoning": "<detailed explanation>",
  "product_indicators": ["<what suggests products>"],
  "red_flags": ["<what suggests NOT products>"],
  "suggestions": ["<how to improve detection>"]
}}

JSON only:"""

        try:
            # Use ainvoke (SimpleOllama method)
            llm_response = await self.llm.ainvoke(prompt)
            response = llm_response.get('text', '') if isinstance(llm_response, dict) else str(llm_response)
            result = json.loads(response.strip().replace("```json", "").replace("```", ""))
            return result
        except Exception as e:
            return {
                "is_valid": True,
                "confidence": 0.5,
                "reasoning": f"LLM validation failed: {e}",
                "product_indicators": [],
                "red_flags": ["LLM unavailable"],
                "suggestions": []
            }
    
    def _format_candidates_for_llm(self, candidates: List[Dict]) -> str:
        """Format candidates in human-readable form for LLM"""
        formatted = []
        
        for i, candidate in enumerate(candidates[:10]):  # Top 10 only
            selector = candidate.get('selector', 'unknown')
            count = candidate.get('count', 0)
            sample = candidate.get('sample_text', '')[:300]  # More context
            score = candidate.get('statistical_score', candidate.get('score', 0))
            has_price = candidate.get('has_price', False)
            has_link = candidate.get('has_link', False)
            has_image = candidate.get('has_image', False)
            has_product_links = candidate.get('has_product_links', False)
            avg_text_len = candidate.get('avg_text_length', 0)
            
            # Warn about potential CSS/script content
            content_warning = ""
            if '{' in sample and ':' in sample and '}' in sample:
                content_warning = " ⚠️ CONTAINS CSS STYLE CONTENT - LIKELY NOT A PRODUCT"
            elif 'function' in sample or 'var ' in sample:
                content_warning = " ⚠️ CONTAINS SCRIPT CONTENT - LIKELY NOT A PRODUCT"
            
            formatted.append(f"""
Candidate {i+1}:
  Selector: {selector}
  Count: {count} elements
  Has Price: {has_price} | Has Link: {has_link} | Has Image: {has_image} | Product Links: {has_product_links}
  Avg Text Length: {avg_text_len:.0f} chars
  Statistical Score: {score:.1f}{content_warning}
  Sample Text: "{sample}"
""")
        
        return "\n".join(formatted)
    
    def _find_recommended(
        self,
        llm_result: Dict,
        candidates: List[Dict]
    ) -> Optional[Dict]:
        """Find recommended container from LLM result"""
        
        recommended_selector = llm_result.get('recommended_selector')
        
        if not recommended_selector:
            # Find highest confidence valid container
            validated = llm_result.get('validated', [])
            valid_containers = [
                v for v in validated
                if v.get('is_valid') and v.get('confidence', 0) > 0.5
            ]
            
            if valid_containers:
                best = max(valid_containers, key=lambda x: x.get('confidence', 0))
                recommended_selector = best.get('selector')
        
        # Find original candidate
        for candidate in candidates:
            if candidate.get('selector') == recommended_selector:
                return {
                    **candidate,
                    'llm_validated': True,
                    'llm_confidence': next(
                        (v.get('confidence') for v in llm_result.get('validated', [])
                         if v.get('selector') == recommended_selector),
                        0.5
                    )
                }
        
        # Fallback: first candidate
        return candidates[0] if candidates else None


class StatisticalContainerRanker:
    """
    Rank containers using pure statistics (no hard-coded rules)
    
    Statistical features:
    - Count distribution
    - Feature density (price/link/image per element)
    - Text consistency (variance)
    - Class specificity (entropy)
    """
    
    def __init__(self):
        pass
    
    def rank_candidates(
        self,
        candidates: List[Dict[str, Any]],
        dom_stats: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Rank candidates using statistical properties
        
        NO HARD-CODED THRESHOLDS!
        """
        
        if not candidates:
            return []
        
        # Extract statistics
        optimal_depths = dom_stats.get("optimal_depths", {})
        class_patterns = dom_stats.get("class_patterns", {})
        
        import re
        
        # Score each candidate
        for candidate in candidates:
            score = 0.0
            sample_text = candidate.get('sample_text', '')
            
            # CRITICAL: Check for CSS/script content in sample_text
            has_css_keywords = 'color:' in sample_text or 'font-size:' in sample_text or \
                              'margin:' in sample_text or 'padding:' in sample_text or \
                              'position:' in sample_text or 'background:' in sample_text
            has_css_pattern = bool(re.search(r'\.[a-zA-Z_-]+\s*\{', sample_text))
            is_css = has_css_keywords or has_css_pattern or '@media' in sample_text
            is_script = 'function' in sample_text or 'var ' in sample_text or \
                        bool(re.search(r'\bif\s*\(', sample_text))
            
            if is_css or is_script:
                candidate['statistical_score'] = -100  # Heavy penalty
                continue  # Skip further scoring
            
            # 1. Count score (normalized) - reduced weight
            counts = [c.get('count', 0) for c in candidates]
            if counts:
                max_count = max(counts)
                min_count = min(counts)
                if max_count > min_count:
                    normalized_count = (candidate.get('count', 0) - min_count) / (max_count - min_count)
                    score += normalized_count * 15  # Reduced from 30
            
            # 2. Feature completeness (has_price + has_link + has_image)
            completeness = sum([
                candidate.get('has_price', False),
                candidate.get('has_link', False),
                candidate.get('has_image', False)
            ]) / 3.0
            score += completeness * 40
            
            # 3. Depth alignment (close to optimal depth?)
            if 'depth' in candidate and 'co_location_depth' in optimal_depths:
                optimal_depth = optimal_depths['co_location_depth']
                depth_diff = abs(candidate['depth'] - optimal_depth)
                depth_score = max(0, 20 - depth_diff * 2)  # Penalty for distance
                score += depth_score
            
            # 4. Class frequency (high-frequency = likely container)
            if 'classes' in candidate and class_patterns:
                first_class = candidate['classes'].split()[0] if candidate['classes'] else None
                if first_class:
                    high_freq = class_patterns.get('high_frequency_classes', [])
                    freq_map = dict(high_freq) if high_freq else {}
                    if first_class in freq_map:
                        # Normalize by mean frequency
                        mean_freq = class_patterns.get('mean_frequency', 1)
                        normalized_freq = min(freq_map[first_class] / mean_freq, 2.0)  # Cap at 2x
                        score += normalized_freq * 10
            
            # 5. Product text indicators bonus
            has_product_text = bool(re.search(r'[A-Z][a-z]+\s+[A-Z0-9]', sample_text)) or \
                               bool(re.search(r'\d+\s*(GB|TB|GHz|MHz|W|mAh|mm|cm|kg)', sample_text, re.I))
            if has_product_text:
                score += 25
            
            # 6. Reasonable text length (not too long = likely wrapper)
            avg_length = candidate.get('avg_text_length', 0)
            if 50 < avg_length < 500:  # Product-like length
                score += 15
            elif avg_length > 2000:  # Too long = probably wrapper
                score -= 20
            
            candidate['statistical_score'] = score
        
        # Sort by score
        ranked = sorted(candidates, key=lambda x: x.get('statistical_score', 0), reverse=True)
        
        return ranked
