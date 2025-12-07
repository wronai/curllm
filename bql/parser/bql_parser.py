"""BQL Parser - Browser Query Language Parser"""

import re
from typing import Dict, List, Any


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
