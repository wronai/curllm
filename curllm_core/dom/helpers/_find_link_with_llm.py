import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from .link_info import LinkInfo
from .extract_all_links import extract_all_links

logger = logging.getLogger(__name__)

async def _find_link_with_llm(page, goal: str, llm) -> Optional[LinkInfo]:
    """Use LLM to find the best link for a goal"""
    try:
        # Get all visible links with context
        all_links = await extract_all_links(page)
        
        if not all_links:
            return None
        
        # Prepare compact link summary for LLM
        link_summary = []
        for i, link in enumerate(all_links[:50]):  # Limit for token efficiency
            link_summary.append({
                "idx": i,
                "text": link.text[:50] if link.text else "",
                "url": link.url,
                "loc": link.location,
                "aria": link.aria_label[:30] if link.aria_label else ""
            })
        
        import json
        prompt = f"""Find the best link for goal: "{goal}"

Available links:
{json.dumps(link_summary, indent=1)}

Return JSON: {{"index": N, "confidence": 0.0-1.0, "reason": "why"}}
If no good match, return: {{"index": -1, "confidence": 0, "reason": "not found"}}
"""
        
        response = await llm.aquery(prompt)
        
        # Parse response
        import re
        json_match = re.search(r'\{[^{}]+\}', response)
        if json_match:
            result = json.loads(json_match.group())
            idx = result.get('index', -1)
            confidence = result.get('confidence', 0)
            
            if idx >= 0 and idx < len(all_links) and confidence > 0.5:
                link = all_links[idx]
                link.score = confidence * 10
                link.method = 'llm'
                logger.info(f"LLM found link for {goal}: {link.url} (confidence: {confidence})")
                return link
    
    except Exception as e:
        logger.debug(f"LLM link finding failed: {e}")
    
    return None
