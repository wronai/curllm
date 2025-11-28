"""
LLM-Based Filter Validator

Uses LLM to validate products against semantic criteria that are hard to match with regex:
- "gluten-free" - check ingredients, not just keywords
- "organic" - verify certification mentions
- "vegan" - check for animal products
- Custom queries: "suitable for diabetics", "low-sodium", etc.

LLM provides semantic understanding beyond pattern matching.
"""

import json
from typing import Dict, List, Optional, Any


class LLMFilterValidator:
    """
    LLM-based product validation
    
    Validates products against semantic criteria that require understanding:
    - Ingredient analysis
    - Dietary compliance
    - Quality attributes
    - Custom user requirements
    """
    
    def __init__(self, llm_client, run_logger=None):
        self.llm = llm_client
        self.run_logger = run_logger
    
    def _log(self, msg: str, data: Any = None):
        """Log with structured data"""
        if self.run_logger:
            # Use log_text (standard RunLogger method)
            self.run_logger.log_text(msg)
            if data and isinstance(data, dict):
                import json
                self.run_logger.log_code("json", json.dumps(data, indent=2, ensure_ascii=False))
    
    async def validate_product(
        self,
        product: Dict[str, Any],
        semantic_criteria: List[str],
        instruction: str
    ) -> Dict[str, Any]:
        """
        Validate single product against semantic criteria
        
        Args:
            product: {name, price, url, description, ...}
            semantic_criteria: ["gluten-free", "organic", ...]
            instruction: Original user instruction
        
        Returns:
            {
                "passes": True/False,
                "confidence": 0.0-1.0,
                "reasoning": "...",
                "warnings": [...],
                "criteria_check": {
                    "gluten-free": {passes: True, confidence: 0.9},
                    "organic": {passes: False, confidence: 0.8}
                }
            }
        """
        
        product_text = self._format_product_text(product)
        
        prompt = f"""You are analyzing a product to validate if it meets specific criteria.

PRODUCT:
{product_text}

USER INSTRUCTION: {instruction}

SEMANTIC CRITERIA TO VALIDATE:
{json.dumps(semantic_criteria, indent=2)}

Your task:
1. For each criterion, analyze if the product meets it
2. Consider:
   - Explicit mentions (keywords)
   - Implicit indicators (ingredients, descriptions)
   - Absence of contradictory information
3. Be conservative: if unsure, mark as not validated

Respond with JSON:
{{
  "passes": <true if ALL criteria met>,
  "confidence": <0.0-1.0 overall confidence>,
  "reasoning": "<explain your decision>",
  "criteria_check": {{
    "<criterion>": {{
      "passes": <true/false>,
      "confidence": <0.0-1.0>,
      "reasoning": "<why>"
    }}
  }},
  "warnings": ["<any concerns or missing info>"]
}}

JSON only:"""

        try:
            # Use ainvoke (SimpleOllama method)
            llm_response = await self.llm.ainvoke(prompt)
            response = llm_response.get('text', '') if isinstance(llm_response, dict) else str(llm_response)
            
            # Parse LLM response
            result = json.loads(response.strip().replace("```json", "").replace("```", ""))
            
            self._log("🧠 LLM Validation", {
                "product": product.get('name', 'Unknown'),
                "criteria": semantic_criteria,
                "passes": result.get('passes', False),
                "confidence": result.get('confidence', 0.0)
            })
            
            return result
            
        except Exception as e:
            self._log(f"⚠️ LLM validation failed: {e}")
            return {
                "error": str(e),
                "passes": False,
                "confidence": 0.0,
                "reasoning": "LLM validation failed",
                "warnings": ["Could not validate due to LLM error"]
            }
    
    async def validate_batch(
        self,
        products: List[Dict[str, Any]],
        semantic_criteria: List[str],
        instruction: str,
        max_concurrent: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Validate multiple products (batch processing)
        
        Returns list of validation results for each product.
        """
        results = []
        
        # Process in batches to avoid overwhelming LLM
        for i in range(0, len(products), max_concurrent):
            batch = products[i:i+max_concurrent]
            
            batch_results = await self._validate_batch_internal(
                batch, semantic_criteria, instruction
            )
            
            results.extend(batch_results)
        
        return results
    
    async def _validate_batch_internal(
        self,
        products: List[Dict[str, Any]],
        semantic_criteria: List[str],
        instruction: str
    ) -> List[Dict[str, Any]]:
        """Validate a small batch of products in single LLM call"""
        
        products_text = "\n\n".join([
            f"PRODUCT {i+1}:\n{self._format_product_text(p)}"
            for i, p in enumerate(products)
        ])
        
        prompt = f"""You are analyzing multiple products to validate if they meet specific criteria.

{products_text}

USER INSTRUCTION: {instruction}

SEMANTIC CRITERIA: {', '.join(semantic_criteria)}

For each product, validate if it meets ALL criteria.

Respond with JSON array:
[
  {{
    "product_index": 0,
    "passes": <true/false>,
    "confidence": <0.0-1.0>,
    "reasoning": "<brief explanation>"
  }},
  ...
]

JSON only:"""

        try:
            # Use ainvoke (SimpleOllama method)
            llm_response = await self.llm.ainvoke(prompt)
            response = llm_response.get('text', '') if isinstance(llm_response, dict) else str(llm_response)
            
            # Parse LLM response
            results = json.loads(response.strip().replace("```json", "").replace("```", ""))
            
            # Match results to products
            validated = []
            for result in results:
                idx = result.get('product_index', 0)
                if idx < len(products):
                    validated.append({
                        **result,
                        'product': products[idx]
                    })
            
            return validated
            
        except Exception as e:
            self._log(f"⚠️ Batch validation failed: {e}")
            # Return all as failed
            return [
                {
                    "product_index": i,
                    "passes": False,
                    "confidence": 0.0,
                    "reasoning": "Batch validation failed",
                    "error": str(e)
                }
                for i in range(len(products))
            ]
    
    def _format_product_text(self, product: Dict[str, Any]) -> str:
        """Format product data for LLM analysis"""
        parts = []
        
        if 'name' in product:
            parts.append(f"Name: {product['name']}")
        
        if 'price' in product:
            unit = product.get('price_unit', 'zł')
            parts.append(f"Price: {product['price']}{unit}")
        
        if 'weight' in product:
            parts.append(f"Weight: {product['weight']}{product.get('weight_unit', 'g')}")
        
        if 'volume' in product:
            parts.append(f"Volume: {product['volume']}{product.get('volume_unit', 'ml')}")
        
        if 'description' in product:
            parts.append(f"Description: {product['description']}")
        
        if 'attributes' in product:
            parts.append(f"Detected Attributes: {', '.join(product['attributes'])}")
        
        return "\n".join(parts)


# Example usage
if __name__ == "__main__":
    # Mock LLM for testing
    class MockLLM:
        async def generate(self, prompt, temperature=0.3):
            return '''
            {
              "passes": true,
              "confidence": 0.85,
              "reasoning": "Product explicitly mentions 'gluten-free' and 'organic' certifications",
              "criteria_check": {
                "gluten-free": {"passes": true, "confidence": 0.9, "reasoning": "Clearly labeled"},
                "organic": {"passes": true, "confidence": 0.8, "reasoning": "Bio certification mentioned"}
              },
              "warnings": []
            }
            '''
    
    # Test
    import asyncio
    
    async def test():
        validator = LLMFilterValidator(MockLLM())
        
        product = {
            "name": "Organic Gluten-Free Pasta 500g",
            "price": 12.99,
            "price_unit": "zł",
            "weight": 500,
            "weight_unit": "g",
            "description": "Bio certified, gluten-free pasta made from rice flour"
        }
        
        result = await validator.validate_product(
            product,
            ["gluten-free", "organic"],
            "Find gluten-free organic products"
        )
        
        print(f"Validation Result: {json.dumps(result, indent=2)}")
    
    asyncio.run(test())
