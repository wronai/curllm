"""
Multi-Criteria Filtering Layer

Complete filtering orchestration that combines:
1. InstructionParser - parse user criteria
2. CurrencyTranslator - currency conversion for price filters
3. UniversalFieldExtractor - extract fields from products
4. LLMFilterValidator - LLM validation for semantic criteria
5. Multi-stage filtering with transparency

Supports:
- Numeric filters: price, weight, volume (regex-based, fast)
- Currency translation: "$100" → "~405 zł" for Polish sites
- Semantic filters: gluten-free, organic, vegan (LLM-based, accurate)
- Combined filters: "under 50zł AND gluten-free" (both methods)
- Fallback strategies: if LLM fails, use regex only

Complete transparency: logs all decisions, filtering stages, reasons.
"""

from typing import Dict, List, Optional, Any
import json
from .instruction_parser import InstructionParser
from .universal_field_extractor import UniversalFieldExtractor
from .llm_filter_validator import LLMFilterValidator

# Currency translation support
try:
    from .streamware.components.currency import CurrencyTranslator, normalize_price_filter
    CURRENCY_SUPPORT = True
except ImportError:
    CURRENCY_SUPPORT = False


class FilterStage:
    """Single filtering stage result"""
    def __init__(self, name: str):
        self.name = name
        self.input_count = 0
        self.output_count = 0
        self.filtered_count = 0
        self.reasons = []
        self.duration_ms = 0
    
    def to_dict(self) -> Dict:
        return {
            "stage": self.name,
            "input": self.input_count,
            "output": self.output_count,
            "filtered": self.filtered_count,
            "reasons": self.reasons,
            "duration_ms": self.duration_ms
        }


