#!/usr/bin/env python3
"""
curllm_core.bql - Browser Query Language Parser and Executor (internal)
This is a packaged copy of the original bql_parser.py for reuse.
"""

import json
import re
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Union
from enum import Enum

class QueryType(Enum):
    PAGE = "page"
    NAVIGATE = "navigate"
    CLICK = "click"
    FILL = "fill"
    SELECT = "select"
    EXTRACT = "extract"
    WAIT = "wait"
    SCREENSHOT = "screenshot"

@dataclass
class BQLNode:
    type: QueryType
    selector: Optional[str] = None
    attributes: Dict[str, Any] = None
    children: List['BQLNode'] = None

    def __post_init__(self):
        self.attributes = self.attributes or {}
        self.children = self.children or []

class BQLParser:
    def __init__(self):
        self.tokens = []
        self.current = 0

    def parse(self, query: str) -> Dict[str, Any]:
        query = self._preprocess(query)
        self.tokens = self._tokenize(query)
        self.current = 0
        if self._match("query"):
            return self._parse_query_block()
        elif self._match("mutation"):
            return self._parse_mutation_block()
        else:
            return self._parse_simple_instruction(query)

    def _preprocess(self, query: str) -> str:
        query = re.sub(r'#.*?\n', '\n', query)
        query = re.sub(r'\s+', ' ', query)
        return query.strip()

    def _tokenize(self, query: str) -> List[str]:
        pattern = r'(\w+|{|}|\(|\)|:|,|"[^"]*"|\'[^\']*\'|\[|\]|=)'
        tokens = re.findall(pattern, query)
        return [t.strip() for t in tokens if t.strip()]

    def _match(self, *expected: str) -> bool:
        if self.current < len(self.tokens):
            return self.tokens[self.current] in expected
        return False

    def _consume(self, expected: str = None) -> str:
        if self.current >= len(self.tokens):
            raise SyntaxError("Unexpected end of query")
        token = self.tokens[self.current]
        if expected and token != expected:
            raise SyntaxError(f"Expected '{expected}', got '{token}'")
        self.current += 1
        return token

    def _parse_query_block(self) -> Dict[str, Any]:
        self._consume("query")
        name = None
        if not self._match("{"):
            name = self._consume()
        self._consume("{")
        operations = []
        while not self._match("}"):
            operations.append(self._parse_operation())
            if self._match(","):
                self._consume(",")
        self._consume("}")
        return {"type": "query", "name": name, "operations": operations}

    def _parse_mutation_block(self) -> Dict[str, Any]:
        self._consume("mutation")
        name = None
        if not self._match("{"):
            name = self._consume()
        self._consume("{")
        actions = []
        while not self._match("}"):
            actions.append(self._parse_action())
            if self._match(","):
                self._consume(",")
        self._consume("}")
        return {"type": "mutation", "name": name, "actions": actions}

    def _parse_operation(self) -> Dict[str, Any]:
        alias = None
        if self.current + 1 < len(self.tokens) and self.tokens[self.current + 1] == ":":
            alias = self._consume()
            self._consume(":")
        operation = self._consume()
        args = {}
        if self._match("("):
            args = self._parse_arguments()
        selections = []
        if self._match("{"):
            selections = self._parse_selection_set()
        return {"alias": alias, "operation": operation, "arguments": args, "selections": selections}

    def _parse_action(self) -> Dict[str, Any]:
        action_type = self._consume()
        args = {}
        if self._match("("):
            args = self._parse_arguments()
        return {"action": action_type, "arguments": args}

    def _parse_arguments(self) -> Dict[str, Any]:
        self._consume("(")
        args = {}
        while not self._match(")"):
            key = self._consume()
            self._consume(":")
            value = self._parse_value()
            args[key] = value
            if self._match(","):
                self._consume(",")
        self._consume(")")
        return args

    def _parse_value(self) -> Any:
        token = self.tokens[self.current]
        if token.startswith('"') or token.startswith("'"):
            value = self._consume()
            return value[1:-1]
        if token.replace('.', '').replace('-', '').isdigit():
            value = self._consume()
            return float(value) if '.' in value else int(value)
        if token in ['true', 'false']:
            return self._consume() == 'true'
        if token == '[':
            return self._parse_array()
        if token == '{':
            return self._parse_object()
        return self._consume()

    def _parse_array(self) -> List[Any]:
        self._consume("[")
        items = []
        while not self._match("]"):
            items.append(self._parse_value())
            if self._match(","):
                self._consume(",")
        self._consume("]")
        return items

    def _parse_object(self) -> Dict[str, Any]:
        self._consume("{")
        obj = {}
        while not self._match("}"):
            key = self._consume()
            self._consume(":")
            value = self._parse_value()
            obj[key] = value
            if self._match(","):
                self._consume(",")
        self._consume("}")
        return obj

    def _parse_selection_set(self) -> List[Dict[str, Any]]:
        self._consume("{")
        selections = []
        while not self._match("}"):
            selections.append(self._parse_operation())
            if self._match(","):
                self._consume(",")
        self._consume("}")
        return selections

    def _parse_simple_instruction(self, instruction: str) -> Dict[str, Any]:
        return {"type": "instruction", "text": instruction, "operations": self._extract_operations_from_text(instruction)}

    def _extract_operations_from_text(self, text: str) -> List[Dict[str, Any]]:
        operations: List[Dict[str, Any]] = []
        patterns = {
            "navigate": r'(?:go to|navigate to|open|visit)\s+(?:url\s+)?([^\s]+)',
            "click": r'click\s+(?:on\s+)?(?:the\s+)?([^,]+)',
            "fill": r'(?:fill|type|enter)\s+([^\s]+)\s+(?:with|as|=)\s+([^,]+)',
            "extract": r'(?:extract|get|find|scrape)\s+(?:all\s+)?([^,]+)',
            "wait": r'wait\s+(?:for\s+)?(\d+)\s*(?:seconds?|ms)?',
        }
        for op_type, pattern in patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if op_type == "navigate":
                    operations.append({"operation": "navigate", "arguments": {"url": match.group(1)}})
                elif op_type == "click":
                    operations.append({"operation": "click", "arguments": {"selector": match.group(1).strip()}})
                elif op_type == "fill":
                    operations.append({"operation": "fill", "arguments": {"field": match.group(1).strip(), "value": match.group(2).strip()}})
                elif op_type == "extract":
                    operations.append({"operation": "extract", "arguments": {"target": match.group(1).strip()}})
                elif op_type == "wait":
                    duration = int(match.group(1))
                    operations.append({"operation": "wait", "arguments": {"duration": duration}})
        return operations

