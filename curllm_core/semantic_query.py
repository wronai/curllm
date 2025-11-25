"""
Semantic Query Engine - Natural Language → Structured Extraction

Allows LLM to break down complex queries into atomic operations with full observability.

Example:
    Natural: "Find products under 150zł with ratings"
    
    Structured:
    {
      "intent": "extract_products",
      "filters": {
        "price": {"max": 150, "currency": "PLN"},
        "has_rating": true
      },
      "fields": ["name", "price", "url", "rating"],
      "execution_plan": [
        {"step": "identify_containers", "strategy": "price_heuristic"},
        {"step": "extract_fields", "parallel": true},
        {"step": "filter_results"},
        {"step": "validate_schema"}
      ]
    }
"""

import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class FieldSpec:
    """Specification for a single field to extract"""
    name: str
    type: str  # text, number, url, date, etc.
    required: bool = True
    selectors: List[str] = None
    patterns: List[str] = None
    transform: Optional[str] = None  # e.g., "parse_price", "normalize_url"
    
    def __post_init__(self):
        if self.selectors is None:
            self.selectors = []
        if self.patterns is None:
            self.patterns = []


@dataclass
class QueryFilter:
    """Filter condition for results"""
    field: str
    operator: str  # eq, ne, lt, lte, gt, gte, contains, regex
    value: Any


@dataclass
class SemanticQuery:
    """Structured representation of extraction query"""
    intent: str  # extract_products, extract_articles, extract_links, etc.
    entity_type: str  # product, article, comment, etc.
    fields: List[FieldSpec]
    filters: List[QueryFilter] = None
    context: Dict[str, Any] = None
    strategy: str = "auto"  # auto, dom_heuristic, vision, bql, xpath
    
    def __post_init__(self):
        if self.filters is None:
            self.filters = []
        if self.context is None:
            self.context = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent,
            "entity_type": self.entity_type,
            "fields": [asdict(f) for f in self.fields],
            "filters": [asdict(f) for f in self.filters],
            "context": self.context,
            "strategy": self.strategy
        }


class SemanticQueryEngine:
    """Convert natural language to structured queries and execute them"""
    
    def __init__(self, llm, page, run_logger=None):
        self.llm = llm
        self.page = page
        self.run_logger = run_logger
        
    async def parse_natural_language(self, instruction: str, page_context: Optional[Dict] = None) -> SemanticQuery:
        """
        Convert natural language instruction to structured SemanticQuery.
        
        Example:
            "Find products under 150zł" →
            SemanticQuery(
                intent="extract_products",
                entity_type="product",
                fields=[
                    FieldSpec("name", "text", required=True),
                    FieldSpec("price", "number", required=True),
                    FieldSpec("url", "url", required=True)
                ],
                filters=[
                    QueryFilter("price", "lte", 150)
                ]
            )
        """
        url = page_context.get("url", "") if page_context else ""
        
        prompt = f"""Parse extraction instruction into structured query.

Instruction: {instruction}
URL: {url}

Identify:
1. Intent (extract_products, extract_articles, extract_links, etc.)
2. Entity type (product, article, comment, etc.)
3. Fields to extract (name, price, url, etc.)
4. Filters (price < 150, rating > 4, etc.)

Respond JSON:
{{
  "intent": "extract_products",
  "entity_type": "product",
  "fields": [
    {{"name": "name", "type": "text", "required": true}},
    {{"name": "price", "type": "number", "required": true}},
    {{"name": "url", "type": "url", "required": true}}
  ],
  "filters": [
    {{"field": "price", "operator": "lte", "value": 150}}
  ],
  "strategy": "auto"
}}

JSON:"""
        
        response = await self.llm.ainvoke(prompt)
        text = response.get("text", "")
        
        # Extract JSON
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            data = json.loads(text[start:end+1])
            
            # Convert to SemanticQuery
            fields = [FieldSpec(**f) for f in data.get("fields", [])]
            filters = [QueryFilter(**f) for f in data.get("filters", [])]
            
            query = SemanticQuery(
                intent=data.get("intent"),
                entity_type=data.get("entity_type"),
                fields=fields,
                filters=filters,
                strategy=data.get("strategy", "auto")
            )
            
            if self.run_logger:
                self.run_logger.log_text("\n🔍 Parsed Semantic Query:")
                self.run_logger.log_code("json", json.dumps(query.to_dict(), indent=2))
            
            return query
        
        return None
    
    async def execute_query(self, query: SemanticQuery) -> Dict[str, Any]:
        """
        Execute semantic query using multi-step atomic operations.
        
        Returns:
            {
                "entities": [...],
                "execution_log": [...],
                "quality_metrics": {...}
            }
        """
        from .atomic_functions import AtomicFunctionExecutor
        
        executor = AtomicFunctionExecutor(self.page, self.run_logger)
        
        if self.run_logger:
            self.run_logger.log_text("\n⚙️ Executing Query with Atomic Functions")
        
        # Step 1: Identify containers
        containers = await executor.find_containers(
            entity_type=query.entity_type,
            min_count=1
        )
        
        if self.run_logger:
            self.run_logger.log_text(f"   Found {len(containers)} potential containers")
        
        # Step 2: Extract fields from each container
        entities = []
        for i, container in enumerate(containers):
            entity = {}
            
            for field_spec in query.fields:
                value = await executor.extract_field(
                    container=container,
                    field_spec=field_spec
                )
                entity[field_spec.name] = value
            
            # Apply filters
            if self._passes_filters(entity, query.filters):
                entities.append(entity)
        
        if self.run_logger:
            self.run_logger.log_text(f"   Extracted {len(entities)} entities after filtering")
        
        # Step 3: Validate
        validated = await executor.validate_entities(entities, query.fields)
        
        return {
            "entities": validated,
            "count": len(validated),
            "quality": {
                "completeness": self._calculate_completeness(validated, query.fields),
                "containers_found": len(containers),
                "extraction_rate": len(validated) / len(containers) if containers else 0
            }
        }
    
    def _passes_filters(self, entity: Dict, filters: List[QueryFilter]) -> bool:
        """Check if entity passes all filters"""
        for filter in filters:
            value = entity.get(filter.field)
            if value is None:
                return False
            
            if filter.operator == "lte":
                if not (value <= filter.value):
                    return False
            elif filter.operator == "gte":
                if not (value >= filter.value):
                    return False
            elif filter.operator == "eq":
                if not (value == filter.value):
                    return False
            # Add more operators as needed
        
        return True
    
    def _calculate_completeness(self, entities: List[Dict], fields: List[FieldSpec]) -> float:
        """Calculate what % of required fields are present"""
        if not entities:
            return 0.0
        
        required_fields = [f.name for f in fields if f.required]
        total_required = len(required_fields) * len(entities)
        total_present = 0
        
        for entity in entities:
            for field_name in required_fields:
                if entity.get(field_name):
                    total_present += 1
        
        return total_present / total_required if total_required > 0 else 1.0


async def semantic_extract(instruction: str, page, llm, run_logger=None, page_context: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
    """
    Convenience function for semantic extraction.
    
    Usage:
        result = await semantic_extract(
            "Find products under 150zł",
            page, llm, logger
        )
        
        # result = {
        #   "entities": [{name: ..., price: ..., url: ...}, ...],
        #   "count": 5,
        #   "quality": {"completeness": 0.95, ...}
        # }
    """
    engine = SemanticQueryEngine(llm, page, run_logger)
    query = await engine.parse_natural_language(instruction, page_context)
    
    if query:
        return await engine.execute_query(query)
    
    return None
