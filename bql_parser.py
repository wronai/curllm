#!/usr/bin/env python3
"""
bql_parser.py - Browser Query Language Parser
GraphQL-like syntax for browser automation and data extraction
"""

import json
import re
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Union
from enum import Enum

class QueryType(Enum):
    """BQL query types"""
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
    """Represents a node in BQL query tree"""
    type: QueryType
    selector: Optional[str] = None
    attributes: Dict[str, Any] = None
    children: List['BQLNode'] = None
    
    def __post_init__(self):
        self.attributes = self.attributes or {}
        self.children = self.children or []

class BQLParser:
    """Parser for Browser Query Language"""
    
    def __init__(self):
        self.tokens = []
        self.current = 0
    
    def parse(self, query: str) -> Dict[str, Any]:
        """Parse BQL query string into execution plan"""
        
        # Clean and tokenize
        query = self._preprocess(query)
        self.tokens = self._tokenize(query)
        self.current = 0
        
        # Parse root query
        if self._match("query"):
            return self._parse_query_block()
        elif self._match("mutation"):
            return self._parse_mutation_block()
        else:
            # Try to parse as simple instruction
            return self._parse_simple_instruction(query)
    
    def _preprocess(self, query: str) -> str:
        """Preprocess query string"""
        # Remove comments
        query = re.sub(r'#.*?\n', '\n', query)
        # Normalize whitespace
        query = re.sub(r'\s+', ' ', query)
        return query.strip()
    
    def _tokenize(self, query: str) -> List[str]:
        """Tokenize query into components"""
        # Simple tokenizer - can be enhanced
        pattern = r'(\w+|{|}|\(|\)|:|,|"[^"]*"|\'[^\']*\'|\[|\]|=)'
        tokens = re.findall(pattern, query)
        return [t.strip() for t in tokens if t.strip()]
    
    def _match(self, *expected: str) -> bool:
        """Check if current token matches expected"""
        if self.current < len(self.tokens):
            return self.tokens[self.current] in expected
        return False
    
    def _consume(self, expected: str = None) -> str:
        """Consume and return current token"""
        if self.current >= len(self.tokens):
            raise SyntaxError(f"Unexpected end of query")
        
        token = self.tokens[self.current]
        if expected and token != expected:
            raise SyntaxError(f"Expected '{expected}', got '{token}'")
        
        self.current += 1
        return token
    
    def _parse_query_block(self) -> Dict[str, Any]:
        """Parse query block"""
        self._consume("query")
        
        # Optional query name
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
        
        return {
            "type": "query",
            "name": name,
            "operations": operations
        }
    
    def _parse_mutation_block(self) -> Dict[str, Any]:
        """Parse mutation block for actions"""
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
        
        return {
            "type": "mutation",
            "name": name,
            "actions": actions
        }
    
    def _parse_operation(self) -> Dict[str, Any]:
        """Parse single operation"""
        # Check for alias
        alias = None
        if self.current + 1 < len(self.tokens) and self.tokens[self.current + 1] == ":":
            alias = self._consume()
            self._consume(":")
        
        # Operation name
        operation = self._consume()
        
        # Parse arguments if present
        args = {}
        if self._match("("):
            args = self._parse_arguments()
        
        # Parse selection set if present
        selections = []
        if self._match("{"):
            selections = self._parse_selection_set()
        
        return {
            "alias": alias,
            "operation": operation,
            "arguments": args,
            "selections": selections
        }
    
    def _parse_action(self) -> Dict[str, Any]:
        """Parse mutation action"""
        action_type = self._consume()
        
        args = {}
        if self._match("("):
            args = self._parse_arguments()
        
        return {
            "action": action_type,
            "arguments": args
        }
    
    def _parse_arguments(self) -> Dict[str, Any]:
        """Parse operation arguments"""
        self._consume("(")
        args = {}
        
        while not self._match(")"):
            # Argument name
            key = self._consume()
            self._consume(":")
            
            # Argument value
            value = self._parse_value()
            args[key] = value
            
            if self._match(","):
                self._consume(",")
        
        self._consume(")")
        return args
    
    def _parse_value(self) -> Any:
        """Parse argument value"""
        token = self.tokens[self.current]
        
        # String value
        if token.startswith('"') or token.startswith("'"):
            value = self._consume()
            return value[1:-1]  # Remove quotes
        
        # Number
        if token.replace('.', '').replace('-', '').isdigit():
            value = self._consume()
            return float(value) if '.' in value else int(value)
        
        # Boolean
        if token in ['true', 'false']:
            return self._consume() == 'true'
        
        # Array
        if token == '[':
            return self._parse_array()
        
        # Object
        if token == '{':
            return self._parse_object()
        
        # Identifier
        return self._consume()
    
    def _parse_array(self) -> List[Any]:
        """Parse array value"""
        self._consume("[")
        items = []
        
        while not self._match("]"):
            items.append(self._parse_value())
            if self._match(","):
                self._consume(",")
        
        self._consume("]")
        return items
    
    def _parse_object(self) -> Dict[str, Any]:
        """Parse object value"""
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
        """Parse selection set"""
        self._consume("{")
        selections = []
        
        while not self._match("}"):
            selections.append(self._parse_operation())
            if self._match(","):
                self._consume(",")
        
        self._consume("}")
        return selections
    
    def _parse_simple_instruction(self, instruction: str) -> Dict[str, Any]:
        """Parse simple text instruction into operations"""
        # Fallback for natural language instructions
        return {
            "type": "instruction",
            "text": instruction,
            "operations": self._extract_operations_from_text(instruction)
        }
    
    def _extract_operations_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract operations from natural language"""
        operations = []
        
        # Common patterns
        patterns = {
            "navigate": r'(?:go to|navigate to|open|visit)\s+(?:url\s+)?([^\s]+)',
            "click": r'click\s+(?:on\s+)?(?:the\s+)?([^,]+)',
            "fill": r'(?:fill|type|enter)\s+([^\s]+)\s+(?:with|as|=)\s+([^,]+)',
            "extract": r'(?:extract|get|find|scrape)\s+(?:all\s+)?([^,]+)',
            "wait": r'wait\s+(?:for\s+)?(\d+)\s*(?:seconds?|ms)?'
        }
        
        for op_type, pattern in patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if op_type == "navigate":
                    operations.append({
                        "operation": "navigate",
                        "arguments": {"url": match.group(1)}
                    })
                elif op_type == "click":
                    operations.append({
                        "operation": "click",
                        "arguments": {"selector": match.group(1).strip()}
                    })
                elif op_type == "fill":
                    operations.append({
                        "operation": "fill",
                        "arguments": {
                            "field": match.group(1).strip(),
                            "value": match.group(2).strip()
                        }
                    })
                elif op_type == "extract":
                    operations.append({
                        "operation": "extract",
                        "arguments": {"target": match.group(1).strip()}
                    })
                elif op_type == "wait":
                    duration = int(match.group(1))
                    operations.append({
                        "operation": "wait",
                        "arguments": {"duration": duration}
                    })
        
        return operations

class BQLExecutor:
    """Executor for parsed BQL queries"""
    
    def __init__(self, browser_context):
        self.browser = browser_context
        self.parser = BQLParser()
    
    async def execute(self, query: str) -> Dict[str, Any]:
        """Execute BQL query and return results"""
        
        # Parse query
        parsed = self.parser.parse(query)
        
        # Execute based on type
        if parsed["type"] == "query":
            return await self._execute_query(parsed)
        elif parsed["type"] == "mutation":
            return await self._execute_mutation(parsed)
        else:
            return await self._execute_instruction(parsed)
    
    async def _execute_query(self, query: Dict) -> Dict[str, Any]:
        """Execute query operations"""
        results = {}
        
        for operation in query["operations"]:
            result = await self._execute_operation(operation)
            key = operation["alias"] or operation["operation"]
            results[key] = result
        
        return {
            "data": results,
            "errors": []
        }
    
    async def _execute_mutation(self, mutation: Dict) -> Dict[str, Any]:
        """Execute mutation actions"""
        results = []
        
        for action in mutation["actions"]:
            result = await self._execute_action(action)
            results.append(result)
        
        return {
            "data": {"mutations": results},
            "errors": []
        }
    
    async def _execute_operation(self, operation: Dict) -> Any:
        """Execute single operation"""
        op_type = operation["operation"]
        args = operation["arguments"]
        
        if op_type == "page":
            # Navigate to page and extract data
            page = await self.browser.new_page()
            await page.goto(args.get("url"))
            
            # Execute selections
            if operation["selections"]:
                return await self._execute_selections(page, operation["selections"])
            else:
                return {"url": page.url, "title": await page.title()}
        
        elif op_type == "select":
            # Select elements
            selector = args.get("css") or args.get("xpath")
            elements = await self.browser.current_page.query_selector_all(selector)
            
            results = []
            for element in elements:
                if operation["selections"]:
                    result = {}
                    for selection in operation["selections"]:
                        key = selection["alias"] or selection["operation"]
                        result[key] = await self._extract_from_element(element, selection)
                    results.append(result)
                else:
                    results.append(await element.text_content())
            
            return results
        
        elif op_type == "text":
            # Extract text
            selector = args.get("css")
            if selector:
                element = await self.browser.current_page.query_selector(selector)
                return await element.text_content() if element else None
            return None
        
        elif op_type == "attr":
            # Extract attribute
            selector = args.get("css")
            attr_name = args.get("name")
            if selector:
                element = await self.browser.current_page.query_selector(selector)
                return await element.get_attribute(attr_name) if element else None
            return None
    
    async def _execute_action(self, action: Dict) -> Dict[str, Any]:
        """Execute single mutation action"""
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
        """Execute selection set on page"""
        results = {}
        
        for selection in selections:
            key = selection["alias"] or selection["operation"]
            results[key] = await self._execute_page_selection(page, selection)
        
        return results
    
    async def _execute_page_selection(self, page, selection: Dict) -> Any:
        """Execute selection on page"""
        op = selection["operation"]
        args = selection["arguments"]
        
        if op == "title":
            return await page.title()
        elif op == "url":
            return page.url
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
        """Select multiple elements and extract data"""
        selector = selection["arguments"].get("css")
        elements = await page.query_selector_all(selector)
        
        results = []
        for element in elements:
            if selection["selections"]:
                item = {}
                for sub_selection in selection["selections"]:
                    key = sub_selection["alias"] or sub_selection["operation"]
                    item[key] = await self._extract_from_element(element, sub_selection)
                results.append(item)
            else:
                results.append(await element.text_content())
        
        return results
    
    async def _extract_from_element(self, element, selection: Dict) -> Any:
        """Extract data from element"""
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
        """Execute natural language instruction"""
        results = []
        
        for operation in instruction["operations"]:
            result = await self._execute_operation(operation)
            results.append(result)
        
        return {
            "data": results,
            "instruction": instruction["text"],
            "errors": []
        }


# Example BQL Queries
EXAMPLE_QUERIES = {
    "simple_extraction": """
        query {
            page(url: "https://example.com") {
                title
                description: text(css: "meta[name='description']")
                links: select(css: "a") {
                    text
                    href: attr(name: "href")
                }
            }
        }
    """,
    
    "news_scraping": """
        query NewsArticles {
            page(url: "https://news.ycombinator.com") {
                articles: select(css: ".athing") {
                    title: text(css: ".storylink")
                    url: attr(css: ".storylink", name: "href")
                    points: text(css: ".score")
                    author: text(css: ".hnuser")
                }
            }
        }
    """,
    
    "form_automation": """
        mutation FillLoginForm {
            navigate(url: "https://example.com/login")
            wait(duration: 2000)
            fill(selector: "#username", value: "john@example.com")
            fill(selector: "#password", value: "secret123")
            click(selector: "button[type='submit']")
            wait(duration: 3000)
        }
    """,
    
    "complex_workflow": """
        mutation DownloadReport {
            navigate(url: "https://app.example.com")
            fill(selector: "#username", value: "user")
            fill(selector: "#password", value: "pass")
            click(selector: "#login-btn")
            wait(duration: 2000)
            click(selector: "a[href*='reports']")
            wait(duration: 1000)
            click(selector: ".download-pdf")
        }
    """
}

if __name__ == "__main__":
    # Test parser
    parser = BQLParser()
    
    for name, query in EXAMPLE_QUERIES.items():
        print(f"\n=== {name} ===")
        try:
            parsed = parser.parse(query)
            print(json.dumps(parsed, indent=2))
        except Exception as e:
            print(f"Error: {e}")