class BQLExecutor:
    def __init__(self, browser_context):
        self.browser = browser_context
        self.parser = BQLParser()

    async def execute(self, query: str) -> Dict[str, Any]:
        parsed = self.parser.parse(query)
        if parsed["type"] == "query":
            return await self._execute_query(parsed)
        elif parsed["type"] == "mutation":
            return await self._execute_mutation(parsed)
        else:
            return await self._execute_instruction(parsed)

    async def _execute_query(self, query: Dict) -> Dict[str, Any]:
        results = {}
        for operation in query["operations"]:
            result = await self._execute_operation(operation)
            key = operation["alias"] or operation["operation"]
            results[key] = result
        return {"data": results, "errors": []}

    async def _execute_mutation(self, mutation: Dict) -> Dict[str, Any]:
        results = []
        for action in mutation["actions"]:
            result = await self._execute_action(action)
            results.append(result)
        return {"data": {"mutations": results}, "errors": []}

    async def _execute_operation(self, operation: Dict) -> Any:
        op_type = operation["operation"]
        args = operation["arguments"]
        if op_type == "page":
            page = await self.browser.new_page()
            await page.goto(args.get("url"))
            if operation["selections"]:
                return await self._execute_selections(page, operation["selections"])
            else:
                return {"url": await page.evaluate("() => window.location.href"), "title": await page.title()}
        elif op_type == "select":
            selector = args.get("css") or args.get("xpath")
            elements = await self.browser.current_page.query_selector_all(selector)
            results: List[Any] = []
            for element in elements:
                if operation["selections"]:
                    result: Dict[str, Any] = {}
                    for selection in operation["selections"]:
                        key = selection["alias"] or selection["operation"]
                        result[key] = await self._extract_from_element(element, selection)
                    results.append(result)
                else:
                    results.append(await element.text_content())
            return results
        elif op_type == "text":
            selector = args.get("css")
            if selector:
                element = await self.browser.current_page.query_selector(selector)
                return await element.text_content() if element else None
            return None
        elif op_type == "attr":
            selector = args.get("css")
            attr_name = args.get("name")
            if selector:
                element = await self.browser.current_page.query_selector(selector)
                return await element.get_attribute(attr_name) if element else None
            return None

    async def _execute_action(self, action: Dict) -> Dict[str, Any]:
        action_type = action["action"]
        args = action["arguments"]
        try:
            if action_type == "click":
                await self.browser.current_page.click(args["selector"])
                return {"success": True, "action": "click"}
            elif action_type == "fill":
                await self.browser.current_page.fill(args["selector"], args["value"])
                return {"success": True, "action": "fill"}
            elif action_type == "navigate":
                await self.browser.current_page.goto(args["url"])
                return {"success": True, "action": "navigate", "url": args["url"]}
            elif action_type == "wait":
                await self.browser.current_page.wait_for_timeout(args.get("duration", 1000))
                return {"success": True, "action": "wait"}
            else:
                return {"success": False, "error": f"Unknown action: {action_type}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _execute_selections(self, page, selections: List[Dict]) -> Dict[str, Any]:
        results: Dict[str, Any] = {}
        for selection in selections:
            key = selection["alias"] or selection["operation"]
            results[key] = await self._execute_page_selection(page, selection)
        return results

    async def _execute_page_selection(self, page, selection: Dict) -> Any:
        op = selection["operation"]
        args = selection["arguments"]
        if op == "title":
            return await page.title()
        elif op == "url":
            return await page.evaluate("() => window.location.href")
        elif op == "text":
            if "css" in args:
                element = await page.query_selector(args["css"])
                return await element.text_content() if element else None
            else:
                return await page.text_content()
        elif op == "select":
            return await self._select_elements(page, selection)
        return None

    async def _select_elements(self, page, selection: Dict) -> List[Dict]:
        selector = selection["arguments"].get("css")
        elements = await page.query_selector_all(selector)
        results: List[Dict[str, Any]] = []
        for element in elements:
            if selection["selections"]:
                item: Dict[str, Any] = {}
                for sub_selection in selection["selections"]:
                    key = sub_selection["alias"] or sub_selection["operation"]
                    item[key] = await self._extract_from_element(element, sub_selection)
                results.append(item)
            else:
                results.append(await element.text_content())
        return results

    async def _extract_from_element(self, element, selection: Dict) -> Any:
        op = selection["operation"]
        args = selection["arguments"]
        if op == "text":
            if "css" in args:
                sub_element = await element.query_selector(args["css"])
                return await sub_element.text_content() if sub_element else None
            return await element.text_content()
        elif op == "attr":
            return await element.get_attribute(args["name"])
        elif op == "html":
            return await element.inner_html()
        return None

    async def _execute_instruction(self, instruction: Dict) -> Dict[str, Any]:
        results: List[Any] = []
        for operation in instruction["operations"]:
            result = await self._execute_operation(operation)
            results.append(result)
        return {"data": results, "instruction": instruction["text"], "errors": []}
