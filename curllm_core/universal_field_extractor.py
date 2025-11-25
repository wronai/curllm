"""
Universal Field Extractor

Extracts various fields from product text:
- Price: 49.99 zł, 50 PLN, 49,99 złotych
- Weight: 500g, 1kg, 250 gram
- Volume: 500ml, 1l, 1.5 liter
- Dimensions: 15x20cm, 10" screen
- Attributes: gluten-free, organic, vegan (from text)

Uses regex patterns + normalization to standard units.
"""

import re
from typing import Dict, Optional, Any, List


class UniversalFieldExtractor:
    """
    Extract structured data from product text
    
    Handles:
    - Numeric fields: price, weight, volume, dimensions
    - Text fields: brand, attributes
    - Boolean fields: has_gluten_free, has_organic
    """
    
    def __init__(self):
        # Price patterns (multiple currencies)
        self.price_patterns = [
            r'(\d+[,\.\s]?\d*)\s*(?:zł|PLN|złotych)',
            r'(\d+[,\.\s]?\d*)\s*(?:€|EUR|euro)',
            r'(?:\$|USD)\s*(\d+[,\.\s]?\d*)',
        ]
        
        # Weight patterns
        self.weight_patterns = [
            r'(\d+[,\.\s]?\d*)\s*(?:kg|kilogram)',      # kg
            r'(\d+[,\.\s]?\d*)\s*(?:g|gram|gramów)',    # g
            r'(\d+[,\.\s]?\d*)\s*(?:mg|miligram)',      # mg
        ]
        
        # Volume patterns
        self.volume_patterns = [
            r'(\d+[,\.\s]?\d*)\s*(?:l|liter|litr)',     # liters
            r'(\d+[,\.\s]?\d*)\s*(?:ml|mililiter)',     # ml
        ]
        
        # Dimension patterns
        self.dimension_patterns = [
            r'(\d+)\s*x\s*(\d+)\s*(?:cm|mm|m)?',        # 15x20cm
            r'(\d+(?:[,\.]\d+)?)\s*(?:"|inch|cale)',    # 15" screen
        ]
        
        # Semantic attributes
        self.semantic_attributes = {
            'dietary': {
                'gluten-free': r'(?:gluten[- ]?free|bezglutenow)',
                'lactose-free': r'(?:lactose[- ]?free|bez laktozy)',
                'vegan': r'vegan|wegańsk',
                'vegetarian': r'vegetarian|wegetariańsk',
                'organic': r'(?:organic|bio|ekologiczn)',
            },
            'quality': {
                'premium': r'premium|luksusow',
                'eco-friendly': r'(?:eco[- ]?friendly|ekologiczn)',
                'sustainable': r'sustainable|zrównoważon',
            }
        }
    
    def extract_all(self, text: str) -> Dict[str, Any]:
        """
        Extract all fields from text
        
        Returns:
            {
                "price": 49.99,
                "price_unit": "zł",
                "weight": 500,
                "weight_unit": "g",
                "volume": 1000,
                "volume_unit": "ml",
                "attributes": ["gluten-free", "organic"],
                "raw_text": "..."
            }
        """
        result = {
            "raw_text": text
        }
        
        # Extract price
        price = self.extract_price(text)
        if price:
            result.update(price)
        
        # Extract weight
        weight = self.extract_weight(text)
        if weight:
            result.update(weight)
        
        # Extract volume
        volume = self.extract_volume(text)
        if volume:
            result.update(volume)
        
        # Extract attributes
        attributes = self.extract_attributes(text)
        if attributes:
            result['attributes'] = attributes
        
        return result
    
    def extract_price(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract price from text
        
        Examples:
            "49.99 zł" → {price: 49.99, price_unit: "zł"}
            "50 PLN" → {price: 50.0, price_unit: "PLN"}
        """
        for pattern in self.price_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value_str = match.group(1).replace(',', '.').replace(' ', '')
                try:
                    value = float(value_str)
                    
                    # Detect unit from pattern
                    if 'zł' in match.group(0).lower():
                        unit = 'zł'
                    elif 'eur' in match.group(0).lower() or '€' in match.group(0):
                        unit = '€'
                    elif 'usd' in match.group(0).lower() or '$' in match.group(0):
                        unit = '$'
                    else:
                        unit = 'zł'  # default
                    
                    return {
                        'price': value,
                        'price_unit': unit,
                        'price_raw': match.group(0)
                    }
                except ValueError:
                    continue
        
        return None
    
    def extract_weight(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract weight from text, normalize to grams
        
        Examples:
            "500g" → {weight: 500, weight_unit: "g"}
            "1kg" → {weight: 1000, weight_unit: "g"}
            "250 gram" → {weight: 250, weight_unit: "g"}
        """
        for pattern in self.weight_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value_str = match.group(1).replace(',', '.').replace(' ', '')
                try:
                    value = float(value_str)
                    
                    # Normalize to grams
                    if 'kg' in match.group(0).lower():
                        value *= 1000
                    elif 'mg' in match.group(0).lower():
                        value /= 1000
                    
                    return {
                        'weight': value,
                        'weight_unit': 'g',
                        'weight_raw': match.group(0)
                    }
                except ValueError:
                    continue
        
        return None
    
    def extract_volume(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract volume from text, normalize to ml
        
        Examples:
            "500ml" → {volume: 500, volume_unit: "ml"}
            "1l" → {volume: 1000, volume_unit: "ml"}
        """
        for pattern in self.volume_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value_str = match.group(1).replace(',', '.').replace(' ', '')
                try:
                    value = float(value_str)
                    
                    # Normalize to ml
                    if 'l' in match.group(0).lower() and 'ml' not in match.group(0).lower():
                        value *= 1000
                    
                    return {
                        'volume': value,
                        'volume_unit': 'ml',
                        'volume_raw': match.group(0)
                    }
                except ValueError:
                    continue
        
        return None
    
    def extract_attributes(self, text: str) -> List[str]:
        """
        Extract semantic attributes from text
        
        Examples:
            "Gluten-free organic pasta" → ["gluten-free", "organic"]
        """
        found = []
        text_lower = text.lower()
        
        for category, patterns in self.semantic_attributes.items():
            for attr_name, pattern in patterns.items():
                if re.search(pattern, text_lower):
                    found.append(attr_name)
        
        return list(set(found))  # Remove duplicates
    
    def matches_criteria(
        self,
        extracted: Dict[str, Any],
        criteria: Dict[str, Any]
    ) -> tuple[bool, List[str]]:
        """
        Check if extracted data matches criteria
        
        Args:
            extracted: Result from extract_all()
            criteria: From InstructionParser
        
        Returns:
            (matches: bool, reasons: List[str])
        """
        matches = True
        reasons = []
        
        # Check price
        if 'price' in criteria:
            price_crit = criteria['price']
            if 'price' not in extracted:
                matches = False
                reasons.append("No price found in product")
            else:
                price = extracted['price']
                op = price_crit['operator']
                
                if op == 'less_than' and price >= price_crit['value']:
                    matches = False
                    reasons.append(f"Price {price}{extracted['price_unit']} >= {price_crit['value']}{price_crit['unit']}")
                elif op == 'greater_than' and price <= price_crit['value']:
                    matches = False
                    reasons.append(f"Price {price}{extracted['price_unit']} <= {price_crit['value']}{price_crit['unit']}")
                elif op == 'between' and not (price_crit['min'] <= price <= price_crit['max']):
                    matches = False
                    reasons.append(f"Price {price} not in range {price_crit['min']}-{price_crit['max']}")
        
        # Check weight
        if 'weight' in criteria:
            weight_crit = criteria['weight']
            if 'weight' not in extracted:
                matches = False
                reasons.append("No weight found in product")
            else:
                weight = extracted['weight']
                op = weight_crit['operator']
                
                if op == 'less_than' and weight >= weight_crit['value']:
                    matches = False
                    reasons.append(f"Weight {weight}g >= {weight_crit['value']}{weight_crit['unit']}")
                elif op == 'greater_than' and weight <= weight_crit['value']:
                    matches = False
                    reasons.append(f"Weight {weight}g <= {weight_crit['value']}{weight_crit['unit']}")
        
        # Check volume
        if 'volume' in criteria:
            volume_crit = criteria['volume']
            if 'volume' not in extracted:
                matches = False
                reasons.append("No volume found in product")
            else:
                volume = extracted['volume']
                op = volume_crit['operator']
                
                if op == 'less_than' and volume >= volume_crit['value']:
                    matches = False
                    reasons.append(f"Volume {volume}ml >= {volume_crit['value']}{volume_crit['unit']}")
        
        # Check semantic attributes
        if 'semantic' in criteria:
            required_attrs = set(criteria['semantic'])
            product_attrs = set(extracted.get('attributes', []))
            
            missing = required_attrs - product_attrs
            if missing:
                matches = False
                reasons.append(f"Missing attributes: {', '.join(missing)}")
        
        return matches, reasons


# Example usage
if __name__ == "__main__":
    extractor = UniversalFieldExtractor()
    
    examples = [
        "Pasta gluten-free organic 500g - 12.99 zł",
        "Mleko bez laktozy 1l - 8.50 PLN",
        "Sok pomarańczowy 250ml - 5.99 zł",
        "Ekologiczna kawa 1kg - 45.00 zł",
    ]
    
    for text in examples:
        result = extractor.extract_all(text)
        print(f"\nText: {text}")
        print(f"Extracted: {result}")
