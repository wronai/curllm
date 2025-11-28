"""
BQL Executor - Executes parsed BQL queries.

Runs browser operations based on parsed BQL AST.
"""
from typing import Dict, List, Any
from .parser import BQLParser


class BQLExecutor:
    """
    Executes BQL queries against a browser context.
    
    Supports:
    - Query operations (extract data)
    - Mutation operations (perform actions)
    - Natural language instructions
    """
    
    def __init__(self, browser_context):
        """
        Initialize executor with browser context.
        
        Args:
            browser_context: Playwright browser context or similar
        """
        self.browser = browser_context
        self.parser = BQLParser()

    async def execute(self, query: str) -> Dict[str, Any]:
        """
        Execute a BQL query.
        
        Args:
            query: BQL query string
            
        Returns:
            Execution result with data and errors
        """
        parsed = self.parser.parse(query)
        
        if parsed["type"] == "query":
            return await self._execute_query(parsed)
        elif parsed["type"] == "mutation":
            return await self._execute_mutation(parsed)
        else:
            return await self._execute_instruction(parsed)

    async def _execute_query(self, query: Dict) -> Dict[str, Any]:
        """Execute a query block."""
        results = {}
        for operation in query["operations"]:
            result = await self._execute_operation(operation)
            key = operation["alias"] or operation["operation"]
            results[key] = result
        return {"data": results, "errors": []}

    async def _execute_mutation(self, mutation: Dict) -> Dict[str, Any]:
        """Execute a mutation block."""
        results = []
        for action in mutation["actions"]:
            result = await self._execute_action(action)
            results.append(result)
        return {"data": {"mutations": results}, "errors": []}

    async def _execute_operation(self, operation: Dict) -> Any:
        """Execute a single operation."""
        op_type = operation["operation"]
        args = operation["arguments"]
        
        if op_type == "page":
            page = await self.browser.new_page()
            await page.goto(args.get("url"))
            if operation["selections"]:
                return await self._execute_selections(page, operation["selections"])
            else:
                return {
                    "url": await page.evaluate("() => window.location.href"),
                    "title": await page.title()
                }
                
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
            
        return None

    async def _execute_action(self, action: Dict) -> Dict[str, Any]:
        """Execute a single action."""
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
        """Execute selections on a page."""
        results: Dict[str, Any] = {}
        for selection in selections:
            key = selection["alias"] or selection["operation"]
            results[key] = await self._execute_page_selection(page, selection)
        return results

    async def _execute_page_selection(self, page, selection: Dict) -> Any:
        """Execute a selection on a page."""
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
            return await page.text_content()
        elif op == "select":
            return await self._select_elements(page, selection)
            
        return None

    async def _select_elements(self, page, selection: Dict) -> List[Dict]:
        """Select elements from page."""
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
                text = await element.text_content()
                results.append({"text": text})
                
        return results

    async def _extract_from_element(self, element, selection: Dict) -> Any:
        """Extract data from an element."""
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
        """Execute natural language instruction."""
        results: List[Any] = []
        for operation in instruction["operations"]:
            result = await self._execute_operation(operation)
            results.append(result)
        return {
            "data": results,
            "instruction": instruction["text"],
            "errors": []
        }
