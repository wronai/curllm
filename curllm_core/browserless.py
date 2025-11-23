#!/usr/bin/env python3
import base64
import json

class BrowserlessContext:
    """Wrapper for Browserless WebSocket connection"""
    def __init__(self, websocket):
        self.ws = websocket

    async def new_page(self):
        await self.ws.send(json.dumps({"type": "newPage", "stealth": True}))
        return BrowserlessPage(self.ws)

    async def close(self):
        await self.ws.close()

class BrowserlessPage:
    def __init__(self, websocket):
        self.ws = websocket

    async def goto(self, url: str):
        await self.ws.send(json.dumps({"type": "goto", "url": url}))

    async def click(self, selector: str):
        await self.ws.send(json.dumps({"type": "click", "selector": selector}))

    async def fill(self, selector: str, value: str):
        await self.ws.send(json.dumps({"type": "fill", "selector": selector, "value": value}))

    async def screenshot(self, path: str):
        await self.ws.send(json.dumps({"type": "screenshot"}))
        response = await self.ws.recv()
        data = json.loads(response)
        with open(path, 'wb') as f:
            f.write(base64.b64decode(data['screenshot']))

    async def evaluate(self, script: str):
        await self.ws.send(json.dumps({"type": "evaluate", "script": script}))
        response = await self.ws.recv()
        return json.loads(response).get('result')

    async def close(self):
        await self.ws.send(json.dumps({"type": "closePage"}))
