"""
BQL Parser - Browser Query Language Parser

Parses GraphQL-like queries for browser automation.
"""
import re
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from enum import Enum


class QueryType(Enum):
    """Supported BQL operation types"""
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
    """Represents a node in the BQL AST"""
    type: QueryType
    selector: Optional[str] = None
    attributes: Dict[str, Any] = None
    children: List['BQLNode'] = None

    def __post_init__(self):
        self.attributes = self.attributes or {}
        self.children = self.children or []


class BQLParser:
    """
    Parser for Browser Query Language.
    
    Supports:
    - GraphQL-like query syntax
    - Mutation blocks for actions
    - Natural language instructions
    """
    
    def __init__(self):
        self.tokens = []
        self.current = 0

    def parse(self, query: str) -> Dict[str, Any]:
        """
        Parse a BQL query string.
        
        Args:
            query: BQL query string
            
        Returns:
            Parsed query as dictionary
        """
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
        """Remove comments and normalize whitespace."""
        query = re.sub(r'#.*?\n', '\n', query)
        query = re.sub(r'\s+', ' ', query)
        return query.strip()

    def _tokenize(self, query: str) -> List[str]:
        """Tokenize query string."""
        pattern = r'(\w+|{|}|\(|\)|:|,|"[^"]*"|\'[^\']*\'|\[|\]|=)'
        tokens = re.findall(pattern, query)
        return [t.strip() for t in tokens if t.strip()]

    def _match(self, *expected: str) -> bool:
        """Check if current token matches expected."""
        if self.current < len(self.tokens):
            return self.tokens[self.current] in expected
        return False

    def _consume(self, expected: str = None) -> str:
        """Consume and return current token."""
        if self.current >= len(self.tokens):
            raise SyntaxError("Unexpected end of query")
        token = self.tokens[self.current]
        if expected and token != expected:
            raise SyntaxError(f"Expected '{expected}', got '{token}'")
        self.current += 1
        return token

    def _parse_query_block(self) -> Dict[str, Any]:
        """Parse a query block."""
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
        """Parse a mutation block."""
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
        """Parse an operation."""
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
        return {
            "alias": alias,
            "operation": operation,
            "arguments": args,
            "selections": selections
        }

    def _parse_action(self) -> Dict[str, Any]:
        """Parse an action."""
        action_type = self._consume()
        args = {}
        if self._match("("):
            args = self._parse_arguments()
        return {"action": action_type, "arguments": args}

    def _parse_arguments(self) -> Dict[str, Any]:
        """Parse arguments block."""
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
        """Parse a value."""
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
        """Parse an array."""
        self._consume("[")
        items = []
        while not self._match("]"):
            items.append(self._parse_value())
            if self._match(","):
                self._consume(",")
        self._consume("]")
        return items

    def _parse_object(self) -> Dict[str, Any]:
        """Parse an object."""
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
        """Parse a selection set."""
        self._consume("{")
        selections = []
        while not self._match("}"):
            selections.append(self._parse_operation())
            if self._match(","):
                self._consume(",")
        self._consume("}")
        return selections

    def _parse_simple_instruction(self, instruction: str) -> Dict[str, Any]:
        """Parse natural language instruction."""
        return {
            "type": "instruction",
            "text": instruction,
            "operations": self._extract_operations_from_text(instruction)
        }

    def _extract_operations_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract operations from natural language text."""
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
