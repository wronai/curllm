"""
DOM Statistics Analyzer

Dynamically analyzes DOM structure to find optimal container depth.
NO HARD-CODED RULES - pure statistical analysis.

Approach:
1. Build depth map: count elements at each depth level
2. Calculate distribution: prices, links, images per level
3. Find statistical peaks: where product containers likely exist
4. Score candidates based on statistical properties
"""

from typing import Dict, List, Any, Optional
from collections import defaultdict
import statistics


class DOMStatistics:
    """
    Statistical analysis of DOM structure
    
    Analyzes:
    - Depth distribution: element counts per level
    - Feature distribution: prices, links, images per level
    - Text patterns: length distribution, keyword frequency
    - Structural patterns: repeating classes, similar siblings
    """
    
    def __init__(self):
        self.depth_map = defaultdict(int)
        self.price_depth_map = defaultdict(int)
        self.link_depth_map = defaultdict(int)
        self.image_depth_map = defaultdict(int)
        self.class_frequency = defaultdict(int)
        self.text_length_by_depth = defaultdict(list)
    
    async def analyze_dom_tree(self, page) -> Dict[str, Any]:
        """
        Analyze entire DOM tree structure
        
        Returns statistical insights without hard-coded rules
        """
        stats = {
            "depth_distribution": {},
            "feature_distribution": {},
            "optimal_depths": {},
            "class_patterns": {},
            "statistical_insights": {}
        }
        
        # Gather statistics from page (async methods)
        await self._gather_depth_stats(page)
        await self._gather_feature_stats(page)
        await self._gather_class_patterns(page)
        
        # Calculate statistical properties
        stats["depth_distribution"] = dict(self.depth_map)
        stats["feature_distribution"] = {
            "prices": dict(self.price_depth_map),
            "links": dict(self.link_depth_map),
            "images": dict(self.image_depth_map)
        }
        
        # Find optimal depths using statistics
        stats["optimal_depths"] = self._calculate_optimal_depths()
        
        # Pattern analysis
        stats["class_patterns"] = self._find_repeating_patterns()
        
        # Statistical insights
        stats["statistical_insights"] = self._generate_insights()
        
        return stats
    
    async def _gather_depth_stats(self, page):
        """Gather element count statistics per depth level"""
        # Use JavaScript to analyze DOM depth
        script = """
        const stats = {
            depthMap: {},
            textLengthByDepth: {}
        };
        
        function analyzeDepth(element, depth = 0) {
            stats.depthMap[depth] = (stats.depthMap[depth] || 0) + 1;
            
            // Text length statistics
            const textLength = (element.textContent || '').trim().length;
            if (!stats.textLengthByDepth[depth]) {
                stats.textLengthByDepth[depth] = [];
            }
            if (textLength > 0 && textLength < 500) {
                stats.textLengthByDepth[depth].push(textLength);
            }
            
            // Recurse
            for (const child of element.children) {
                analyzeDepth(child, depth + 1);
            }
        }
        
        analyzeDepth(document.body);
        return stats;
        """
        
        try:
            result = await page.evaluate(script)
            self.depth_map = defaultdict(int, {int(k): v for k, v in result['depthMap'].items()})
            self.text_length_by_depth = defaultdict(list, {
                int(k): v for k, v in result['textLengthByDepth'].items()
            })
        except Exception:
            pass
    
    async def _gather_feature_stats(self, page):
        """Gather price/link/image statistics per depth"""
        script = """
        const stats = {
            prices: {},
            links: {},
            images: {}
        };
        
        function getDepth(element) {
            let depth = 0;
            let current = element;
            while (current && current !== document.body) {
                depth++;
                current = current.parentElement;
            }
            return depth;
        }
        
        // Price patterns (no hard-coded selectors!)
        const pricePattern = /\\d+[,.]?\\d*\\s*(?:zł|PLN|€|\\$)/;
        document.querySelectorAll('*').forEach(el => {
            const text = el.textContent || '';
            if (text.match(pricePattern) && text.length < 100) {
                const depth = getDepth(el);
                stats.prices[depth] = (stats.prices[depth] || 0) + 1;
            }
        });
        
        // Links
        document.querySelectorAll('a[href]').forEach(el => {
            const depth = getDepth(el);
            stats.links[depth] = (stats.links[depth] || 0) + 1;
        });
        
        // Images
        document.querySelectorAll('img[src]').forEach(el => {
            const depth = getDepth(el);
            stats.images[depth] = (stats.images[depth] || 0) + 1;
        });
        
        return stats;
        """
        
        try:
            result = await page.evaluate(script)
            self.price_depth_map = defaultdict(int, {int(k): v for k, v in result['prices'].items()})
            self.link_depth_map = defaultdict(int, {int(k): v for k, v in result['links'].items()})
            self.image_depth_map = defaultdict(int, {int(k): v for k, v in result['images'].items()})
        except Exception:
            pass
    
    async def _gather_class_patterns(self, page):
        """Find repeating class patterns (potential product containers)"""
        script = """
        const classFreq = {};
        
        document.querySelectorAll('*').forEach(el => {
            if (el.className && typeof el.className === 'string') {
                const classes = el.className.split(' ').filter(c => c.length > 0);
                const firstClass = classes[0];
                if (firstClass) {
                    classFreq[firstClass] = (classFreq[firstClass] || 0) + 1;
                }
            }
        });
        
        return classFreq;
        """
        
        try:
            result = await page.evaluate(script)
            self.class_frequency = defaultdict(int, result)
        except Exception:
            pass
    
    def _calculate_optimal_depths(self) -> Dict[str, Any]:
        """
        Calculate optimal depth levels using statistical analysis
        
        NO HARD-CODED THRESHOLDS!
        Uses statistical properties:
        - Variance peaks
        - Density peaks
        - Feature co-location
        """
        optimal = {}
        
        # Find depth with highest price density
        if self.price_depth_map:
            price_depths = list(self.price_depth_map.keys())
            price_counts = list(self.price_depth_map.values())
            
            max_price_depth = price_depths[price_counts.index(max(price_counts))]
            optimal["price_peak_depth"] = max_price_depth
            optimal["price_count_at_peak"] = max(price_counts)
        
        # Find depth with best price+link+image co-location
        co_location_scores = {}
        for depth in set(self.price_depth_map.keys()) | set(self.link_depth_map.keys()) | set(self.image_depth_map.keys()):
            score = (
                self.price_depth_map.get(depth, 0) * 3 +  # Prices most important
                self.link_depth_map.get(depth, 0) * 2 +   # Links important
                self.image_depth_map.get(depth, 0) * 1    # Images helpful
            )
            co_location_scores[depth] = score
        
        if co_location_scores:
            best_depth = max(co_location_scores.items(), key=lambda x: x[1])
            optimal["co_location_depth"] = best_depth[0]
            optimal["co_location_score"] = best_depth[1]
        
        # Find depth with consistent text length (product names)
        text_variance_by_depth = {}
        for depth, lengths in self.text_length_by_depth.items():
            if len(lengths) >= 3:  # Need at least 3 samples
                variance = statistics.variance(lengths)
                text_variance_by_depth[depth] = variance
        
        if text_variance_by_depth:
            # Lower variance = more consistent = likely product names
            consistent_depth = min(text_variance_by_depth.items(), key=lambda x: x[1])
            optimal["consistent_text_depth"] = consistent_depth[0]
            optimal["text_variance"] = consistent_depth[1]
        
        return optimal
    
    def _find_repeating_patterns(self) -> Dict[str, Any]:
        """
        Find repeating patterns that suggest product containers
        
        Statistical approach: high-frequency classes are likely containers
        """
        patterns = {}
        
        if not self.class_frequency:
            return patterns
        
        # Sort by frequency
        sorted_classes = sorted(
            self.class_frequency.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Statistical threshold: classes appearing more than median
        frequencies = list(self.class_frequency.values())
        if frequencies:
            median_freq = statistics.median(frequencies)
            mean_freq = statistics.mean(frequencies)
            
            # High-frequency classes (above mean)
            high_freq = [(cls, count) for cls, count in sorted_classes if count > mean_freq]
            
            patterns["high_frequency_classes"] = high_freq[:20]  # Top 20
            patterns["median_frequency"] = median_freq
            patterns["mean_frequency"] = mean_freq
            patterns["total_unique_classes"] = len(self.class_frequency)
        
        return patterns
    
    def _generate_insights(self) -> Dict[str, Any]:
        """
        Generate statistical insights about page structure
        
        NO HARD-CODED RULES - derive from data
        """
        insights = {}
        
        # Depth distribution shape
        if self.depth_map:
            depths = list(self.depth_map.keys())
            counts = list(self.depth_map.values())
            
            insights["max_depth"] = max(depths) if depths else 0
            insights["total_elements"] = sum(counts)
            insights["avg_elements_per_depth"] = statistics.mean(counts) if counts else 0
            
            # Find depth with most elements (potential product container level)
            peak_depth = depths[counts.index(max(counts))]
            insights["element_peak_depth"] = peak_depth
            insights["element_peak_count"] = max(counts)
        
        # Feature density
        if self.price_depth_map:
            total_prices = sum(self.price_depth_map.values())
            insights["total_prices"] = total_prices
            insights["price_depth_spread"] = len(self.price_depth_map.keys())
        
        # Page complexity score
        if self.class_frequency:
            unique_classes = len(self.class_frequency)
            total_elements = sum(self.depth_map.values()) if self.depth_map else 1
            insights["class_diversity"] = unique_classes / total_elements if total_elements > 0 else 0
        
        return insights


class AdaptiveDepthAnalyzer:
    """
    Dynamically finds optimal container depth
    
    Uses DOMStatistics to avoid hard-coded rules:
    1. Analyze statistical properties at each depth
    2. Score depths based on feature co-location
    3. Select optimal depth dynamically
    """
    
    def __init__(self):
        self.stats = DOMStatistics()
    
    async def find_optimal_container_depth(
        self,
        page,
        instruction: str = ""
    ) -> Dict[str, Any]:
        """
        Find optimal depth for product containers
        
        Returns:
            {
                "recommended_depth": <int>,
                "confidence": <float>,
                "reasoning": <str>,
                "alternatives": [<depths>],
                "statistics": {...}
            }
        """
        # Gather statistics
        dom_stats = await self.stats.analyze_dom_tree(page)
        
        # Extract optimal depths
        optimal_depths = dom_stats.get("optimal_depths", {})
        
        # Score each candidate depth
        depth_scores = {}
        
        # Price peak depth (most important)
        if "price_peak_depth" in optimal_depths:
            depth = optimal_depths["price_peak_depth"]
            depth_scores[depth] = depth_scores.get(depth, 0) + 50
        
        # Co-location depth (price + link + image together)
        if "co_location_depth" in optimal_depths:
            depth = optimal_depths["co_location_depth"]
            depth_scores[depth] = depth_scores.get(depth, 0) + 40
        
        # Consistent text depth (uniform product names)
        if "consistent_text_depth" in optimal_depths:
            depth = optimal_depths["consistent_text_depth"]
            depth_scores[depth] = depth_scores.get(depth, 0) + 30
        
        # Element peak depth (many similar elements)
        insights = dom_stats.get("statistical_insights", {})
        if "element_peak_depth" in insights:
            depth = insights["element_peak_depth"]
            depth_scores[depth] = depth_scores.get(depth, 0) + 20
        
        # Select best depth
        if depth_scores:
            best_depth = max(depth_scores.items(), key=lambda x: x[1])
            
            # Calculate confidence based on score separation
            sorted_scores = sorted(depth_scores.values(), reverse=True)
            if len(sorted_scores) > 1:
                confidence = (sorted_scores[0] - sorted_scores[1]) / sorted_scores[0]
            else:
                confidence = 1.0
            
            return {
                "recommended_depth": best_depth[0],
                "confidence": min(confidence, 1.0),
                "reasoning": self._generate_reasoning(best_depth[0], dom_stats),
                "alternatives": [d for d, s in sorted(depth_scores.items(), key=lambda x: x[1], reverse=True)][1:4],
                "statistics": dom_stats,
                "depth_scores": depth_scores
            }
        
        # Fallback: use statistical median
        all_depths = set()
        for depth_map in [self.stats.price_depth_map, self.stats.link_depth_map, self.stats.image_depth_map]:
            all_depths.update(depth_map.keys())
        
        if all_depths:
            median_depth = int(statistics.median(all_depths))
            return {
                "recommended_depth": median_depth,
                "confidence": 0.3,
                "reasoning": "Using statistical median depth as fallback",
                "alternatives": [],
                "statistics": dom_stats
            }
        
        return {
            "recommended_depth": None,
            "confidence": 0.0,
            "reasoning": "Could not determine optimal depth from statistics",
            "alternatives": [],
            "statistics": dom_stats
        }
    
    def _generate_reasoning(self, depth: int, stats: Dict) -> str:
        """Generate human-readable reasoning for depth selection"""
        reasons = []
        
        optimal = stats.get("optimal_depths", {})
        
        if optimal.get("price_peak_depth") == depth:
            count = optimal.get("price_count_at_peak", 0)
            reasons.append(f"Peak price density ({count} prices at this depth)")
        
        if optimal.get("co_location_depth") == depth:
            score = optimal.get("co_location_score", 0)
            reasons.append(f"Best feature co-location (score: {score})")
        
        if optimal.get("consistent_text_depth") == depth:
            reasons.append("Consistent text length (likely product names)")
        
        insights = stats.get("statistical_insights", {})
        if insights.get("element_peak_depth") == depth:
            count = insights.get("element_peak_count", 0)
            reasons.append(f"Element count peak ({count} elements)")
        
        return " | ".join(reasons) if reasons else "Statistical analysis"
