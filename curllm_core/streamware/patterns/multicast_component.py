from typing import Any, List, Callable, Optional, Iterator
import json
from ..core import Component, StreamComponent
from ..uri import StreamwareURI
from ..registry import register, create_component
from ..exceptions import ComponentError
from ...diagnostics import get_logger

logger = get_logger(__name__)


@register("multicast")
class MulticastComponent(Component):
    """
    Send data to multiple destinations
    
    URI format:
        multicast://parallel?destinations=uri1,uri2,uri3
    """
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def process(self, data: Any) -> List[Any]:
        """Send to all destinations and collect results"""
        destinations = self.uri.get_param('destinations', [])
        
        if isinstance(destinations, str):
            destinations = [d.strip() for d in destinations.split(',')]
            
        if not destinations:
            logger.warning("Multicast has no destinations")
            return [data]
            
        results = []
        
        for dest_uri in destinations:
            try:
                component = create_component(dest_uri)
                result = component.process(data)
                results.append(result)
            except Exception as e:
                logger.error(f"Multicast destination {dest_uri} failed: {e}")
                results.append({"error": str(e), "destination": dest_uri})
                
        return results

