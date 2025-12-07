"""Browserless Context - Wrapper for Browserless WebSocket connection"""

import json

from curllm_server.browser.browserless_page import BrowserlessPage


class BrowserlessContext:
    """Wrapper for Browserless WebSocket connection"""
    
    def __init__(self, websocket):
        self.ws = websocket
    
    async def new_page(self):
        """Create new page via Browserless"""
        # Send BQL query to create page
        await self.ws.send(json.dumps({
            "type": "newPage",
            "stealth": True
        }))
        # Return page wrapper
        return BrowserlessPage(self.ws)
    
    async def close(self):
        """Close connection"""
        await self.ws.close()
