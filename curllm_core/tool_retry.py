"""
Tool Retry Manager - Intelligent retry logic for tool execution.

Prevents infinite loops when tools fail repeatedly with the same error.
Provides fallback strategies and alternative approaches.
"""

from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class ToolRetryManager:
    """Manages tool retry logic to prevent infinite loops and suggest alternatives."""
    
    def __init__(self, max_same_error: int = 2):
        """
        Initialize the retry manager.
        
        Args:
            max_same_error: Maximum number of times the same error is allowed
                           before stopping retries (default: 2)
        """
        self.tool_failures: Dict[str, List[str]] = {}
        self.max_same_error = max_same_error
        self.total_failures: Dict[str, int] = {}
    
    def should_retry(self, tool_name: str, error: str) -> bool:
        """
        Check if a tool should be retried or skipped.
        
        Args:
            tool_name: Name of the tool that failed
            error: Error message from the tool
            
        Returns:
            True if the tool should be retried, False if it should be skipped
        """
        if tool_name not in self.tool_failures:
            self.tool_failures[tool_name] = []
            self.total_failures[tool_name] = 0
        
        # Count how many times this exact error occurred
        error_count = self.tool_failures[tool_name].count(error)
        
        if error_count >= self.max_same_error:
            logger.warning(
                f"Tool '{tool_name}' failed {error_count}x with same error - SKIPPING further retries"
            )
            return False
        
        # Record this failure
        self.tool_failures[tool_name].append(error)
        self.total_failures[tool_name] += 1
        
        return True
    
    def get_alternative_approach(self, tool_name: str) -> Optional[str]:
        """
        Suggest an alternative approach when a tool repeatedly fails.
        
        Args:
            tool_name: Name of the tool that failed
            
        Returns:
            Name of alternative tool/approach, or None if no alternative exists
        """
        alternatives = {
            "form.fill": "llm_guided_field_fill",
            "click": "navigate",
            "extract": "extract_with_vision",
        }
        
        return alternatives.get(tool_name)
    
    def get_failure_summary(self, tool_name: str) -> Dict:
        """
        Get a summary of failures for a specific tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Dictionary with failure statistics
        """
        if tool_name not in self.tool_failures:
            return {
                "total_failures": 0,
                "unique_errors": 0,
                "errors": []
            }
        
        errors = self.tool_failures[tool_name]
        unique_errors = list(set(errors))
        
        return {
            "total_failures": len(errors),
            "unique_errors": len(unique_errors),
            "errors": unique_errors,
            "most_common_error": max(set(errors), key=errors.count) if errors else None
        }
    
    def reset(self):
        """Reset all failure tracking."""
        self.tool_failures.clear()
        self.total_failures.clear()
    
    def is_repetitive_failure(self, tool_name: str) -> bool:
        """
        Check if a tool is failing repetitively with the same error.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            True if the tool has repetitive failures
        """
        if tool_name not in self.tool_failures:
            return False
        
        errors = self.tool_failures[tool_name]
        if len(errors) < 2:
            return False
        
        # Check if the last N errors are the same
        last_n = min(3, len(errors))
        recent_errors = errors[-last_n:]
        
        return len(set(recent_errors)) == 1
