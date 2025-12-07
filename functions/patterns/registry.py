"""
Adaptive Pattern Registry

Manages regex patterns that can be modified by LLM when they fail to match.

Usage:
    from functions.patterns import get_pattern, adapt_pattern
    
    # Get a pattern
    pattern = get_pattern("price.polish")
    match = pattern.match("1 234,56 zł")
    
    # If pattern fails, adapt it
    if not match:
        new_pattern = await adapt_pattern(
            "price.polish",
            failed_input="1.234,56 zł",  # Actual input that failed
            context="Polish price with dot as thousands separator"
        )
"""

import re
import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Pattern

logger = logging.getLogger(__name__)


@dataclass
class AdaptivePattern:
    """A regex pattern that can be adapted."""
    
    name: str
    pattern: str
    description: str = ""
    examples: List[Dict[str, str]] = field(default_factory=list)
    flags: int = 0
    version: int = 1
    success_count: int = 0
    failure_count: int = 0
    last_adapted: str = ""
    
    _compiled: Optional[Pattern] = field(default=None, repr=False)
    
    def __post_init__(self):
        self._compile()
    
    def _compile(self):
        """Compile the pattern."""
        try:
            self._compiled = re.compile(self.pattern, self.flags)
        except re.error as e:
            logger.error(f"Invalid pattern '{self.name}': {e}")
            self._compiled = None
    
    def match(self, text: str) -> Optional[re.Match]:
        """Match against text."""
        if not self._compiled:
            return None
        return self._compiled.search(text)
    
    def findall(self, text: str) -> List[str]:
        """Find all matches."""
        if not self._compiled:
            return []
        return self._compiled.findall(text)
    
    def update_pattern(self, new_pattern: str):
        """Update the pattern."""
        self.pattern = new_pattern
        self.version += 1
        self.last_adapted = datetime.now().isoformat()
        self._compile()
    
    def record_success(self):
        """Record successful match."""
        self.success_count += 1
    
    def record_failure(self):
        """Record failed match."""
        self.failure_count += 1
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "pattern": self.pattern,
            "description": self.description,
            "examples": self.examples,
            "flags": self.flags,
            "version": self.version,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.success_rate,
        }


