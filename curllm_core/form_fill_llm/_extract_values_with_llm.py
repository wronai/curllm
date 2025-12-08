from typing import Any, Dict, List, Optional
from ._simple_parse import _simple_parse

async def _extract_values_with_llm(instruction: str, llm) -> Dict[str, str]:
    """
    Extract key-value pairs from instruction using LLM.
    
    NO HARDCODED PARSING - LLM understands the instruction.
    """
    prompt = f"""Extract key-value pairs from this form filling instruction.

Instruction: "{instruction}"

Return JSON with field names as keys and values to fill:
{{"field_name": "value", ...}}

Examples:
- "email=test@example.com, name=John" → {{"email": "test@example.com", "name": "John"}}
- "wypełnij formularz: imię Jan, telefon 123456" → {{"name": "Jan", "phone": "123456"}}

Return ONLY the JSON, no explanation."""

    try:
        response = await llm.agenerate([prompt])
        answer = response.generations[0][0].text.strip()
        
        # Clean markdown
        import re
        if '```' in answer:
            answer = re.sub(r'```\w*\n?', '', answer)
        
        import json
        return json.loads(answer)
    except Exception as e:
        logger.error(f"LLM value extraction failed: {e}")
        # Fallback: simple regex parsing
        return _simple_parse(instruction)
