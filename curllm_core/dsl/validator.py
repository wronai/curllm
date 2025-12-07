"""
Result Validator - LLM-Based Validation of Extraction Results

Validates:
1. JSON structure matches expected format
2. Data makes sense for the instruction
3. Values are reasonable (prices, names, etc.)
4. Completeness (required fields present)

Uses minimal LLM context (< 500 chars) for validation.
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of validation."""
    
    valid: bool
    score: float  # 0.0 - 1.0
    issues: List[str]
    suggestions: List[str]
    corrected_data: Optional[Any] = None
    llm_reasoning: str = ""


class ResultValidator:
    """
    Validate and optionally correct extraction results.
    
    Two-phase validation:
    1. Deterministic checks (format, types, required fields)
    2. LLM semantic check (does it match instruction?)
    """
    
    def __init__(self, llm_client=None):
        self.llm = llm_client
    
    # =========================================================================
    # DETERMINISTIC VALIDATION (No LLM)
    # =========================================================================
    
    def validate_structure(
        self, 
        data: Any, 
        expected_fields: List[str] = None,
        min_items: int = 1
    ) -> ValidationResult:
        """
        Validate data structure without LLM.
        
        Checks:
        - Is it a list or dict?
        - Has required fields?
        - Minimum item count?
        """
        issues = []
        suggestions = []
        score = 1.0
        
        # Check type
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            # Try to extract list from common keys
            for key in ['items', 'products', 'results', 'data']:
                if key in data and isinstance(data[key], list):
                    items = data[key]
                    break
            else:
                items = [data]  # Single item
        else:
            return ValidationResult(
                valid=False,
                score=0.0,
                issues=["Data is not a list or dict"],
                suggestions=["Return a list of items or a dict with 'items' key"]
            )
        
        # Check minimum count
        if len(items) < min_items:
            issues.append(f"Expected at least {min_items} items, got {len(items)}")
            score -= 0.3
        
        # Check required fields
        if expected_fields and items:
            for i, item in enumerate(items[:5]):  # Check first 5
                if isinstance(item, dict):
                    missing = [f for f in expected_fields if f not in item or item[f] is None]
                    if missing:
                        issues.append(f"Item {i}: missing fields {missing}")
                        score -= 0.1 * len(missing)
        
        # Check for empty values
        empty_count = 0
        for item in items[:10]:
            if isinstance(item, dict):
                empty_count += sum(1 for v in item.values() if v in [None, "", [], {}])
        
        if empty_count > len(items):
            issues.append(f"Many empty values detected ({empty_count})")
            score -= 0.2
        
        score = max(0.0, score)
        
        return ValidationResult(
            valid=len(issues) == 0,
            score=score,
            issues=issues,
            suggestions=suggestions
        )
    
    def validate_prices(self, data: List[Dict]) -> ValidationResult:
        """
        Validate price fields are reasonable.
        
        Checks:
        - Prices are numeric
        - Prices are positive
        - Prices are in reasonable range
        """
        issues = []
        score = 1.0
        
        prices = []
        for item in data[:20]:
            if isinstance(item, dict) and 'price' in item:
                price = item['price']
                if price is None:
                    continue
                if not isinstance(price, (int, float)):
                    issues.append(f"Price '{price}' is not numeric")
                    score -= 0.1
                elif price <= 0:
                    issues.append(f"Price {price} is not positive")
                    score -= 0.1
                elif price > 10000000:
                    issues.append(f"Price {price} seems unreasonably high")
                    score -= 0.05
                else:
                    prices.append(price)
        
        # Check for suspicious patterns
        if prices:
            if len(set(prices)) == 1 and len(prices) > 3:
                issues.append(f"All prices are identical ({prices[0]})")
                score -= 0.3
            
            avg_price = sum(prices) / len(prices)
            if avg_price < 0.01:
                issues.append(f"Average price {avg_price} seems too low")
                score -= 0.2
        
        return ValidationResult(
            valid=len(issues) == 0,
            score=max(0.0, score),
            issues=issues,
            suggestions=[]
        )
    
    def validate_names(self, data: List[Dict]) -> ValidationResult:
        """
        Validate name/title fields are reasonable.
        
        Checks:
        - Names are strings
        - Names have reasonable length
        - Names are not duplicates
        """
        issues = []
        score = 1.0
        
        names = []
        for item in data[:20]:
            if isinstance(item, dict):
                name = item.get('name') or item.get('title')
                if name is None:
                    continue
                if not isinstance(name, str):
                    issues.append(f"Name '{name}' is not a string")
                    score -= 0.1
                elif len(name) < 3:
                    issues.append(f"Name '{name}' is too short")
                    score -= 0.05
                elif len(name) > 500:
                    issues.append(f"Name is too long ({len(name)} chars)")
                    score -= 0.1
                else:
                    names.append(name)
        
        # Check duplicates
        if names:
            unique = set(names)
            if len(unique) < len(names) * 0.5:
                issues.append(f"Many duplicate names ({len(names) - len(unique)} duplicates)")
                score -= 0.3
        
        return ValidationResult(
            valid=len(issues) == 0,
            score=max(0.0, score),
            issues=issues,
            suggestions=[]
        )
    
    # =========================================================================
    # LLM-BASED VALIDATION (Semantic)
    # =========================================================================
    
    async def validate_semantic(
        self,
        data: Any,
        instruction: str,
        task_type: str = "extraction"
    ) -> ValidationResult:
        """
        Use LLM to validate results match instruction.
        
        Minimal context: instruction + 2-3 sample items.
        """
        if not self.llm:
            return ValidationResult(
                valid=True,
                score=0.5,
                issues=["No LLM available for semantic validation"],
                suggestions=[]
            )
        
        # Prepare minimal sample
        if isinstance(data, list):
            sample = data[:3]
        elif isinstance(data, dict):
            for key in ['items', 'products', 'results', 'data']:
                if key in data and isinstance(data[key], list):
                    sample = data[key][:3]
                    break
            else:
                sample = [data]
        else:
            sample = [str(data)[:200]]
        
        # Build minimal prompt
        prompt = f"""Validate extraction result.

Instruction: {instruction[:150]}
Task: {task_type}
Sample (first 3 items):
{json.dumps(sample, indent=2, ensure_ascii=False)[:400]}

Questions:
1. Does result match instruction? (yes/no)
2. Data quality? (good/partial/poor)
3. Any issues? (list briefly)

Respond JSON only:
{{"valid": true/false, "quality": "good/partial/poor", "issues": []}}
"""
        
        try:
            response = await self.llm.ainvoke(prompt)
            text = response.get("text", "") if isinstance(response, dict) else str(response)
            
            # Parse JSON from response
            json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                
                quality_scores = {"good": 1.0, "partial": 0.6, "poor": 0.3}
                score = quality_scores.get(result.get("quality", "partial"), 0.5)
                
                return ValidationResult(
                    valid=result.get("valid", False),
                    score=score,
                    issues=result.get("issues", []),
                    suggestions=[],
                    llm_reasoning=text
                )
        except Exception as e:
            return ValidationResult(
                valid=True,
                score=0.5,
                issues=[f"LLM validation error: {str(e)}"],
                suggestions=[]
            )
        
        return ValidationResult(
            valid=True,
            score=0.5,
            issues=["Could not parse LLM response"],
            suggestions=[]
        )
    
    # =========================================================================
    # JSON CORRECTION
    # =========================================================================
    
    def try_fix_json(self, raw_text: str) -> Tuple[bool, Any]:
        """
        Try to fix common JSON issues.
        
        Fixes:
        - Trailing commas
        - Single quotes instead of double
        - Missing brackets
        - Unquoted keys
        """
        text = raw_text.strip()
        
        # Try direct parse first
        try:
            return True, json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Extract JSON from markdown code blocks
        code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if code_block_match:
            try:
                return True, json.loads(code_block_match.group(1))
            except json.JSONDecodeError:
                text = code_block_match.group(1)
        
        # Fix single quotes
        fixed = text.replace("'", '"')
        try:
            return True, json.loads(fixed)
        except json.JSONDecodeError:
            pass
        
        # Fix trailing commas
        fixed = re.sub(r',\s*([}\]])', r'\1', text)
        try:
            return True, json.loads(fixed)
        except json.JSONDecodeError:
            pass
        
        # Try to wrap in array if it looks like objects
        if text.startswith('{') and not text.startswith('['):
            try:
                return True, json.loads('[' + text + ']')
            except json.JSONDecodeError:
                pass
        
        # Try jsonrepair library if available
        try:
            from json_repair import repair_json
            repaired = repair_json(text)
            return True, json.loads(repaired)
        except (ImportError, Exception):
            pass
        
        return False, None
    
    async def fix_with_llm(self, raw_text: str, expected_format: str = "") -> Tuple[bool, Any]:
        """
        Use LLM to fix malformed JSON.
        
        Only call if deterministic fixes failed.
        """
        if not self.llm:
            return False, None
        
        prompt = f"""Fix this malformed JSON. Return ONLY valid JSON, no explanation.

Input:
{raw_text[:500]}

Expected format: {expected_format or "list of objects with name, price, url"}

Fixed JSON:"""
        
        try:
            response = await self.llm.ainvoke(prompt)
            text = response.get("text", "") if isinstance(response, dict) else str(response)
            
            # Try to parse the fixed JSON
            success, data = self.try_fix_json(text)
            return success, data
        except Exception:
            return False, None
    
    # =========================================================================
    # COMBINED VALIDATION
    # =========================================================================
    
    async def validate(
        self,
        data: Any,
        instruction: str,
        expected_fields: List[str] = None,
        min_items: int = 1,
        use_llm: bool = True
    ) -> ValidationResult:
        """
        Full validation pipeline.
        
        1. Structure validation (deterministic)
        2. Field-specific validation (deterministic)
        3. Semantic validation (LLM, optional)
        """
        all_issues = []
        all_suggestions = []
        scores = []
        
        # 1. Structure validation
        struct_result = self.validate_structure(data, expected_fields, min_items)
        all_issues.extend(struct_result.issues)
        all_suggestions.extend(struct_result.suggestions)
        scores.append(struct_result.score)
        
        # Get items list for further validation
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            for key in ['items', 'products', 'results', 'data']:
                if key in data and isinstance(data[key], list):
                    items = data[key]
                    break
            else:
                items = [data]
        else:
            items = []
        
        if items:
            # 2. Price validation
            if expected_fields and 'price' in expected_fields:
                price_result = self.validate_prices(items)
                all_issues.extend(price_result.issues)
                scores.append(price_result.score)
            
            # 3. Name validation
            if expected_fields and ('name' in expected_fields or 'title' in expected_fields):
                name_result = self.validate_names(items)
                all_issues.extend(name_result.issues)
                scores.append(name_result.score)
        
        # 4. Semantic validation (LLM)
        llm_reasoning = ""
        if use_llm and self.llm:
            semantic_result = await self.validate_semantic(data, instruction)
            all_issues.extend(semantic_result.issues)
            scores.append(semantic_result.score)
            llm_reasoning = semantic_result.llm_reasoning
        
        # Combine scores
        final_score = sum(scores) / len(scores) if scores else 0.0
        
        return ValidationResult(
            valid=final_score >= 0.5 and len([i for i in all_issues if 'error' in i.lower()]) == 0,
            score=final_score,
            issues=all_issues,
            suggestions=all_suggestions,
            llm_reasoning=llm_reasoning
        )