class PatternRegistry:
    """Registry for adaptive patterns."""
    
    _instance: Optional["PatternRegistry"] = None
    
    def __new__(cls, db_path: str = "dsl/patterns.db"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._patterns: Dict[str, AdaptivePattern] = {}
            cls._instance._db_path = Path(db_path)
            cls._instance._db_path.parent.mkdir(parents=True, exist_ok=True)
            cls._instance._init_db()
            cls._instance._load_patterns()
        return cls._instance
    
    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS patterns (
                    name TEXT PRIMARY KEY,
                    pattern TEXT NOT NULL,
                    description TEXT,
                    examples TEXT,
                    flags INTEGER DEFAULT 0,
                    version INTEGER DEFAULT 1,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    last_adapted TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pattern_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    old_pattern TEXT,
                    new_pattern TEXT,
                    reason TEXT,
                    failed_input TEXT,
                    timestamp TEXT
                )
            """)
    
    def _load_patterns(self):
        """Load patterns from database."""
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute("""
                SELECT name, pattern, description, examples, flags, version,
                       success_count, failure_count, last_adapted
                FROM patterns
            """).fetchall()
        
        for row in rows:
            self._patterns[row[0]] = AdaptivePattern(
                name=row[0],
                pattern=row[1],
                description=row[2] or "",
                examples=json.loads(row[3]) if row[3] else [],
                flags=row[4] or 0,
                version=row[5] or 1,
                success_count=row[6] or 0,
                failure_count=row[7] or 0,
                last_adapted=row[8] or "",
            )
    
    def register(
        self,
        name: str,
        pattern: str,
        description: str = "",
        examples: List[Dict] = None,
        flags: int = 0,
    ) -> AdaptivePattern:
        """
        Register a new pattern.
        
        Args:
            name: Pattern name (e.g., "price.polish")
            pattern: Regex pattern string
            description: What the pattern matches
            examples: List of {input, expected} examples
            flags: Regex flags (re.IGNORECASE, etc.)
        """
        now = datetime.now().isoformat()
        
        adaptive = AdaptivePattern(
            name=name,
            pattern=pattern,
            description=description,
            examples=examples or [],
            flags=flags,
        )
        
        self._patterns[name] = adaptive
        
        # Save to database
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO patterns
                (name, pattern, description, examples, flags, version,
                 success_count, failure_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 1, 0, 0, ?, ?)
            """, (
                name, pattern, description,
                json.dumps(examples or []),
                flags, now, now
            ))
        
        logger.debug(f"Registered pattern: {name}")
        return adaptive
    
    def get(self, name: str) -> Optional[AdaptivePattern]:
        """Get a pattern by name."""
        return self._patterns.get(name)
    
    def update(self, name: str, new_pattern: str, reason: str = "", failed_input: str = ""):
        """
        Update a pattern.
        
        Args:
            name: Pattern name
            new_pattern: New regex pattern
            reason: Reason for update
            failed_input: Input that caused the failure
        """
        if name not in self._patterns:
            logger.warning(f"Pattern not found: {name}")
            return
        
        old_pattern = self._patterns[name].pattern
        self._patterns[name].update_pattern(new_pattern)
        
        now = datetime.now().isoformat()
        
        # Save to database
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                UPDATE patterns
                SET pattern = ?, version = version + 1, updated_at = ?, last_adapted = ?
                WHERE name = ?
            """, (new_pattern, now, now, name))
            
            # Record history
            conn.execute("""
                INSERT INTO pattern_history
                (name, old_pattern, new_pattern, reason, failed_input, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, old_pattern, new_pattern, reason, failed_input, now))
        
        logger.info(f"Updated pattern {name}: {old_pattern} -> {new_pattern}")
    
    def record_result(self, name: str, success: bool):
        """Record match result."""
        if name in self._patterns:
            if success:
                self._patterns[name].record_success()
            else:
                self._patterns[name].record_failure()
            
            # Update in database
            with sqlite3.connect(self._db_path) as conn:
                col = "success_count" if success else "failure_count"
                conn.execute(f"""
                    UPDATE patterns SET {col} = {col} + 1 WHERE name = ?
                """, (name,))
    
    def list(self, prefix: str = None) -> List[AdaptivePattern]:
        """List patterns, optionally filtered by prefix."""
        if prefix:
            return [p for n, p in self._patterns.items() if n.startswith(prefix)]
        return list(self._patterns.values())
    
    def get_history(self, name: str, limit: int = 10) -> List[Dict]:
        """Get pattern update history."""
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute("""
                SELECT old_pattern, new_pattern, reason, failed_input, timestamp
                FROM pattern_history
                WHERE name = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (name, limit)).fetchall()
        
        return [
            {
                "old_pattern": r[0],
                "new_pattern": r[1],
                "reason": r[2],
                "failed_input": r[3],
                "timestamp": r[4],
            }
            for r in rows
        ]


# Global registry instance
_registry: Optional[PatternRegistry] = None


def get_registry() -> PatternRegistry:
    """Get global pattern registry."""
    global _registry
    if _registry is None:
        _registry = PatternRegistry()
    return _registry


def get_pattern(name: str) -> Optional[AdaptivePattern]:
    """Get a pattern by name."""
    return get_registry().get(name)


def register_pattern(
    name: str,
    pattern: str,
    description: str = "",
    examples: List[Dict] = None,
    flags: int = 0,
) -> AdaptivePattern:
    """Register a new pattern."""
    return get_registry().register(name, pattern, description, examples, flags)


async def adapt_pattern(
    name: str,
    failed_input: str,
    context: str = "",
    llm_client = None,
) -> Optional[str]:
    """
    Adapt a pattern using LLM when it fails.
    
    Args:
        name: Pattern name
        failed_input: Input that the pattern failed to match
        context: Additional context about what should match
        llm_client: LLM client for generating new pattern
        
    Returns:
        New pattern string or None
    """
    registry = get_registry()
    pattern = registry.get(name)
    
    if not pattern:
        logger.warning(f"Pattern not found: {name}")
        return None
    
    if not llm_client:
        logger.warning("No LLM client provided for pattern adaptation")
        return None
    
    # Build prompt
    examples_str = "\n".join(
        f"  - {e.get('input', '')} -> should match"
        for e in pattern.examples[:5]
    )
    
    prompt = f"""Fix this regex pattern that failed to match the input.

Pattern name: {name}
Description: {pattern.description}
Current pattern: {pattern.pattern}
Failed to match: {failed_input!r}
Context: {context}

Working examples:
{examples_str}

The pattern should now also match: {failed_input!r}

Requirements:
1. Return ONLY the new regex pattern
2. The pattern must still match all previous examples
3. Use Python regex syntax
4. Keep the pattern as simple as possible

New pattern:"""

    try:
        response = await llm_client.ainvoke(prompt)
        text = response.get("text", "").strip()
        
        # Extract pattern (remove quotes if present)
        new_pattern = text.strip("'\"` \n")
        
        # Validate the new pattern
        try:
            compiled = re.compile(new_pattern, pattern.flags)
            
            # Test against failed input
            if not compiled.search(failed_input):
                logger.warning(f"New pattern still doesn't match failed input")
                return None
            
            # Test against existing examples
            for ex in pattern.examples:
                if "input" in ex and not compiled.search(ex["input"]):
                    logger.warning(f"New pattern breaks existing example: {ex['input']}")
                    return None
            
            # Update the pattern
            registry.update(name, new_pattern, f"Adapted to match: {failed_input}", failed_input)
            
            # Add new example
            pattern.examples.append({"input": failed_input, "adapted": True})
            
            logger.info(f"Successfully adapted pattern {name}")
            return new_pattern
            
        except re.error as e:
            logger.error(f"Invalid pattern from LLM: {e}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to adapt pattern: {e}")
        return None
