"""Browserless Page - Wrapper for Browserless page operations"""

import base64
import json


class BrowserlessPage:
    """Browserless page wrapper"""
    
    def __init__(self, websocket):
        self.ws = websocket
    
    async def goto(self, url: str):
        """Navigate to URL"""
        await self.ws.send(json.dumps({
            "type": "goto",
            "url": url
        }))
    
    async def click(self, selector: str):
        """Click element"""
        await self.ws.send(json.dumps({
            "type": "click",
            "selector": selector
        }))
    
    async def fill(self, selector: str, value: str):
        """Fill input field"""
        await self.ws.send(json.dumps({
            "type": "fill",
            "selector": selector,
            "value": value
        }))
    
    async def screenshot(self, path: str):
        """Take screenshot"""
        await self.ws.send(json.dumps({
            "type": "screenshot"
        }))
        # Wait for base64 response
        response = await self.ws.recv()
        data = json.loads(response)
        
        # Save to file
        with open(path, 'wb') as f:
            f.write(base64.b64decode(data['screenshot']))
    
    async def evaluate(self, script: str):
        """Execute JavaScript"""
        await self.ws.send(json.dumps({
            "type": "evaluate",
            "script": script
        }))
        response = await self.ws.recv()
        return json.loads(response).get('result')
    
    async def close(self):
        """Close page"""
        await self.ws.send(json.dumps({
            "type": "closePage"
        }))