class MultiCriteriaFilter:
    """
    Complete multi-criteria filtering orchestration
    
    Architecture:
    1. Parse instruction → criteria
    2. Stage 1: Numeric filtering (fast, regex-based)
       - Filter by price, weight, volume
       - Log each filter stage
    3. Stage 2: Semantic filtering (LLM-based)
       - Validate gluten-free, organic, vegan
       - Only if semantic criteria present
    4. Generate transparency report
    """
    
    def __init__(self, llm_client=None, run_logger=None, page=None):
        self.instruction_parser = InstructionParser()
        self.field_extractor = UniversalFieldExtractor()
        self.llm_validator = LLMFilterValidator(llm_client, run_logger) if llm_client else None
        self.run_logger = run_logger
        self.page = page  # For currency detection
        self.stages = []
        
        # Currency translator
        self.currency_translator = CurrencyTranslator(llm_client, run_logger) if CURRENCY_SUPPORT else None
    
    def _log(self, msg: str, data: Any = None):
        """Log with structured data"""
        if self.run_logger:
            # Use log_text (standard RunLogger method)
            self.run_logger.log_text(msg)
            if data and isinstance(data, dict):
                import json
                self.run_logger.log_code("json", json.dumps(data, indent=2, ensure_ascii=False))
    
    async def filter_products(
        self,
        products: List[Dict[str, Any]],
        instruction: str,
        use_llm: bool = True
    ) -> Dict[str, Any]:
        """
        Filter products using multi-criteria approach
        
        Args:
            products: List of products from extraction
            instruction: User's original instruction
            use_llm: Whether to use LLM for semantic validation
        
        Returns:
            {
                "filtered_products": [...],
                "original_count": N,
                "filtered_count": M,
                "stages": [...],
                "criteria": {...},
                "transparency": {...}
            }
        """
        self.stages = []
        
        # Parse instruction first to get price criteria
        parsed_criteria = self.instruction_parser.parse(instruction)
        criteria = parsed_criteria['criteria']
        
        # Currency translation stage - convert foreign currencies to page currency
        if CURRENCY_SUPPORT and criteria.get('price'):
            price_criteria = criteria['price']
            source_currency = price_criteria.get('unit', 'unknown')
            
            # Detect target currency from page or URL
            target_currency = 'PLN'  # Default for Polish sites
            if self.page:
                try:
                    url = await self.page.url() if hasattr(self.page, 'url') else str(self.page)
                    if '.pl' in str(url):
                        target_currency = 'PLN'
                    elif '.de' in str(url) or '.fr' in str(url):
                        target_currency = 'EUR'
                    elif '.uk' in str(url):
                        target_currency = 'GBP'
                except:
                    pass
            
            # Convert if currencies differ
            if source_currency and source_currency != target_currency and source_currency != 'unknown':
                try:
                    from .streamware.components.currency import convert_price
                    
                    if price_criteria.get('value'):
                        original = price_criteria['value']
                        converted = convert_price(original, source_currency, target_currency)
                        
                        self._log("💱 Currency Translation", {
                            "original": f"{original} {source_currency}",
                            "converted": f"{converted:.0f} {target_currency}"
                        })
                        
                        # Update criteria with converted value
                        if price_criteria.get('operator') == 'less_than':
                            criteria['price'] = {'max': converted, 'unit': target_currency}
                        elif price_criteria.get('operator') == 'greater_than':
                            criteria['price'] = {'min': converted, 'unit': target_currency}
                        else:
                            criteria['price']['value'] = converted
                            criteria['price']['unit'] = target_currency
                        
                        parsed_criteria['has_filters'] = True
                except Exception as e:
                    self._log(f"⚠️ Currency conversion failed: {e}")
        
        self._log("📋 Parsed Criteria", {
            "summary": self.instruction_parser.format_criteria_summary(parsed_criteria),
            "criteria": criteria
        })
        
        if not parsed_criteria['has_filters']:
            self._log("⚠️ No specific filters detected in instruction")
            return {
                "filtered_products": products,
                "original_count": len(products),
                "filtered_count": len(products),
                "stages": [],
                "criteria": {},
                "message": "No filters applied"
            }
        
        # Start filtering pipeline
        current_products = products
        
        # Stage 1: Extract fields from all products
        stage_extract = FilterStage("field_extraction")
        stage_extract.input_count = len(current_products)
        
        enriched_products = []
        for product in current_products:
            # Combine product text for extraction
            product_text = " ".join([
                str(product.get('name', '')),
                str(product.get('description', '')),
                str(product.get('price', ''))
            ])
            
            # Extract all fields
            extracted = self.field_extractor.extract_all(product_text)
            
            # Merge with original product
            enriched = {**product, **extracted}
            enriched_products.append(enriched)
        
        stage_extract.output_count = len(enriched_products)
        self.stages.append(stage_extract)
        
        current_products = enriched_products
        
        # Stage 2: Numeric filtering (price, weight, volume)
        has_numeric = any(k in criteria for k in ['price', 'weight', 'volume'])
        
        if has_numeric:
            stage_numeric = FilterStage("numeric_filtering")
            stage_numeric.input_count = len(current_products)
            
            filtered_numeric = []
            for product in current_products:
                matches, reasons = self.field_extractor.matches_criteria(product, criteria)
                
                if matches:
                    filtered_numeric.append(product)
                else:
                    stage_numeric.reasons.extend(reasons)
            
            stage_numeric.output_count = len(filtered_numeric)
            stage_numeric.filtered_count = stage_numeric.input_count - stage_numeric.output_count
            self.stages.append(stage_numeric)
            
            self._log(f"🔢 Numeric Filter", {
                "input": stage_numeric.input_count,
                "output": stage_numeric.output_count,
                "filtered": stage_numeric.filtered_count
            })
            
            current_products = filtered_numeric
        
        # Stage 3: Semantic filtering (LLM-based)
        has_semantic = 'semantic' in criteria and len(criteria['semantic']) > 0
        
        if has_semantic and use_llm and self.llm_validator:
            stage_semantic = FilterStage("semantic_filtering_llm")
            stage_semantic.input_count = len(current_products)
            
            semantic_criteria = criteria['semantic']
            
            self._log(f"🧠 LLM Semantic Validation", {
                "criteria": semantic_criteria,
                "products_to_validate": len(current_products)
            })
            
            # Validate with LLM
            validated = []
            for product in current_products:
                validation = await self.llm_validator.validate_product(
                    product,
                    semantic_criteria,
                    instruction
                )
                
                if validation.get('passes', False):
                    product['llm_validation'] = validation
                    validated.append(product)
                else:
                    stage_semantic.reasons.append(
                        f"{product.get('name', 'Unknown')}: {validation.get('reasoning', 'Failed')}"
                    )
            
            stage_semantic.output_count = len(validated)
            stage_semantic.filtered_count = stage_semantic.input_count - stage_semantic.output_count
            self.stages.append(stage_semantic)
            
            self._log(f"✅ LLM Validation Complete", {
                "passed": stage_semantic.output_count,
                "filtered": stage_semantic.filtered_count
            })
            
            current_products = validated
        
        elif has_semantic and not use_llm:
            # Fallback: regex-based semantic filtering
            stage_semantic_regex = FilterStage("semantic_filtering_regex")
            stage_semantic_regex.input_count = len(current_products)
            
            semantic_criteria = set(criteria['semantic'])
            
            filtered_semantic = []
            for product in current_products:
                product_attrs = set(product.get('attributes', []))
                
                # Check if all required attributes present
                if semantic_criteria.issubset(product_attrs):
                    filtered_semantic.append(product)
                else:
                    missing = semantic_criteria - product_attrs
                    stage_semantic_regex.reasons.append(
                        f"{product.get('name', 'Unknown')}: Missing {', '.join(missing)}"
                    )
            
            stage_semantic_regex.output_count = len(filtered_semantic)
            stage_semantic_regex.filtered_count = stage_semantic_regex.input_count - stage_semantic_regex.output_count
            self.stages.append(stage_semantic_regex)
            
            self._log(f"⚠️ Regex Semantic Filter (LLM disabled)", {
                "passed": stage_semantic_regex.output_count,
                "filtered": stage_semantic_regex.filtered_count
            })
            
            current_products = filtered_semantic
        
        # Generate result
        result = {
            "filtered_products": current_products,
            "original_count": len(products),
            "filtered_count": len(current_products),
            "stages": [s.to_dict() for s in self.stages],
            "criteria": criteria,
            "criteria_summary": self.instruction_parser.format_criteria_summary(parsed_criteria),
            "transparency": self._generate_transparency()
        }
        
        self._log("✅ Multi-Criteria Filtering Complete", {
            "original": result['original_count'],
            "filtered": result['filtered_count'],
            "stages": len(self.stages)
        })
        
        return result
    
    def _generate_transparency(self) -> Dict[str, Any]:
        """Generate transparency report"""
        return {
            "total_stages": len(self.stages),
            "filter_cascade": [
                {
                    "stage": s.name,
                    "kept": s.output_count,
                    "removed": s.filtered_count
                }
                for s in self.stages
            ],
            "reasons_summary": {
                s.name: s.reasons[:5]  # Top 5 reasons per stage
                for s in self.stages
                if s.reasons
            }
        }
    
    def print_filtering_report(self, result: Dict[str, Any]):
        """Print human-readable filtering report"""
        print("\n" + "="*60)
        print("🎯 MULTI-CRITERIA FILTERING REPORT")
        print("="*60)
        
        print(f"\n📝 Criteria: {result['criteria_summary']}")
        print(f"📦 Original Products: {result['original_count']}")
        print(f"✅ Filtered Products: {result['filtered_count']}")
        print(f"❌ Removed: {result['original_count'] - result['filtered_count']}")
        
        print(f"\n📊 FILTERING PIPELINE ({len(result['stages'])} stages):")
        for stage in result['stages']:
            print(f"\n  {stage['stage'].upper()}")
            print(f"    Input: {stage['input']}")
            print(f"    Output: {stage['output']}")
            print(f"    Filtered: {stage['filtered']}")
            
            if stage['reasons']:
                print(f"    Reasons (sample):")
                for reason in stage['reasons'][:3]:
                    print(f"      - {reason}")
        
        print("\n" + "="*60 + "\n")
