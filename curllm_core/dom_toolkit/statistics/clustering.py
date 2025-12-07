"""
Element Clusterer - Group Similar DOM Elements

Cluster elements by structural similarity without LLM.
Uses feature vectors and simple distance metrics.
"""

from typing import Dict, List, Any


class ElementClusterer:
    """
    Cluster DOM elements by similarity.
    
    Features used for clustering:
    - Tag name
    - Class structure
    - Children count
    - Text length
    - Presence of links/images
    """
    
    @staticmethod
    async def cluster_by_structure(page, selector: str, max_clusters: int = 10) -> Dict[str, Any]:
        """
        Cluster elements matching selector by their internal structure.
        
        Returns clusters with representative samples.
        """
        return await page.evaluate("""
            (args) => {
                const elements = document.querySelectorAll(args.selector);
                if (elements.length === 0) return { found: false };
                
                // Build feature vector for each element
                const features = Array.from(elements).map(el => {
                    const childTags = {};
                    for (const child of el.children) {
                        const tag = child.tagName.toLowerCase();
                        childTags[tag] = (childTags[tag] || 0) + 1;
                    }
                    
                    return {
                        element: el,
                        features: {
                            children_count: el.children.length,
                            text_length: (el.textContent || '').length,
                            has_link: !!el.querySelector('a[href]'),
                            has_image: !!el.querySelector('img'),
                            has_price: /\\d+[,.]\\d{2}/.test(el.textContent || ''),
                            child_tags: Object.keys(childTags).sort().join(','),
                            depth: (() => {
                                let d = 0, c = el;
                                while (c && c !== document.body) { d++; c = c.parentElement; }
                                return d;
                            })()
                        }
                    };
                });
                
                // Simple clustering by feature signature
                const clusters = new Map();
                
                for (const item of features) {
                    // Create signature from key features
                    const sig = [
                        item.features.children_count > 5 ? 'many_children' : 'few_children',
                        item.features.text_length > 100 ? 'long_text' : 'short_text',
                        item.features.has_link ? 'has_link' : 'no_link',
                        item.features.has_image ? 'has_image' : 'no_image',
                        item.features.has_price ? 'has_price' : 'no_price',
                        item.features.child_tags
                    ].join('|');
                    
                    if (!clusters.has(sig)) {
                        clusters.set(sig, {
                            signature: sig,
                            count: 0,
                            samples: [],
                            features: item.features
                        });
                    }
                    
                    const cluster = clusters.get(sig);
                    cluster.count++;
                    if (cluster.samples.length < 3) {
                        cluster.samples.push({
                            text_preview: (item.element.textContent || '').slice(0, 100),
                            classes: typeof item.element.className === 'string' 
                                ? item.element.className.split(' ').slice(0, 3).join(' ')
                                : ''
                        });
                    }
                }
                
                // Sort clusters by size
                const sortedClusters = Array.from(clusters.values())
                    .sort((a, b) => b.count - a.count)
                    .slice(0, args.maxClusters);
                
                return {
                    found: true,
                    total_elements: elements.length,
                    cluster_count: clusters.size,
                    clusters: sortedClusters
                };
            }
        """, {"selector": selector, "maxClusters": max_clusters})
    
    @staticmethod
    async def find_similar_elements(page, reference_selector: str, threshold: float = 0.7) -> List[Dict]:
        """
        Find elements similar to a reference element.
        
        Uses structural similarity scoring.
        """
        return await page.evaluate("""
            (args) => {
                const ref = document.querySelector(args.referenceSelector);
                if (!ref) return [];
                
                // Build reference features
                const refFeatures = {
                    tag: ref.tagName,
                    children_count: ref.children.length,
                    text_length: (ref.textContent || '').length,
                    child_tags: Array.from(ref.children).map(c => c.tagName).sort().join(','),
                    has_link: !!ref.querySelector('a[href]'),
                    has_image: !!ref.querySelector('img')
                };
                
                // Score similarity function
                const scoreSimilarity = (el) => {
                    let score = 0;
                    const maxScore = 6;
                    
                    if (el.tagName === refFeatures.tag) score += 1;
                    if (Math.abs(el.children.length - refFeatures.children_count) <= 2) score += 1;
                    
                    const textLenRatio = Math.min(
                        (el.textContent || '').length / refFeatures.text_length,
                        refFeatures.text_length / (el.textContent || '').length
                    );
                    if (textLenRatio > 0.5) score += 1;
                    
                    const childTags = Array.from(el.children).map(c => c.tagName).sort().join(',');
                    if (childTags === refFeatures.child_tags) score += 1;
                    
                    if (!!el.querySelector('a[href]') === refFeatures.has_link) score += 1;
                    if (!!el.querySelector('img') === refFeatures.has_image) score += 1;
                    
                    return score / maxScore;
                };
                
                // Find similar elements
                const similar = [];
                const allElements = document.querySelectorAll(ref.tagName);
                
                for (const el of allElements) {
                    if (el === ref) continue;
                    
                    const similarity = scoreSimilarity(el);
                    if (similarity >= args.threshold) {
                        const cls = typeof el.className === 'string'
                            ? el.className.split(' ')[0]
                            : null;
                        
                        similar.push({
                            selector: el.tagName.toLowerCase() + (cls ? '.' + cls : ''),
                            similarity: Math.round(similarity * 100) / 100,
                            text_preview: (el.textContent || '').slice(0, 80)
                        });
                    }
                }
                
                return similar.sort((a, b) => b.similarity - a.similarity).slice(0, 50);
            }
        """, {"referenceSelector": reference_selector, "threshold": threshold})
    
    @staticmethod
    async def group_by_parent(page, selector: str) -> List[Dict]:
        """
        Group elements by their parent container.
        
        Useful for understanding item distribution across containers.
        """
        return await page.evaluate("""
            (selector) => {
                const elements = document.querySelectorAll(selector);
                const byParent = new Map();
                
                for (const el of elements) {
                    const parent = el.parentElement;
                    if (!parent) continue;
                    
                    const parentCls = typeof parent.className === 'string'
                        ? parent.className.split(' ')[0]
                        : null;
                    const parentKey = parent.tagName.toLowerCase() + 
                        (parentCls ? '.' + parentCls : '');
                    
                    if (!byParent.has(parentKey)) {
                        byParent.set(parentKey, {
                            parent_selector: parentKey,
                            count: 0,
                            sample_children: []
                        });
                    }
                    
                    const group = byParent.get(parentKey);
                    group.count++;
                    if (group.sample_children.length < 2) {
                        group.sample_children.push(
                            (el.textContent || '').slice(0, 50)
                        );
                    }
                }
                
                return Array.from(byParent.values())
                    .sort((a, b) => b.count - a.count)
                    .slice(0, 15);
            }
        """, selector)
