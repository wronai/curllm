"""
Tool Orchestrator - LLM-driven tool selection and execution

The orchestrator:
1. Analyzes user instruction
2. Selects appropriate tools from registry
3. Generates execution plan (JSON DSL)
4. Executes tools sequentially/in pipeline
5. Validates output
"""

import json
from typing import Any, Dict, List, Optional
from .registry import get_registry


class ToolOrchestrator:
    """LLM-driven orchestrator for tool selection and execution"""
    
    def __init__(self, llm, page, run_logger=None):
        self.llm = llm
        self.page = page
        self.run_logger = run_logger
        self.registry = get_registry()
        
    async def orchestrate(self, instruction: str, page_context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Main orchestration flow:
        1. Generate execution plan using LLM
        2. Execute tools in sequence
        3. Return final result
        """
        try:
            if self.run_logger:
                self.run_logger.log_text("\n🔧 ═══ TOOL ORCHESTRATOR ═══")
                self.run_logger.log_text(f"Instruction: {instruction}")
            
            # Phase 1: Generate execution plan
            plan = await self._generate_plan(instruction, page_context)
            if not plan or "plan" not in plan:
                if self.run_logger:
                    self.run_logger.log_text("⚠️ No execution plan generated")
                return None
            
            if self.run_logger:
                self.run_logger.log_text("\n📋 Execution Plan:")
                self.run_logger.log_code("json", json.dumps(plan, indent=2))
            
            # Phase 2: Execute tools
            result = await self._execute_plan(plan)
            
            if self.run_logger:
                self.run_logger.log_text(f"\n✅ Orchestration complete")
                if result:
                    self.run_logger.log_code("json", json.dumps(result, indent=2)[:500])
            
            return result
            
        except Exception as e:
            if self.run_logger:
                self.run_logger.log_text(f"❌ Orchestration failed: {e}")
            return None
    
    async def _generate_plan(self, instruction: str, page_context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Use LLM to generate tool execution plan"""
        
        # Get available tools
        manifests = self.registry.get_manifests()
        
        # Build compact tool catalog for LLM
        tool_catalog = []
        for name, manifest in manifests.items():
            tool_catalog.append({
                "name": name,
                "category": manifest.get("category"),
                "description": manifest.get("description", "")[:100],
                "parameters": list(manifest.get("parameters", {}).get("properties", {}).keys()),
                "triggers": manifest.get("triggers", [])[:3]
            })
        
        # Build prompt
        url = page_context.get("url", "") if page_context else ""
        prompt = f"""You are a tool orchestration planner. Generate an execution plan using available tools.

Instruction: {instruction}
URL: {url}

Available Tools:
{json.dumps(tool_catalog, indent=2)}

Generate a JSON execution plan with these tools. Each step should use ONE tool.

Example plan structure:
{{
  "plan": [
    {{
      "tool": "forms.price_filter",
      "parameters": {{"max": 150, "submit": true}},
      "description": "Apply price filter"
    }},
    {{
      "tool": "navigation.scroll_load",
      "parameters": {{"times": 8}},
      "description": "Load more products"
    }},
    {{
      "tool": "extraction.products_ceneo",
      "parameters": {{"max_price": 150}},
      "description": "Extract products"
    }}
  ]
}}

Rules:
1. Use tools in logical order: navigation → forms → extraction
2. Match tool names EXACTLY from catalog
3. Include only required parameters
4. Keep plan minimal (2-4 steps typically)

JSON:"""
        
        response = await self.llm.ainvoke(prompt)
        text = response.get("text", "")
        
        # Extract JSON
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end+1])
            except Exception as e:
                if self.run_logger:
                    self.run_logger.log_text(f"⚠️ Failed to parse plan: {e}")
                return None
        
        return None
    
    async def _execute_plan(self, plan: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute tools according to plan"""
        steps = plan.get("plan", [])
        context = {}
        final_result = None
        
        for i, step in enumerate(steps):
            tool_name = step.get("tool")
            parameters = step.get("parameters", {})
            description = step.get("description", "")
            
            if self.run_logger:
                self.run_logger.log_text(f"\n🔧 Step {i+1}/{len(steps)}: {description}")
                self.run_logger.log_text(f"   Tool: {tool_name}")
                self.run_logger.log_text(f"   Parameters: {json.dumps(parameters)}")
            
            # Get tool from registry
            tool = self.registry.get(tool_name)
            if not tool:
                if self.run_logger:
                    self.run_logger.log_text(f"⚠️ Tool not found: {tool_name}")
                continue
            
            # Execute tool
            try:
                result = await tool.execute(self.page, parameters, context)
                
                if self.run_logger:
                    self.run_logger.log_text(f"   ✅ Success: {json.dumps(result, indent=2)[:200]}")
                
                # Update context for next tool
                context.update(result)
                final_result = result
                
            except Exception as e:
                if self.run_logger:
                    self.run_logger.log_text(f"   ❌ Error: {e}")
                continue
        
        return final_result


async def orchestrate_with_tools(instruction: str, page, llm, run_logger=None, page_context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Convenience function to orchestrate tool execution.
    
    Usage:
        result = await orchestrate_with_tools(
            "Find products under 150zł on Ceneo",
            page, llm, run_logger
        )
    """
    orchestrator = ToolOrchestrator(llm, page, run_logger)
    return await orchestrator.orchestrate(instruction, page_context)
