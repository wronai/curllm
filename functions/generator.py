"""
Function Generator

Uses LLM to generate new atomic functions based on patterns and examples.
Generated functions are saved to the functions directory.

Usage:
    from functions.generator import FunctionGenerator
    
    generator = FunctionGenerator(llm_client)
    
    func_info = await generator.generate_python_function(
        name="extract_allegro_price",
        description="Extract price from Allegro product listing",
        examples=[
            {"input": "99,99 zł", "output": 99.99},
        ]
    )
"""

import json
import logging
import re
import ast
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class FunctionGenerator:
    """Generates atomic functions using LLM."""
    
    def __init__(self, llm_client, output_dir: str = "functions"):
        self.llm = llm_client
        self.output_dir = Path(output_dir)
        self.generated_dir = self.output_dir / "generated"
        self.generated_dir.mkdir(parents=True, exist_ok=True)
    
    async def generate_python_function(
        self,
        name: str,
        description: str,
        examples: List[Dict[str, Any]],
        category: str = "extractors",
        input_type: str = "str",
        output_type: str = "Any",
        tags: List[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a Python function using LLM.
        
        Args:
            name: Function name
            description: What the function does
            examples: List of {input, output} examples
            category: Function category
            input_type: Input parameter type
            output_type: Return type
            tags: Optional tags
            
        Returns:
            Dictionary with function info and file path, or None on failure
        """
        prompt = self._build_python_prompt(
            name, description, examples, input_type, output_type, tags or []
        )
        
        try:
            response = await self.llm.ainvoke(prompt)
            code = self._extract_code(response.get("text", ""), language="python")
            
            if not code:
                logger.error("Failed to extract code from LLM response")
                return None
            
            # Validate syntax
            if not self._validate_python_syntax(code):
                logger.error("Generated code has syntax errors")
                return None
            
            # Save to file
            filepath = self.generated_dir / f"{name}.py"
            full_code = self._wrap_python_function(code, name, category, description, examples, tags)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(full_code)
            
            logger.info(f"Generated function saved to {filepath}")
            
            return {
                "name": name,
                "category": category,
                "description": description,
                "filepath": str(filepath),
                "code": code,
            }
            
        except Exception as e:
            logger.error(f"Failed to generate function: {e}")
            return None
    
    async def generate_js_function(
        self,
        name: str,
        description: str,
        examples: List[Dict[str, Any]],
        category: str = "extractors",
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a JavaScript function using LLM.
        
        Args:
            name: Function name
            description: What the function does
            examples: List of {input, output} examples
            category: Function category
            
        Returns:
            Dictionary with function info and file path
        """
        prompt = self._build_js_prompt(name, description, examples)
        
        try:
            response = await self.llm.ainvoke(prompt)
            code = self._extract_code(response.get("text", ""), language="javascript")
            
            if not code:
                logger.error("Failed to extract JS code from LLM response")
                return None
            
            # Save to file
            filepath = self.output_dir / "js" / "generated" / f"{name}.js"
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            full_code = self._wrap_js_function(code, name, category, description)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(full_code)
            
            logger.info(f"Generated JS function saved to {filepath}")
            
            return {
                "name": name,
                "category": category,
                "description": description,
                "filepath": str(filepath),
                "code": code,
            }
            
        except Exception as e:
            logger.error(f"Failed to generate JS function: {e}")
            return None
    
    def _build_python_prompt(
        self,
        name: str,
        description: str,
        examples: List[Dict],
        input_type: str,
        output_type: str,
        tags: List[str],
    ) -> str:
        """Build prompt for Python function generation."""
        examples_str = "\n".join(
            f"  - Input: {e['input']!r} → Output: {e['output']!r}"
            for e in examples[:5]
        )
        
        return f"""Generate a Python function with the following specification:

Function name: {name}
Description: {description}
Input type: {input_type}
Output type: {output_type}
Tags: {', '.join(tags)}

Examples:
{examples_str}

Requirements:
1. The function must be pure (no side effects)
2. Handle edge cases (None, empty string, etc.)
3. Return None on invalid input
4. Use type hints
5. Include a docstring

Output ONLY the function code (def ... : ... return), no imports or decorators.
The function should be self-contained and work with standard Python.

```python
def {name}("""
    
    def _build_js_prompt(
        self,
        name: str,
        description: str,
        examples: List[Dict],
    ) -> str:
        """Build prompt for JavaScript function generation."""
        examples_str = "\n".join(
            f"  - Input: {json.dumps(e['input'])} → Output: {json.dumps(e['output'])}"
            for e in examples[:5]
        )
        
        return f"""Generate a JavaScript function with the following specification:

Function name: {name}
Description: {description}

Examples:
{examples_str}

Requirements:
1. The function should work in browser context
2. Handle null/undefined inputs gracefully
3. Return null on invalid input
4. Use JSDoc comments

Output ONLY the function code, no module exports.

```javascript
function {name}("""
    
    def _extract_code(self, text: str, language: str = "python") -> Optional[str]:
        """Extract code from LLM response."""
        # Try to find code block
        patterns = [
            rf'```{language}\s*\n(.*?)```',
            rf'```\s*\n(.*?)```',
            r'def \w+\(.*?\):.*?(?=\n\n|\Z)',  # Python function
            r'function \w+\(.*?\)\s*\{.*?\}',  # JS function
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                return match.group(1).strip() if '```' in pattern else match.group(0).strip()
        
        # Try to find function definition directly
        if language == "python" and "def " in text:
            start = text.find("def ")
            if start >= 0:
                # Find the end of the function
                lines = text[start:].split('\n')
                func_lines = []
                for i, line in enumerate(lines):
                    func_lines.append(line)
                    # Stop at empty line or next def (but not first)
                    if i > 0 and (line.strip() == '' or line.startswith('def ')):
                        break
                return '\n'.join(func_lines).strip()
        
        return None
    
    def _validate_python_syntax(self, code: str) -> bool:
        """Validate Python syntax."""
        try:
            ast.parse(code)
            return True
        except SyntaxError as e:
            logger.warning(f"Syntax error in generated code: {e}")
            return False
    
    def _wrap_python_function(
        self,
        code: str,
        name: str,
        category: str,
        description: str,
        examples: List[Dict],
        tags: List[str] = None,
    ) -> str:
        """Wrap function code with imports and registration."""
        examples_json = json.dumps(examples, ensure_ascii=False)
        tags_str = json.dumps(tags or [])
        
        return f'''"""
Auto-generated function: {name}
Generated: {datetime.now().isoformat()}
Description: {description}
"""

from typing import Optional, Any
import re
import sys
sys.path.insert(0, str(__file__).rsplit('/', 3)[0])

from functions.registry import register_function


@register_function(
    category="{category}",
    description="""{description}""",
    examples={examples_json},
    tags={tags_str}
)
{code}
'''
    
    def _wrap_js_function(
        self,
        code: str,
        name: str,
        category: str,
        description: str,
    ) -> str:
        """Wrap JS function code with registration."""
        return f'''/**
 * Auto-generated function: {name}
 * Generated: {datetime.now().isoformat()}
 * Description: {description}
 */

{code}

// Register function
if (typeof FunctionRegistry !== 'undefined') {{
    FunctionRegistry.register('{name}', {name}, {{
        category: '{category}',
        description: '{description}',
        generated: true
    }});
}}

// Export for Node.js
if (typeof module !== 'undefined') {{
    module.exports = {{ {name} }};
}}
'''
    
    async def generate_from_feedback(
        self,
        feedback: Dict[str, Any],
        existing_functions: List[str],
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a function based on user feedback.
        
        Args:
            feedback: User feedback dict with hint, missing_fields, etc.
            existing_functions: List of existing function names to avoid duplicates
            
        Returns:
            Generated function info or None
        """
        hint = feedback.get("hint", "")
        missing = feedback.get("missing_fields", [])
        incorrect = feedback.get("incorrect_data", {})
        
        if not hint and not missing and not incorrect:
            return None
        
        # Build prompt for function suggestion
        prompt = f"""Based on this user feedback about a data extraction issue:

Hint: {hint}
Missing fields: {missing}
Incorrect data: {json.dumps(incorrect)}

Existing functions: {existing_functions[:20]}

Suggest a new atomic function that could help fix this issue.
Provide:
1. Function name (snake_case)
2. Description
3. Input/output examples (3-5)
4. Whether it should be Python or JavaScript

Format:
NAME: function_name
LANG: python|javascript
DESCRIPTION: What it does
EXAMPLES:
- input: "example" -> output: "result"
"""
        
        try:
            response = await self.llm.ainvoke(prompt)
            text = response.get("text", "")
            
            # Parse response
            name_match = re.search(r'NAME:\s*(\w+)', text)
            lang_match = re.search(r'LANG:\s*(\w+)', text, re.IGNORECASE)
            desc_match = re.search(r'DESCRIPTION:\s*(.+?)(?=EXAMPLES|$)', text, re.DOTALL)
            
            if not name_match:
                return None
            
            name = name_match.group(1)
            lang = (lang_match.group(1) if lang_match else "python").lower()
            description = desc_match.group(1).strip() if desc_match else hint
            
            # Parse examples
            examples = []
            for match in re.finditer(r'input:\s*["\']?([^"\']+)["\']?\s*->\s*output:\s*["\']?([^"\']+)', text, re.IGNORECASE):
                examples.append({
                    "input": match.group(1).strip(),
                    "output": match.group(2).strip()
                })
            
            if not examples:
                examples = [{"input": "example", "output": "result"}]
            
            # Generate the function
            if lang == "javascript":
                return await self.generate_js_function(name, description, examples)
            else:
                return await self.generate_python_function(name, description, examples)
                
        except Exception as e:
            logger.error(f"Failed to generate function from feedback: {e}")
            return None
