"""
Instruction Parser - Multi-Criteria Extraction

Parses user instructions to extract:
- Numeric criteria: price, weight, volume, size
- Semantic criteria: gluten-free, organic, vegan, brand
- Comparison operators: under, over, between, equals
- Logical operators: AND, OR

Examples:
- "Find products under 50zł" → {price: {op: "lt", value: 50, unit: "zł"}}
- "Find products under 500g" → {weight: {op: "lt", value: 500, unit: "g"}}
- "Find gluten-free products under 50zł" → {price: {...}, semantic: ["gluten-free"]}
- "Find products under 50zł AND under 500g" → {price: {...}, weight: {...}}
"""

import re
from typing import Dict, List, Optional, Any
from enum import Enum


class CriteriaType(Enum):
    """Types of filtering criteria"""
    PRICE = "price"
    WEIGHT = "weight"
    VOLUME = "volume"
    SIZE = "size"
    BRAND = "brand"
    SEMANTIC = "semantic"


class ComparisonOp(Enum):
    """Comparison operators"""
    LT = "less_than"
    GT = "greater_than"
    LTE = "less_than_or_equal"
    GTE = "greater_than_or_equal"
    EQ = "equals"
    BETWEEN = "between"


class InstructionParser:
    """
    Parse user instructions into structured criteria
    
    Supports:
    - Numeric filters: price, weight, volume, size
    - Semantic filters: gluten-free, organic, vegan, etc.
    - Multi-criteria: combined with AND/OR
    """
    
    def __init__(self):
        # Price patterns - support multiple currencies
        # Supported currencies: zł, PLN, $, USD, €, EUR, £, GBP
        currency_pattern = r"(zł|PLN|złotych|\$|USD|€|EUR|£|GBP)"
        
        self.price_patterns = [
            # Symbol before with capture: "$100", "€50", "£75"
            (r"(?:under|below|less than)\s*([\$€£])\s*(\d+(?:[,\.]\d+)?)", ComparisonOp.LT, True),
            (r"(?:over|above|more than)\s*([\$€£])\s*(\d+(?:[,\.]\d+)?)", ComparisonOp.GT, True),
            # Symbol/unit after: "100zł", "50 PLN", "100 USD"
            (r"(?:under|below|less than)\s*(\d+(?:[,\.]\d+)?)\s*" + currency_pattern, ComparisonOp.LT, False),
            (r"(?:over|above|more than)\s*(\d+(?:[,\.]\d+)?)\s*" + currency_pattern, ComparisonOp.GT, False),
            (r"between\s*(\d+(?:[,\.]\d+)?)\s*(?:and|to|-)\s*(\d+(?:[,\.]\d+)?)\s*" + currency_pattern, ComparisonOp.BETWEEN, False),
            # "under price 100 zł" or "price under 100 zł" patterns
            (r"(?:under|below|less than)\s+(?:price|cena)\s+(\d+(?:[,\.]\d+)?)\s*" + currency_pattern, ComparisonOp.LT, False),
            (r"(?:over|above|more than)\s+(?:price|cena)\s+(\d+(?:[,\.]\d+)?)\s*" + currency_pattern, ComparisonOp.GT, False),
            # Simple number with price context: "price under 100", "under 100", "below 50"
            (r"(?:price|cena)\s+(?:under|below|less than|<)\s*(\d+(?:[,\.]\d+)?)", ComparisonOp.LT, False),
            (r"(?:under|below|less than|<)\s+(?:price|cena)?\s*(\d+(?:[,\.]\d+)?)", ComparisonOp.LT, False),
            (r"(?:price|cena)\s+(?:over|above|more than|>)\s*(\d+(?:[,\.]\d+)?)", ComparisonOp.GT, False),
            (r"(?:over|above|more than|>)\s+(?:price|cena)?\s*(\d+(?:[,\.]\d+)?)", ComparisonOp.GT, False),
        ]
        
        # Weight patterns
        self.weight_patterns = [
            (r"(?:under|below|less than)\s*(\d+(?:[,\.]\d+)?)\s*(g|kg|gram|kilogram)", ComparisonOp.LT),
            (r"(?:over|above|more than)\s*(\d+(?:[,\.]\d+)?)\s*(g|kg|gram|kilogram)", ComparisonOp.GT),
            (r"between\s*(\d+(?:[,\.]\d+)?)\s*(?:and|to|-)\s*(\d+(?:[,\.]\d+)?)\s*(g|kg)", ComparisonOp.BETWEEN),
        ]
        
        # Volume patterns
        self.volume_patterns = [
            (r"(?:under|below|less than)\s*(\d+(?:[,\.]\d+)?)\s*(ml|l|liter)", ComparisonOp.LT),
            (r"(?:over|above|more than)\s*(\d+(?:[,\.]\d+)?)\s*(ml|l|liter)", ComparisonOp.GT),
        ]
        
        # Semantic keywords
        self.semantic_keywords = {
            'dietary': ['gluten-free', 'lactose-free', 'vegan', 'vegetarian', 'organic', 'bio'],
            'quality': ['premium', 'luxury', 'budget', 'eco-friendly', 'sustainable'],
            'attributes': ['fresh', 'frozen', 'dried', 'canned', 'packaged']
        }
    
    def parse(self, instruction: str) -> Dict[str, Any]:
        """
        Parse instruction into structured criteria
        
        Returns:
            {
                "criteria": {
                    "price": {op: "lt", value: 50, unit: "zł"},
                    "weight": {op: "lt", value: 500, unit: "g"},
                    "semantic": ["gluten-free", "organic"]
                },
                "logical_op": "AND",  # AND/OR between criteria
                "original": "Find gluten-free products under 50zł"
            }
        """
        instruction_lower = instruction.lower()
        
        criteria = {}
        
        # Parse price
        price_criteria = self._parse_numeric_criteria(
            instruction_lower, 
            self.price_patterns,
            CriteriaType.PRICE
        )
        if price_criteria:
            criteria['price'] = price_criteria
        
        # Parse weight
        weight_criteria = self._parse_numeric_criteria(
            instruction_lower,
            self.weight_patterns,
            CriteriaType.WEIGHT
        )
        if weight_criteria:
            criteria['weight'] = weight_criteria
        
        # Parse volume
        volume_criteria = self._parse_numeric_criteria(
            instruction_lower,
            self.volume_patterns,
            CriteriaType.VOLUME
        )
        if volume_criteria:
            criteria['volume'] = volume_criteria
        
        # Parse semantic keywords
        semantic = self._parse_semantic(instruction_lower)
        if semantic:
            criteria['semantic'] = semantic
        
        # Detect logical operator
        logical_op = "AND" if " and " in instruction_lower else "OR" if " or " in instruction_lower else "AND"
        
        return {
            "criteria": criteria,
            "logical_op": logical_op,
            "original": instruction,
            "has_filters": len(criteria) > 0
        }
    
    def _parse_numeric_criteria(
        self,
        text: str,
        patterns: List,
        criteria_type: CriteriaType
    ) -> Optional[Dict]:
        """Parse numeric criteria (price, weight, volume)"""
        
        for pattern_tuple in patterns:
            # Handle both 2-tuple (pattern, op) and 3-tuple (pattern, op, symbol_first)
            if len(pattern_tuple) == 3:
                pattern, op, symbol_first = pattern_tuple
            else:
                pattern, op = pattern_tuple
                symbol_first = False
            
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if op == ComparisonOp.BETWEEN:
                    # Between has 3 groups: min, max, unit
                    return {
                        "type": criteria_type.value,
                        "operator": op.value,
                        "min": float(match.group(1).replace(',', '.')),
                        "max": float(match.group(2).replace(',', '.')),
                        "unit": match.group(3)
                    }
                else:
                    # Under/Over - handle symbol_first patterns differently
                    if symbol_first:
                        # Pattern: "$100" - group(1) is symbol, group(2) is value
                        unit = match.group(1)
                        value = float(match.group(2).replace(',', '.'))
                    else:
                        # Pattern: "100zł" - group(1) is value, optional group(2) is unit
                        value = float(match.group(1).replace(',', '.'))
                        try:
                            unit = match.group(2) if match.lastindex >= 2 else None
                        except IndexError:
                            unit = None
                    
                    # Default unit for price if not specified
                    if unit is None and criteria_type == CriteriaType.PRICE:
                        unit = "unknown"  # Will be handled by currency translator
                    
                    # Normalize currency units
                    if unit in ['kg', 'kilogram']:
                        value *= 1000
                        unit = 'g'
                    elif unit in ['l', 'liter']:
                        value *= 1000
                        unit = 'ml'
                    elif unit in ['$', 'USD']:
                        unit = 'USD'
                    elif unit in ['€', 'EUR']:
                        unit = 'EUR'
                    elif unit in ['£', 'GBP']:
                        unit = 'GBP'
                    elif unit in ['zł', 'PLN', 'złotych']:
                        unit = 'PLN'
                    
                    return {
                        "type": criteria_type.value,
                        "operator": op.value,
                        "value": value,
                        "unit": unit
                    }
        
        return None
    
    def _parse_semantic(self, text: str) -> List[str]:
        """Parse semantic keywords"""
        found = []
        
        for category, keywords in self.semantic_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    found.append(keyword)
        
        return found
    
    def format_criteria_summary(self, parsed: Dict) -> str:
        """Generate human-readable summary of criteria"""
        if not parsed['has_filters']:
            return "No specific filters detected"
        
        parts = []
        criteria = parsed['criteria']
        
        if 'price' in criteria:
            p = criteria['price']
            if p['operator'] == 'less_than':
                parts.append(f"Price < {p['value']}{p['unit']}")
            elif p['operator'] == 'greater_than':
                parts.append(f"Price > {p['value']}{p['unit']}")
            elif p['operator'] == 'between':
                parts.append(f"Price: {p['min']}-{p['max']}{p['unit']}")
        
        if 'weight' in criteria:
            w = criteria['weight']
            if w['operator'] == 'less_than':
                parts.append(f"Weight < {w['value']}{w['unit']}")
            elif w['operator'] == 'greater_than':
                parts.append(f"Weight > {w['value']}{w['unit']}")
        
        if 'volume' in criteria:
            v = criteria['volume']
            if v['operator'] == 'less_than':
                parts.append(f"Volume < {v['value']}{v['unit']}")
        
        if 'semantic' in criteria:
            parts.append(f"Keywords: {', '.join(criteria['semantic'])}")
        
        op = parsed['logical_op']
        return f" {op} ".join(parts)


# Example usage
if __name__ == "__main__":
    parser = InstructionParser()
    
    examples = [
        "Find all products under 50zł",
        "Find products under 500g",
        "Find gluten-free products under 50zł",
        "Find products under 50zł AND under 500g",
        "Find organic vegan products between 20 and 50 złotych",
        "Find products over 1kg",
    ]
    
    for example in examples:
        parsed = parser.parse(example)
        summary = parser.format_criteria_summary(parsed)
        print(f"\nInstruction: {example}")
        print(f"Summary: {summary}")
        print(f"Criteria: {parsed['criteria']}")
