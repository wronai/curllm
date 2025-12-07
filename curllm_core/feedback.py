"""
User Feedback System

Allows users to rate extraction results and provide hints for improvement.
The system learns from feedback and adapts algorithms accordingly.

Usage:
    from curllm_core.feedback import FeedbackSystem, Feedback
    
    # Rate a result
    feedback = Feedback(
        url="https://shop.pl",
        task="extract_products",
        rating=3,  # 1-5 scale
        hint="Ceny są w złym formacie - powinny być liczbami",
        missing_fields=["image", "description"],
        incorrect_data={"price": "Should be numeric, got string"}
    )
    
    system = FeedbackSystem()
    system.record_feedback(feedback)
    
    # Get hints for next extraction
    hints = system.get_hints_for_url("https://shop.pl")
"""

import json
import sqlite3
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


@dataclass
class Feedback:
    """User feedback on extraction/form-fill result."""
    
    url: str
    task: str  # extract_products, extract_specs, fill_form, etc.
    rating: int  # 1-5 scale (1=terrible, 5=perfect)
    
    # Optional detailed feedback
    hint: str = ""  # General improvement hint
    missing_fields: List[str] = field(default_factory=list)
    incorrect_data: Dict[str, str] = field(default_factory=dict)  # field -> issue
    suggested_selector: str = ""  # If user knows the correct selector
    
    # Metadata
    algorithm_used: str = ""
    items_extracted: int = 0
    timestamp: str = ""
    run_id: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    @property
    def domain(self) -> str:
        return urlparse(self.url).netloc
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Feedback":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class FeedbackSystem:
    """
    System for collecting and utilizing user feedback.
    
    Stores feedback in SQLite and provides hints for future extractions.
    """
    
    def __init__(self, db_path: str = "dsl/feedback.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    task TEXT NOT NULL,
                    rating INTEGER NOT NULL,
                    hint TEXT,
                    missing_fields TEXT,
                    incorrect_data TEXT,
                    suggested_selector TEXT,
                    algorithm_used TEXT,
                    items_extracted INTEGER,
                    timestamp TEXT,
                    run_id TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS learned_hints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT NOT NULL,
                    task TEXT NOT NULL,
                    hint TEXT NOT NULL,
                    priority INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT,
                    UNIQUE(domain, task, hint)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedback_domain ON feedback(domain)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_hints_domain ON learned_hints(domain, task)
            """)
    
    def record_feedback(self, feedback: Feedback) -> int:
        """
        Record user feedback.
        
        Args:
            feedback: Feedback object
            
        Returns:
            Feedback ID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO feedback 
                (url, domain, task, rating, hint, missing_fields, incorrect_data,
                 suggested_selector, algorithm_used, items_extracted, timestamp, run_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                feedback.url,
                feedback.domain,
                feedback.task,
                feedback.rating,
                feedback.hint,
                json.dumps(feedback.missing_fields),
                json.dumps(feedback.incorrect_data),
                feedback.suggested_selector,
                feedback.algorithm_used,
                feedback.items_extracted,
                feedback.timestamp,
                feedback.run_id
            ))
            
            feedback_id = cursor.lastrowid
            
            # Learn from feedback if it contains actionable hints
            if feedback.hint:
                self._learn_from_hint(conn, feedback)
            
            if feedback.rating <= 2:
                self._record_failure_patterns(conn, feedback)
            
            logger.info(f"Recorded feedback #{feedback_id} for {feedback.domain}")
            return feedback_id
    
    def _learn_from_hint(self, conn: sqlite3.Connection, feedback: Feedback):
        """Extract learnable hints from feedback."""
        now = datetime.now().isoformat()
        
        try:
            conn.execute("""
                INSERT INTO learned_hints (domain, task, hint, priority, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(domain, task, hint) DO UPDATE SET
                    priority = priority + 1,
                    updated_at = ?
            """, (
                feedback.domain,
                feedback.task,
                feedback.hint,
                5 - feedback.rating,  # Lower rating = higher priority
                now, now, now
            ))
        except Exception as e:
            logger.warning(f"Failed to learn from hint: {e}")
    
    def _record_failure_patterns(self, conn: sqlite3.Connection, feedback: Feedback):
        """Record patterns from failed extractions."""
        if feedback.missing_fields:
            hint = f"Missing fields: {', '.join(feedback.missing_fields)}"
            self._learn_from_hint(conn, Feedback(
                url=feedback.url,
                task=feedback.task,
                rating=feedback.rating,
                hint=hint
            ))
        
        if feedback.incorrect_data:
            for field, issue in feedback.incorrect_data.items():
                hint = f"Field '{field}' issue: {issue}"
                self._learn_from_hint(conn, Feedback(
                    url=feedback.url,
                    task=feedback.task,
                    rating=feedback.rating,
                    hint=hint
                ))
    
    def get_hints_for_url(self, url: str, task: str = None) -> List[str]:
        """
        Get learned hints for a URL.
        
        Args:
            url: Target URL
            task: Optional task type filter
            
        Returns:
            List of hints sorted by priority
        """
        domain = urlparse(url).netloc
        
        with sqlite3.connect(self.db_path) as conn:
            if task:
                rows = conn.execute("""
                    SELECT hint FROM learned_hints
                    WHERE domain = ? AND task = ?
                    ORDER BY priority DESC, success_count DESC
                    LIMIT 10
                """, (domain, task)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT hint FROM learned_hints
                    WHERE domain = ?
                    ORDER BY priority DESC, success_count DESC
                    LIMIT 10
                """, (domain,)).fetchall()
        
        return [row[0] for row in rows]
    
    def get_feedback_summary(self, domain: str = None) -> Dict[str, Any]:
        """Get summary of feedback for a domain or overall."""
        with sqlite3.connect(self.db_path) as conn:
            if domain:
                stats = conn.execute("""
                    SELECT 
                        COUNT(*) as total,
                        AVG(rating) as avg_rating,
                        SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END) as good_count,
                        SUM(CASE WHEN rating <= 2 THEN 1 ELSE 0 END) as bad_count
                    FROM feedback WHERE domain = ?
                """, (domain,)).fetchone()
            else:
                stats = conn.execute("""
                    SELECT 
                        COUNT(*) as total,
                        AVG(rating) as avg_rating,
                        SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END) as good_count,
                        SUM(CASE WHEN rating <= 2 THEN 1 ELSE 0 END) as bad_count
                    FROM feedback
                """).fetchone()
        
        return {
            "total_feedback": stats[0] or 0,
            "average_rating": round(stats[1] or 0, 2),
            "good_results": stats[2] or 0,
            "bad_results": stats[3] or 0,
        }
    
    def mark_hint_success(self, domain: str, task: str, hint: str):
        """Mark a hint as successful (used and worked)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE learned_hints
                SET success_count = success_count + 1, updated_at = ?
                WHERE domain = ? AND task = ? AND hint = ?
            """, (datetime.now().isoformat(), domain, task, hint))
    
    def mark_hint_failure(self, domain: str, task: str, hint: str):
        """Mark a hint as failed (used but didn't help)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE learned_hints
                SET failure_count = failure_count + 1, 
                    priority = MAX(0, priority - 1),
                    updated_at = ?
                WHERE domain = ? AND task = ? AND hint = ?
            """, (datetime.now().isoformat(), domain, task, hint))
    
    def get_common_issues(self, task: str = None, limit: int = 10) -> List[Dict]:
        """Get most common issues across all domains."""
        with sqlite3.connect(self.db_path) as conn:
            if task:
                rows = conn.execute("""
                    SELECT hint, COUNT(*) as count, AVG(priority) as avg_priority
                    FROM learned_hints
                    WHERE task = ?
                    GROUP BY hint
                    ORDER BY count DESC, avg_priority DESC
                    LIMIT ?
                """, (task, limit)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT hint, COUNT(*) as count, AVG(priority) as avg_priority
                    FROM learned_hints
                    GROUP BY hint
                    ORDER BY count DESC, avg_priority DESC
                    LIMIT ?
                """, (limit,)).fetchall()
        
        return [
            {"hint": row[0], "occurrences": row[1], "priority": round(row[2], 1)}
            for row in rows
        ]
    
    def export_hints(self, filepath: str):
        """Export all learned hints to JSON."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT domain, task, hint, priority, success_count, failure_count
                FROM learned_hints
                ORDER BY domain, task, priority DESC
            """).fetchall()
        
        hints = [
            {
                "domain": r[0], "task": r[1], "hint": r[2],
                "priority": r[3], "success": r[4], "failure": r[5]
            }
            for r in rows
        ]
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(hints, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Exported {len(hints)} hints to {filepath}")


# Global feedback system instance
_feedback_system: Optional[FeedbackSystem] = None


def get_feedback_system() -> FeedbackSystem:
    """Get global feedback system instance."""
    global _feedback_system
    if _feedback_system is None:
        _feedback_system = FeedbackSystem()
    return _feedback_system
