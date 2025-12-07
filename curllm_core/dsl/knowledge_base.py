"""
Knowledge Base - Track Algorithm Performance and Learn Optimal Strategies

Stores:
1. Algorithm success rates per domain
2. Best selectors for known sites
3. Form filling recipes
4. Extraction strategies

Uses SQLite for persistence, JSON for export.
"""

import json
import sqlite3
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime
from urllib.parse import urlparse
import fnmatch


@dataclass
class StrategyRecord:
    """Record of strategy execution."""
    
    url: str
    domain: str
    task: str
    algorithm: str
    selector: str
    fields: Dict[str, str]
    success: bool
    items_extracted: int
    execution_time_ms: int
    error_message: str = ""
    timestamp: str = ""
    dsl_file: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        if not self.domain:
            self.domain = urlparse(self.url).netloc


class KnowledgeBase:
    """
    Knowledge base for algorithm performance and strategies.
    
    Features:
    - Track success rates per domain/algorithm
    - Recommend best algorithm for new tasks
    - Store and retrieve DSL strategies
    - Learn from execution history
    """
    
    def __init__(self, db_path: str = "dsl/knowledge.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS strategies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url_pattern TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    task TEXT NOT NULL,
                    algorithm TEXT NOT NULL,
                    selector TEXT,
                    fields_json TEXT,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    avg_items INTEGER DEFAULT 0,
                    avg_time_ms INTEGER DEFAULT 0,
                    last_used TEXT,
                    dsl_file TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(domain, task, algorithm, selector)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    task TEXT NOT NULL,
                    algorithm TEXT NOT NULL,
                    selector TEXT,
                    success INTEGER NOT NULL,
                    items_extracted INTEGER DEFAULT 0,
                    execution_time_ms INTEGER DEFAULT 0,
                    error_message TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_strategies_domain 
                ON strategies(domain, task)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_executions_domain 
                ON executions(domain, task)
            """)
    
    def record_execution(self, record: StrategyRecord) -> int:
        """Record a strategy execution."""
        with sqlite3.connect(self.db_path) as conn:
            # Insert execution record
            cursor = conn.execute("""
                INSERT INTO executions 
                (url, domain, task, algorithm, selector, success, items_extracted, 
                 execution_time_ms, error_message, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.url,
                record.domain,
                record.task,
                record.algorithm,
                record.selector,
                1 if record.success else 0,
                record.items_extracted,
                record.execution_time_ms,
                record.error_message,
                record.timestamp,
            ))
            
            execution_id = cursor.lastrowid
            
            # Update or insert strategy stats
            fields_json = json.dumps(record.fields) if record.fields else "{}"
            
            conn.execute("""
                INSERT INTO strategies 
                (url_pattern, domain, task, algorithm, selector, fields_json,
                 success_count, failure_count, avg_items, avg_time_ms, last_used, dsl_file)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(domain, task, algorithm, selector) DO UPDATE SET
                    success_count = success_count + ?,
                    failure_count = failure_count + ?,
                    avg_items = (avg_items * (success_count + failure_count) + ?) / 
                                (success_count + failure_count + 1),
                    avg_time_ms = (avg_time_ms * (success_count + failure_count) + ?) / 
                                  (success_count + failure_count + 1),
                    last_used = ?
            """, (
                f"*{record.domain}/*",
                record.domain,
                record.task,
                record.algorithm,
                record.selector,
                fields_json,
                1 if record.success else 0,
                0 if record.success else 1,
                record.items_extracted,
                record.execution_time_ms,
                record.timestamp,
                record.dsl_file,
                # UPDATE values
                1 if record.success else 0,
                0 if record.success else 1,
                record.items_extracted,
                record.execution_time_ms,
                record.timestamp,
            ))
            
            return execution_id
    
    def get_best_strategy(
        self, 
        url: str, 
        task: str,
        min_success_rate: float = 0.5
    ) -> Optional[Dict[str, Any]]:
        """
        Get best strategy for URL and task.
        
        Returns strategy with highest success rate for the domain.
        """
        domain = urlparse(url).netloc
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            cursor = conn.execute("""
                SELECT 
                    *,
                    CAST(success_count AS FLOAT) / 
                        NULLIF(success_count + failure_count, 0) AS success_rate
                FROM strategies
                WHERE domain = ? AND task = ?
                  AND success_count + failure_count >= 1
                ORDER BY success_rate DESC, success_count DESC
                LIMIT 1
            """, (domain, task))
            
            row = cursor.fetchone()
            
            if row and row['success_rate'] >= min_success_rate:
                return {
                    'url_pattern': row['url_pattern'],
                    'domain': row['domain'],
                    'task': row['task'],
                    'algorithm': row['algorithm'],
                    'selector': row['selector'],
                    'fields': json.loads(row['fields_json'] or '{}'),
                    'success_rate': row['success_rate'],
                    'use_count': row['success_count'] + row['failure_count'],
                    'dsl_file': row['dsl_file'],
                }
            
            return None
    
    def get_algorithm_rankings(self, domain: str = None, task: str = None) -> List[Dict]:
        """
        Get algorithm rankings by success rate.
        
        Optionally filter by domain and/or task.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = """
                SELECT 
                    algorithm,
                    SUM(success_count) as total_success,
                    SUM(failure_count) as total_failure,
                    CAST(SUM(success_count) AS FLOAT) / 
                        NULLIF(SUM(success_count) + SUM(failure_count), 0) AS success_rate,
                    AVG(avg_items) as avg_items,
                    AVG(avg_time_ms) as avg_time_ms
                FROM strategies
                WHERE 1=1
            """
            params = []
            
            if domain:
                query += " AND domain = ?"
                params.append(domain)
            if task:
                query += " AND task = ?"
                params.append(task)
            
            query += " GROUP BY algorithm ORDER BY success_rate DESC"
            
            cursor = conn.execute(query, params)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def find_matching_strategies(
        self, 
        url: str, 
        task: str = None
    ) -> List[Dict[str, Any]]:
        """
        Find all strategies matching URL pattern.
        
        Searches by domain and URL patterns.
        """
        domain = urlparse(url).netloc
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = """
                SELECT 
                    *,
                    CAST(success_count AS FLOAT) / 
                        NULLIF(success_count + failure_count, 0) AS success_rate
                FROM strategies
                WHERE domain = ?
            """
            params = [domain]
            
            if task:
                query += " AND task = ?"
                params.append(task)
            
            query += " ORDER BY success_rate DESC, last_used DESC"
            
            cursor = conn.execute(query, params)
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'url_pattern': row['url_pattern'],
                    'domain': row['domain'],
                    'task': row['task'],
                    'algorithm': row['algorithm'],
                    'selector': row['selector'],
                    'fields': json.loads(row['fields_json'] or '{}'),
                    'success_rate': row['success_rate'],
                    'success_count': row['success_count'],
                    'failure_count': row['failure_count'],
                    'avg_items': row['avg_items'],
                    'avg_time_ms': row['avg_time_ms'],
                    'dsl_file': row['dsl_file'],
                })
            
            return results
    
    def suggest_algorithms(self, url: str, task: str) -> List[str]:
        """
        Suggest algorithms to try for URL/task.
        
        Returns list ordered by expected success.
        """
        domain = urlparse(url).netloc
        
        # Get domain-specific rankings
        domain_rankings = self.get_algorithm_rankings(domain=domain, task=task)
        
        # Get global rankings for this task
        global_rankings = self.get_algorithm_rankings(task=task)
        
        # Combine with domain preference
        algorithms = []
        seen = set()
        
        # Domain-specific first
        for r in domain_rankings:
            if r['algorithm'] not in seen:
                algorithms.append(r['algorithm'])
                seen.add(r['algorithm'])
        
        # Then global
        for r in global_rankings:
            if r['algorithm'] not in seen:
                algorithms.append(r['algorithm'])
                seen.add(r['algorithm'])
        
        # Default fallbacks
        defaults = [
            'statistical_containers',
            'pattern_detection',
            'llm_guided',
            'fallback_table'
        ]
        for alg in defaults:
            if alg not in seen:
                algorithms.append(alg)
        
        return algorithms
    
    def export_to_dsl_files(self, directory: str = "dsl") -> List[str]:
        """
        Export all strategies to DSL files.
        
        Returns list of created file paths.
        """
        from .parser import DSLParser, DSLStrategy
        
        parser = DSLParser()
        created_files = []
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            cursor = conn.execute("""
                SELECT * FROM strategies
                WHERE success_count > 0
                ORDER BY domain, task
            """)
            
            for row in cursor.fetchall():
                strategy = DSLStrategy(
                    url_pattern=row['url_pattern'],
                    task=row['task'],
                    algorithm=row['algorithm'],
                    selector=row['selector'] or "",
                    fields=json.loads(row['fields_json'] or '{}'),
                    success_rate=row['success_count'] / max(
                        row['success_count'] + row['failure_count'], 1
                    ),
                    use_count=row['success_count'] + row['failure_count'],
                    last_used=row['last_used'] or "",
                )
                
                filepath = parser.save_strategy(strategy, directory)
                created_files.append(filepath)
        
        return created_files
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get overall knowledge base statistics."""
        with sqlite3.connect(self.db_path) as conn:
            stats = {}
            
            # Total strategies
            cursor = conn.execute("SELECT COUNT(*) FROM strategies")
            stats['total_strategies'] = cursor.fetchone()[0]
            
            # Total executions
            cursor = conn.execute("SELECT COUNT(*) FROM executions")
            stats['total_executions'] = cursor.fetchone()[0]
            
            # Unique domains
            cursor = conn.execute("SELECT COUNT(DISTINCT domain) FROM strategies")
            stats['unique_domains'] = cursor.fetchone()[0]
            
            # Overall success rate
            cursor = conn.execute("""
                SELECT 
                    SUM(success_count) as successes,
                    SUM(failure_count) as failures
                FROM strategies
            """)
            row = cursor.fetchone()
            total = (row[0] or 0) + (row[1] or 0)
            stats['overall_success_rate'] = (row[0] or 0) / max(total, 1)
            
            # Top algorithms
            stats['top_algorithms'] = self.get_algorithm_rankings()[:5]
            
            return stats
