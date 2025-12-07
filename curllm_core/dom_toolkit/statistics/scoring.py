"""
Candidate Scorer - Score and Rank Container Candidates

Score potential containers using statistical features.
No LLM - pure mathematical scoring.
"""

from typing import Dict, List, Any


class CandidateScorer:
    """
    Score container candidates for product/item extraction.
    
    Scoring factors:
    - Repetition count (more = better)
    - Structural completeness (link + price + image)
    - Text quality (not too short/long)
    - Class name semantics (simple heuristics)
    """
    
    @staticmethod
    async def score_containers(page, selectors: List[str]) -> List[Dict]:
        """
        Score multiple container selectors.
        
        Returns sorted list with scores and reasoning.
        """
        return await page.evaluate("""
            (selectors) => {
                const results = [];
                const pricePattern = /\\d+[,.]\\d{2}\\s*(?:zł|PLN|€|\\$)/i;
                
                for (const selector of selectors) {
                    try {
                        const elements = document.querySelectorAll(selector);
                        if (elements.length === 0) continue;
                        
                        // Sample first 10 elements
                        const samples = Array.from(elements).slice(0, 10);
                        
                        // Calculate metrics
                        let linksCount = 0;
                        let pricesCount = 0;
                        let imagesCount = 0;
                        let totalTextLen = 0;
                        
                        for (const el of samples) {
                            if (el.querySelector('a[href]')) linksCount++;
                            if (pricePattern.test(el.textContent || '')) pricesCount++;
                            if (el.querySelector('img')) imagesCount++;
                            totalTextLen += (el.textContent || '').length;
                        }
                        
                        const n = samples.length;
                        const linkRatio = linksCount / n;
                        const priceRatio = pricesCount / n;
                        const imageRatio = imagesCount / n;
                        const avgTextLen = totalTextLen / n;
                        
                        // Calculate score
                        let score = 0;
                        const reasons = [];
                        
                        // Count bonus (more repetition = more likely a list)
                        if (elements.length >= 10) {
                            score += 30;
                            reasons.push('good_count');
                        } else if (elements.length >= 5) {
                            score += 20;
                            reasons.push('ok_count');
                        }
                        
                        // Structure bonuses
                        if (linkRatio >= 0.8) {
                            score += 25;
                            reasons.push('has_links');
                        }
                        if (priceRatio >= 0.5) {
                            score += 35;
                            reasons.push('has_prices');
                        }
                        if (imageRatio >= 0.5) {
                            score += 15;
                            reasons.push('has_images');
                        }
                        
                        // Text quality
                        if (avgTextLen > 30 && avgTextLen < 500) {
                            score += 20;
                            reasons.push('good_text_len');
                        } else if (avgTextLen <= 30) {
                            score -= 20;
                            reasons.push('too_short');
                        } else if (avgTextLen > 2000) {
                            score -= 30;
                            reasons.push('too_long');
                        }
                        
                        // Class name heuristics
                        const selectorLower = selector.toLowerCase();
                        const productKeywords = ['product', 'produkt', 'item', 'card', 'tile', 'offer'];
                        const penaltyKeywords = ['nav', 'menu', 'header', 'footer', 'sidebar', 'banner', 'ad-'];
                        
                        if (productKeywords.some(kw => selectorLower.includes(kw))) {
                            score += 20;
                            reasons.push('product_class');
                        }
                        if (penaltyKeywords.some(kw => selectorLower.includes(kw))) {
                            score -= 40;
                            reasons.push('nav_class_penalty');
                        }
                        
                        results.push({
                            selector,
                            count: elements.length,
                            score,
                            metrics: {
                                link_ratio: Math.round(linkRatio * 100) / 100,
                                price_ratio: Math.round(priceRatio * 100) / 100,
                                image_ratio: Math.round(imageRatio * 100) / 100,
                                avg_text_len: Math.round(avgTextLen)
                            },
                            reasons
                        });
                    } catch (e) {
                        // Invalid selector, skip
                    }
                }
                
                return results.sort((a, b) => b.score - a.score);
            }
        """, selectors)
    
    @staticmethod
    async def rank_by_completeness(page, selector: str) -> Dict[str, Any]:
        """
        Rank elements by field completeness.
        
        Checks which elements have: name, price, url, image.
        """
        return await page.evaluate("""
            (selector) => {
                const elements = document.querySelectorAll(selector);
                if (elements.length === 0) return { found: false };
                
                const pricePattern = /\\d+[,.]\\d{2}\\s*(?:zł|PLN|€|\\$)/i;
                
                const completeness = {
                    all_4: 0,  // name + price + url + image
                    has_3: 0,  // 3 of 4
                    has_2: 0,  // 2 of 4
                    has_1: 0,  // 1 of 4
                    none: 0
                };
                
                const samples = { complete: [], incomplete: [] };
                
                for (const el of elements) {
                    const text = (el.textContent || '').trim();
                    
                    // Check fields
                    const hasName = text.length > 20 && text.length < 500;
                    const hasPrice = pricePattern.test(text);
                    const hasUrl = !!el.querySelector('a[href]');
                    const hasImage = !!el.querySelector('img');
                    
                    const fieldCount = [hasName, hasPrice, hasUrl, hasImage]
                        .filter(Boolean).length;
                    
                    if (fieldCount === 4) completeness.all_4++;
                    else if (fieldCount === 3) completeness.has_3++;
                    else if (fieldCount === 2) completeness.has_2++;
                    else if (fieldCount === 1) completeness.has_1++;
                    else completeness.none++;
                    
                    // Collect samples
                    if (fieldCount >= 3 && samples.complete.length < 2) {
                        samples.complete.push(text.slice(0, 80));
                    } else if (fieldCount <= 1 && samples.incomplete.length < 2) {
                        samples.incomplete.push(text.slice(0, 80));
                    }
                }
                
                const total = elements.length;
                const qualityScore = (
                    completeness.all_4 * 4 +
                    completeness.has_3 * 3 +
                    completeness.has_2 * 2 +
                    completeness.has_1 * 1
                ) / (total * 4) * 100;
                
                return {
                    found: true,
                    total: total,
                    completeness,
                    quality_score: Math.round(qualityScore),
                    samples
                };
            }
        """, selector)
    
    @staticmethod
    async def compare_selectors(page, selector_a: str, selector_b: str) -> Dict[str, Any]:
        """
        Compare two selectors and recommend the better one.
        
        Returns comparison with clear winner.
        """
        return await page.evaluate("""
            (args) => {
                const analyze = (selector) => {
                    const elements = document.querySelectorAll(selector);
                    if (elements.length === 0) return null;
                    
                    const samples = Array.from(elements).slice(0, 10);
                    const pricePattern = /\\d+[,.]\\d{2}/;
                    
                    let priceCount = 0, linkCount = 0, imgCount = 0, textSum = 0;
                    for (const el of samples) {
                        if (pricePattern.test(el.textContent || '')) priceCount++;
                        if (el.querySelector('a[href]')) linkCount++;
                        if (el.querySelector('img')) imgCount++;
                        textSum += (el.textContent || '').length;
                    }
                    
                    return {
                        count: elements.length,
                        price_ratio: priceCount / samples.length,
                        link_ratio: linkCount / samples.length,
                        image_ratio: imgCount / samples.length,
                        avg_text: textSum / samples.length
                    };
                };
                
                const a = analyze(args.selectorA);
                const b = analyze(args.selectorB);
                
                if (!a && !b) return { winner: null, reason: 'both_invalid' };
                if (!a) return { winner: 'B', reason: 'A_invalid' };
                if (!b) return { winner: 'A', reason: 'B_invalid' };
                
                // Score each
                const scoreA = a.count + a.price_ratio * 50 + a.link_ratio * 30;
                const scoreB = b.count + b.price_ratio * 50 + b.link_ratio * 30;
                
                return {
                    A: { selector: args.selectorA, ...a, score: Math.round(scoreA) },
                    B: { selector: args.selectorB, ...b, score: Math.round(scoreB) },
                    winner: scoreA > scoreB ? 'A' : scoreB > scoreA ? 'B' : 'tie',
                    score_diff: Math.abs(scoreA - scoreB)
                };
            }
        """, {"selectorA": selector_a, "selectorB": selector_b})
