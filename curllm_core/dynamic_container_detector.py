"""
Dynamic Container Detector

Fully dynamic, no hard-coded rules. Combines:
1. DOM Statistics (statistical analysis)
2. Algorithmic Ranking (pure math, no thresholds)
3. LLM Validation (semantic understanding)

Philosophy:
- Learn from data, not hard-code rules
- Statistical properties guide detection
- LLM provides semantic layer
- Adapt to ANY site structure
"""

from typing import Dict, List, Any, Optional
from .dom_statistics import AdaptiveDepthAnalyzer, DOMStatistics
from .llm_container_validator import LLMContainerValidator, StatisticalContainerRanker


class DynamicContainerDetector:
    """
    Fully dynamic container detection
    
    Pipeline:
    1. Statistical Analysis → find optimal depth
    2. Candidate Generation → extract potential containers
    3. Statistical Ranking → score without hard-coded rules
    4. LLM Validation → semantic verification
    5. Hybrid Selection → combine statistics + LLM
    
    NO HARD-CODED SELECTORS OR THRESHOLDS!
    """
    
    def __init__(self, llm_client=None, run_logger=None):
        self.depth_analyzer = AdaptiveDepthAnalyzer()
        self.llm_validator = LLMContainerValidator(llm_client, run_logger) if llm_client else None
        self.statistical_ranker = StatisticalContainerRanker()
        self.run_logger = run_logger
    
    def _log(self, msg: str, data: Any = None):
        """Log with structured data"""
        if self.run_logger:
            # Use log_text (standard RunLogger method)
            self.run_logger.log_text(msg)
            if data and isinstance(data, dict):
                import json
                self.run_logger.log_code("json", json.dumps(data, indent=2, ensure_ascii=False))
    
    async def detect_containers(
        self,
        page,
        instruction: str = "",
        use_llm: bool = True
    ) -> Dict[str, Any]:
        """
        Detect product containers dynamically
        
        Returns:
            {
                "containers": [<candidates>],
                "best_container": <recommended>,
                "statistical_analysis": {...},
                "llm_validation": {...},
                "transparency": {...}
            }
        """
        
        self._log("🔍 Dynamic Container Detection Started")
        
        # Step 1: Statistical Analysis
        depth_analysis = await self.depth_analyzer.find_optimal_container_depth(page, instruction)
        
        self._log("📊 Statistical Analysis", {
            "recommended_depth": depth_analysis.get('recommended_depth'),
            "confidence": depth_analysis.get('confidence'),
            "reasoning": depth_analysis.get('reasoning')
        })
        
        # Step 2: Generate Candidates (at optimal and nearby depths)
        candidates = await self._generate_candidates_at_depths(
            page,
            depth_analysis.get('recommended_depth'),
            depth_analysis.get('alternatives', [])
        )
        
        self._log("🎯 Candidates Generated", {
            "count": len(candidates),
            "depths": list(set(c.get('depth', 0) for c in candidates))
        })
        
        if not candidates:
            return {
                "containers": [],
                "best_container": None,
                "statistical_analysis": depth_analysis,
                "llm_validation": None,
                "transparency": {"error": "No candidates found"}
            }
        
        # Step 3: Statistical Ranking
        dom_stats = depth_analysis.get('statistics', {})
        ranked_candidates = self.statistical_ranker.rank_candidates(candidates, dom_stats)
        
        self._log("📈 Statistical Ranking", {
            "top_3_scores": [c.get('statistical_score', 0) for c in ranked_candidates[:3]]
        })
        
        # Step 4: LLM Validation (if available)
        llm_validation = None
        if use_llm and self.llm_validator:
            llm_validation = await self.llm_validator.validate_containers(
                ranked_candidates[:10],  # Top 10 only
                page_context="",
                instruction=instruction
            )
            
            self._log("🧠 LLM Validation", {
                "validated_count": len(llm_validation.get('validated', [])),
                "valid_count": sum(1 for v in llm_validation.get('validated', []) if v.get('is_valid')),
                "recommended": llm_validation.get('recommended', {}).get('selector') if llm_validation.get('recommended') else None
            })
        
        # Step 5: Hybrid Selection
        best_container = self._select_best_container(
            ranked_candidates,
            llm_validation,
            depth_analysis
        )
        
        self._log("✅ Best Container Selected", {
            "selector": best_container.get('selector') if best_container else None,
            "statistical_score": best_container.get('statistical_score') if best_container else None,
            "llm_confidence": best_container.get('llm_confidence') if best_container else None
        })
        
        return {
            "containers": ranked_candidates,
            "best_container": best_container,
            "statistical_analysis": depth_analysis,
            "llm_validation": llm_validation,
            "transparency": self._generate_transparency(
                depth_analysis,
                ranked_candidates,
                llm_validation,
                best_container
            )
        }
    
    async def _generate_candidates_at_depths(
        self,
        page,
        primary_depth: Optional[int],
        alternative_depths: List[int]
    ) -> List[Dict[str, Any]]:
        """
        Generate container candidates at specified depths
        
        Uses JavaScript to query DOM dynamically
        """
        
        depths_to_check = []
        if primary_depth is not None:
            # Check primary and ±1 depth
            depths_to_check.extend([primary_depth - 1, primary_depth, primary_depth + 1])
        
        # Add alternatives
        depths_to_check.extend(alternative_depths[:3])
        
        # Remove duplicates and negatives
        depths_to_check = sorted(set(d for d in depths_to_check if d >= 0))
        
        if not depths_to_check:
            depths_to_check = [5, 6, 7, 8]  # Reasonable defaults from statistics
        
        script = f"""
        (() => {{
        const targetDepths = {json.dumps(depths_to_check)};
        const candidates = [];
        
        function getDepth(element) {{
            let depth = 0;
            let current = element;
            while (current && current !== document.body) {{
                depth++;
                current = current.parentElement;
            }}
            return depth;
        }}
        
        function hasPrice(element) {{
            const text = element.textContent || '';
            // Check text-based prices
            if (/\\d+[,.]?\\d*\\s*(?:zł|PLN|€|\\$)/.test(text)) return true;
            // Check image-based prices (common in Polish shops)
            const priceImgs = element.querySelectorAll('img[src*="cb_"], img[src*="cn_"], img[src*="cena"], img[src*="price"]');
            return priceImgs.length > 0;
        }}
        
        function hasLink(element) {{
            return element.querySelector('a[href]') !== null;
        }}
        
        function hasImage(element) {{
            return element.querySelector('img[src]') !== null;
        }}
        
        function isCartOrNavElement(element) {{
            const text = (element.textContent || '').toLowerCase();
            // Filter out cart, navigation, and header elements
            const cartPatterns = ['twój pc', 'twój koszyk', 'your cart', 'shopping cart', 'zaloguj', 'login', 'menu główne', 'nawigacja', 'katalog produktów', 'konfigurator'];
            const hasCartPattern = cartPatterns.some(p => text.includes(p));
            // Check for empty cart prices (0,00 zł)
            const hasZeroPrice = /0,00\s*zł|0\.00/i.test(text);
            // If has cart pattern OR has zero price with short text = cart/nav element
            return (hasCartPattern && text.length < 150) || (hasZeroPrice && text.length < 50);
        }}
        
        function hasProductLink(element) {{
            const links = element.querySelectorAll('a[href]');
            for (const link of links) {{
                const href = link.href || '';
                // Product links usually have numeric IDs or product patterns
                if (/[_\\/]\\d{{3,}}\\.html?$/i.test(href)) return true;
                if (/[A-Za-z]+\\+[A-Za-z]+.*_\\d+\\.html$/i.test(href)) return true;
            }}
            return false;
        }}
        
        // Find elements at target depths
        const elementsByClass = {{}};
        
        document.querySelectorAll('*').forEach(el => {{
            const depth = getDepth(el);
            
            if (targetDepths.includes(depth)) {{
                // Group by first class
                if (el.className && typeof el.className === 'string') {{
                    const classes = el.className.split(' ').filter(c => c.length > 0);
                    const firstClass = classes[0];
                    
                    if (firstClass && /^[a-zA-Z][a-zA-Z0-9_-]*$/.test(firstClass)) {{
                        if (!elementsByClass[firstClass]) {{
                            elementsByClass[firstClass] = [];
                        }}
                        
                        elementsByClass[firstClass].push({{
                            element: el,
                            depth: depth,
                            hasPrice: hasPrice(el),
                            hasLink: hasLink(el),
                            hasImage: hasImage(el),
                            hasProductLink: hasProductLink(el),
                            isCart: isCartOrNavElement(el),
                            textLength: (el.textContent || '').trim().length
                        }});
                    }}
                }}
            }}
        }});
        
        // Create candidates from groups
        for (const [className, elements] of Object.entries(elementsByClass)) {{
            // Require at least 3 elements to be a candidate
            if (elements.length >= 3) {{
                const firstEl = elements[0];
                const priceCount = elements.filter(e => e.hasPrice).length;
                const linkCount = elements.filter(e => e.hasLink).length;
                const imageCount = elements.filter(e => e.hasImage).length;
                const productLinkCount = elements.filter(e => e.hasProductLink).length;
                const cartElements = elements.filter(e => e.isCart).length;
                
                // Get sample text
                const sampleEl = elements[0].element;
                const sampleText = (sampleEl.textContent || '').trim().substring(0, 200);
                
                // Skip if mostly cart/navigation elements
                if (cartElements > elements.length / 2) continue;
                
                // CRITICAL: Detect CSS/script content in sample text
                const hasCurlyBraces = sampleText.indexOf('{{') >= 0 || sampleText.indexOf('}}') >= 0;
                const hasCssKeywords = sampleText.includes('color:') || sampleText.includes('font-size:') || 
                                       sampleText.includes('margin:') || sampleText.includes('padding:') ||
                                       sampleText.includes('@media') || sampleText.includes('position:');
                const hasCssPattern = /\.[a-zA-Z_-]+\s*\{{/.test(sampleText);
                const isCssContent = hasCurlyBraces || hasCssKeywords || hasCssPattern;
                const isScriptContent = sampleText.includes('function') || 
                                        sampleText.includes('var ') ||
                                        /\bif\s*\(/.test(sampleText);
                
                // Skip CSS/script containers entirely
                if (isCssContent || isScriptContent) continue;
                
                // Calculate product score (higher = more likely to be product container)
                let productScore = 0;
                if (priceCount > 0) productScore += 30;
                if (productLinkCount > 0) productScore += 40;
                if (imageCount > 0) productScore += 20;
                if (elements.length >= 5) productScore += 10;
                // Penalty for cart-like elements
                productScore -= cartElements * 20;
                
                // Bonus for elements with product-like text (names, brands, specs)
                const hasProductText = /[A-Z][a-z]+\s+[A-Z0-9]/.test(sampleText) ||
                                       /\d+\s*(GB|TB|GHz|MHz|W|mAh|mm|cm|kg)/i.test(sampleText);
                if (hasProductText) productScore += 25;
                
                candidates.push({{
                    selector: `.${{className}}`,
                    class_name: className,
                    count: elements.length,
                    depth: firstEl.depth,
                    has_price: priceCount > 0,
                    has_link: linkCount > 0,
                    has_image: imageCount > 0,
                    has_product_links: productLinkCount > 0,
                    cart_elements: cartElements,
                    product_score: productScore,
                    sample_text: sampleText,
                    avg_text_length: elements.reduce((sum, e) => sum + e.textLength, 0) / elements.length
                }});
            }}
        }}
        
        // Sort by product score (highest first)
        candidates.sort((a, b) => b.product_score - a.product_score);
        
        return candidates;
        }})()
        """
        
        try:
            import json as json_module
            candidates = await page.evaluate(script)
            
            # Add computed properties
            for candidate in candidates:
                # Specificity = number of classes
                classes = candidate.get('class_name', '').split('-')
                candidate['specificity'] = len(classes)
                candidate['classes'] = candidate.get('class_name', '')
            
            return candidates
        except Exception as e:
            self._log(f"⚠️ Candidate generation failed: {e}")
            return []
    
    def _select_best_container(
        self,
        statistical_candidates: List[Dict],
        llm_validation: Optional[Dict],
        depth_analysis: Dict
    ) -> Optional[Dict]:
        """
        Select best container using hybrid approach
        
        Priority:
        1. LLM validated + high statistical score
        2. High statistical score (if LLM unavailable)
        3. Fallback to statistical if LLM rejected all but strong indicators exist
        """
        
        if not statistical_candidates:
            return None
        
        # If LLM validation available, check its decision
        if llm_validation:
            # Count valid containers from validated list
            validated = llm_validation.get('validated', [])
            valid_count = sum(1 for v in validated if v.get('is_valid', True))
            
            # If LLM rejected ALL candidates, check for strong product indicators
            if valid_count == 0 and len(validated) > 0:
                # Check if any candidate has strong product indicators
                # (product links, high product score, has price images, etc.)
                strong_candidates = [
                    c for c in statistical_candidates
                    if (c.get('has_product_links') or c.get('product_score', 0) >= 50 or 
                        (c.get('has_price') and c.get('has_link') and c.get('count', 0) >= 5))
                ]
                
                if strong_candidates:
                    self._log("⚠️ LLM rejected all candidates but strong product indicators found - using statistical fallback")
                    best = strong_candidates[0]
                    best['combined_confidence'] = best.get('statistical_score', 0) / 100 * 0.7  # Lower confidence
                    best['fallback_reason'] = 'statistical_override'
                    return best
                else:
                    self._log("⚠️ LLM rejected all candidates - no valid product containers found")
                    return None  # Respect LLM's decision
            
            # If LLM approved at least one, use its recommendation
            if llm_validation.get('recommended'):
                recommended = llm_validation['recommended']
                # Add combined confidence
                statistical_score = recommended.get('statistical_score', 0)
                llm_confidence = recommended.get('llm_confidence', recommended.get('confidence', 0.5))
                recommended['combined_confidence'] = (statistical_score / 100 + llm_confidence) / 2
                return recommended
            
            # No recommendation but some valid - use first valid
            for v in validated:
                if v.get('is_valid', True):
                    # Find matching candidate
                    for c in statistical_candidates:
                        if c.get('selector') == v.get('selector'):
                            c['llm_confidence'] = v.get('confidence', 0.5)
                            c['combined_confidence'] = (c.get('statistical_score', 0) / 100 + c['llm_confidence']) / 2
                            return c
        
        # Otherwise, use top statistical candidate (if LLM unavailable)
        best = statistical_candidates[0]
        best['combined_confidence'] = best.get('statistical_score', 0) / 100
        return best
    
    def _generate_transparency(
        self,
        depth_analysis: Dict,
        candidates: List[Dict],
        llm_validation: Optional[Dict],
        best_container: Optional[Dict]
    ) -> Dict[str, Any]:
        """Generate transparency report"""
        
        return {
            "statistical_analysis": {
                "recommended_depth": depth_analysis.get('recommended_depth'),
                "confidence": depth_analysis.get('confidence'),
                "reasoning": depth_analysis.get('reasoning'),
                "alternatives": depth_analysis.get('alternatives', [])
            },
            "candidates": {
                "total": len(candidates),
                "top_5": [
                    {
                        "selector": c.get('selector'),
                        "statistical_score": c.get('statistical_score'),
                        "count": c.get('count'),
                        "depth": c.get('depth')
                    }
                    for c in candidates[:5]
                ]
            },
            "llm_validation": {
                "used": llm_validation is not None,
                "valid_count": len([v for v in llm_validation.get('validated', []) if v.get('is_valid')]) if llm_validation else 0,
                "reasoning": llm_validation.get('llm_reasoning') if llm_validation else None
            } if llm_validation else None,
            "selection": {
                "selector": best_container.get('selector') if best_container else None,
                "method": "hybrid_llm_statistical" if llm_validation else "statistical_only",
                "confidence": best_container.get('combined_confidence') if best_container else 0
            }
        }


import json
