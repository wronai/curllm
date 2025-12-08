"""
DSL Query Generator - LLM generates DSL queries from natural language

The LLM interprets user intent and generates structured DSL queries
that can be executed by atomic functions.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DSLQuery:
    """A DSL query to be executed"""
    function: str          # Name of atomic function to call
    params: Dict[str, Any] # Parameters for the function
    depends_on: List[str] = None  # Other queries this depends on
    
    def __post_init__(self):
        if self.depends_on is None:
            self.depends_on = []


@dataclass
class DSLPlan:
    """A plan of DSL queries to execute"""
    queries: List[DSLQuery]
    intent: str
    confidence: float


class DSLQueryGenerator:
    """
    Generates DSL queries from natural language using LLM.
    
    NO HARDCODED MAPPINGS - LLM decides what functions to call.
    """
    
    # Available atomic functions - LLM learns these
    AVAILABLE_FUNCTIONS = """
Available atomic functions:

1. find_input_by_context(purpose_description: str)
   - Finds an input field by understanding its context
   - Example: find_input_by_context("field for entering email address")

2. find_clickable_by_intent(intent: str)
   - Finds a clickable element (button/link) by intent
   - Example: find_clickable_by_intent("submit the form")

3. find_url_by_intent(intent: str)
   - Finds a URL/link matching an intent
   - Example: find_url_by_intent("go to login page")

4. analyze_page_structure()
   - Analyzes current page structure statistically
   - Returns: forms count, inputs count, page features

5. find_repeating_pattern(min_count: int)
   - Finds repeating DOM patterns (for lists, products, etc.)
   - Example: find_repeating_pattern(3)

6. detect_message_type()
   - Detects success/error/info messages on page
   - Returns: message type and text

7. extract_data_pattern(description: str)
   - Extracts data matching a description
   - Example: extract_data_pattern("product prices and names")
"""
    
    def __init__(self, llm=None):
        self.llm = llm
    
    async def generate_plan(self, task_description: str, page_context: Dict = None) -> Optional[DSLPlan]:
        """
        Generate a DSL plan from natural language task description.
        
        Args:
            task_description: What the user wants to do
            page_context: Optional context about current page state
            
        Returns:
            DSLPlan with queries to execute
        """
        if not self.llm:
            logger.warning("No LLM available for DSL generation")
            return None
        
        context_info = ""
        if page_context:
            context_info = f"""
Current page context:
- URL: {page_context.get('url', 'unknown')}
- Title: {page_context.get('title', 'unknown')}
- Has forms: {page_context.get('has_forms', 'unknown')}
"""
        
        prompt = f"""You are a DSL query generator. Convert the user's task into a sequence of atomic function calls.

{self.AVAILABLE_FUNCTIONS}

{context_info}

User task: "{task_description}"

Generate a JSON plan with this structure:
{{
    "intent": "brief description of what we're doing",
    "confidence": 0.0-1.0,
    "queries": [
        {{"function": "function_name", "params": {{"param1": "value1"}}}},
        ...
    ]
}}

Rules:
- Use only the available functions
- Order queries logically (dependencies first)
- Keep it minimal - only necessary steps
- Return ONLY valid JSON, no explanation"""

        try:
            response = await self.llm.agenerate([prompt])
            answer = response.generations[0][0].text.strip()
            
            # Clean markdown code blocks
            if '```' in answer:
                answer = re.sub(r'```\w*\n?', '', answer)
            
            # Parse JSON
            data = json.loads(answer)
            
            queries = []
            for q in data.get('queries', []):
                queries.append(DSLQuery(
                    function=q.get('function', ''),
                    params=q.get('params', {}),
                    depends_on=q.get('depends_on', []),
                ))
            
            return DSLPlan(
                queries=queries,
                intent=data.get('intent', task_description),
                confidence=data.get('confidence', 0.7),
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM DSL response: {e}")
            return None
        except Exception as e:
            logger.error(f"DSL generation failed: {e}")
            return None
    
    async def generate_single_query(self, action: str) -> Optional[DSLQuery]:
        """
        Generate a single DSL query for a simple action.
        """
        if not self.llm:
            return None
        
        prompt = f"""Convert this action into a single atomic function call.

{self.AVAILABLE_FUNCTIONS}

Action: "{action}"

Respond with ONLY JSON:
{{"function": "function_name", "params": {{"param": "value"}}}}"""

        try:
            response = await self.llm.agenerate([prompt])
            answer = response.generations[0][0].text.strip()
            
            if '```' in answer:
                answer = re.sub(r'```\w*\n?', '', answer)
            
            data = json.loads(answer)
            return DSLQuery(
                function=data.get('function', ''),
                params=data.get('params', {}),
            )
        except Exception as e:
            logger.error(f"Single query generation failed: {e}")
            return None
    
    async def refine_query(self, query: DSLQuery, error: str) -> Optional[DSLQuery]:
        """
        Refine a failed query based on error feedback.
        """
        if not self.llm:
            return None
        
        prompt = f"""The following DSL query failed. Suggest a fix.

Original query:
- Function: {query.function}
- Params: {json.dumps(query.params)}

Error: {error}

{self.AVAILABLE_FUNCTIONS}

Respond with corrected JSON:
{{"function": "function_name", "params": {{"param": "value"}}}}"""

        try:
            response = await self.llm.agenerate([prompt])
            answer = response.generations[0][0].text.strip()
            
            if '```' in answer:
                answer = re.sub(r'```\w*\n?', '', answer)
            
            data = json.loads(answer)
            return DSLQuery(
                function=data.get('function', ''),
                params=data.get('params', {}),
            )
        except Exception as e:
            logger.error(f"Query refinement failed: {e}")
            return None
