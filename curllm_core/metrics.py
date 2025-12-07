"""
Metrics Collector - Track Algorithm Performance

Collects and analyzes extraction metrics to improve algorithms.

Usage:
    from curllm_core.metrics import MetricsCollector, ExtractionMetrics
    
    collector = MetricsCollector()
    
    collector.record(ExtractionMetrics(
        url="https://shop.pl/products",
        algorithm="statistical_containers",
        success=True,
        items_count=15,
        execution_time_ms=1500,
        llm_calls=2,
        errors=[]
    ))
    
    # Analyze performance
    stats = collector.analyze()
    print(stats["success_rate"])
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse


@dataclass
class ExtractionMetrics:
    """Metrics for a single extraction run."""
    
    url: str
    algorithm: str
    success: bool
    items_count: int
    execution_time_ms: int
    llm_calls: int
    errors: List[str]
    
    # Optional fields
    domain: str = ""
    task: str = "extract"
    selector: str = ""
    validation_score: float = 0.0
    fallbacks_tried: List[str] = None
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        if not self.domain:
            self.domain = urlparse(self.url).netloc
        if self.fallbacks_tried is None:
            self.fallbacks_tried = []
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExtractionMetrics":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class MetricsCollector:
    """
    Collect and analyze extraction metrics.
    
    Stores metrics in JSONL format for easy appending and analysis.
    """
    
    def __init__(self, filepath: str = "metrics/extractions.jsonl"):
        self.filepath = Path(filepath)
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
    
    def record(self, metrics: ExtractionMetrics):
        """Record a single extraction result."""
        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write(metrics.to_json() + "\n")
    
    def load_all(self) -> List[ExtractionMetrics]:
        """Load all recorded metrics."""
        if not self.filepath.exists():
            return []
        
        metrics = []
        with open(self.filepath, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    metrics.append(ExtractionMetrics.from_dict(data))
                except (json.JSONDecodeError, TypeError):
                    continue
        
        return metrics
    
    def analyze(self, domain: str = None, algorithm: str = None) -> Dict[str, Any]:
        """
        Analyze collected metrics.
        
        Args:
            domain: Filter by domain
            algorithm: Filter by algorithm
        
        Returns:
            Statistics dictionary
        """
        metrics = self.load_all()
        
        # Apply filters
        if domain:
            metrics = [m for m in metrics if domain in m.domain]
        if algorithm:
            metrics = [m for m in metrics if m.algorithm == algorithm]
        
        if not metrics:
            return {"total": 0, "success_rate": 0.0}
        
        total = len(metrics)
        successes = sum(1 for m in metrics if m.success)
        success_rate = successes / total if total > 0 else 0.0
        
        # Timing stats
        times = [m.execution_time_ms for m in metrics]
        avg_time = sum(times) / len(times) if times else 0
        
        # LLM usage
        llm_calls = [m.llm_calls for m in metrics]
        avg_llm_calls = sum(llm_calls) / len(llm_calls) if llm_calls else 0
        
        # Items extracted
        items = [m.items_count for m in metrics if m.success]
        avg_items = sum(items) / len(items) if items else 0
        
        # Algorithm breakdown
        by_algorithm = {}
        for m in metrics:
            alg = m.algorithm
            if alg not in by_algorithm:
                by_algorithm[alg] = {"total": 0, "success": 0, "times": []}
            by_algorithm[alg]["total"] += 1
            if m.success:
                by_algorithm[alg]["success"] += 1
            by_algorithm[alg]["times"].append(m.execution_time_ms)
        
        # Calculate per-algorithm stats
        algorithm_stats = {}
        for alg, data in by_algorithm.items():
            algorithm_stats[alg] = {
                "total": data["total"],
                "success_rate": data["success"] / data["total"] if data["total"] > 0 else 0,
                "avg_time_ms": sum(data["times"]) / len(data["times"]) if data["times"] else 0,
            }
        
        # Common errors
        all_errors = []
        for m in metrics:
            all_errors.extend(m.errors)
        error_counts = {}
        for err in all_errors:
            err_key = err[:50]  # Truncate for grouping
            error_counts[err_key] = error_counts.get(err_key, 0) + 1
        top_errors = sorted(error_counts.items(), key=lambda x: -x[1])[:5]
        
        return {
            "total": total,
            "successes": successes,
            "success_rate": round(success_rate, 4),
            "avg_time_ms": round(avg_time, 2),
            "avg_llm_calls": round(avg_llm_calls, 2),
            "avg_items_extracted": round(avg_items, 2),
            "by_algorithm": algorithm_stats,
            "top_errors": top_errors,
        }
    
    def compare_algorithms(self, algorithms: List[str] = None) -> Dict[str, Any]:
        """
        Compare algorithm performance.
        
        Returns ranking by success rate and speed.
        """
        metrics = self.load_all()
        
        # Group by algorithm
        by_algorithm = {}
        for m in metrics:
            alg = m.algorithm
            if algorithms and alg not in algorithms:
                continue
            
            if alg not in by_algorithm:
                by_algorithm[alg] = []
            by_algorithm[alg].append(m)
        
        # Calculate stats
        results = []
        for alg, data in by_algorithm.items():
            total = len(data)
            successes = sum(1 for m in data if m.success)
            times = [m.execution_time_ms for m in data]
            
            results.append({
                "algorithm": alg,
                "total": total,
                "success_rate": successes / total if total > 0 else 0,
                "avg_time_ms": sum(times) / len(times) if times else 0,
                "min_time_ms": min(times) if times else 0,
                "max_time_ms": max(times) if times else 0,
            })
        
        # Sort by success rate, then by speed
        results.sort(key=lambda x: (-x["success_rate"], x["avg_time_ms"]))
        
        return {
            "ranking": results,
            "best_algorithm": results[0]["algorithm"] if results else None,
            "fastest_algorithm": min(results, key=lambda x: x["avg_time_ms"])["algorithm"] if results else None,
        }
    
    def get_domain_stats(self) -> Dict[str, Any]:
        """Get statistics per domain."""
        metrics = self.load_all()
        
        by_domain = {}
        for m in metrics:
            domain = m.domain
            if domain not in by_domain:
                by_domain[domain] = {"total": 0, "success": 0, "algorithms": set()}
            
            by_domain[domain]["total"] += 1
            if m.success:
                by_domain[domain]["success"] += 1
            by_domain[domain]["algorithms"].add(m.algorithm)
        
        # Convert to list with calculated stats
        results = []
        for domain, data in by_domain.items():
            results.append({
                "domain": domain,
                "total": data["total"],
                "success_rate": data["success"] / data["total"] if data["total"] > 0 else 0,
                "algorithms_used": list(data["algorithms"]),
            })
        
        results.sort(key=lambda x: -x["total"])
        
        return {"domains": results}
    
    def export_report(self, output_path: str = "metrics/report.md") -> str:
        """Export analysis as Markdown report."""
        stats = self.analyze()
        algo_compare = self.compare_algorithms()
        domain_stats = self.get_domain_stats()
        
        lines = [
            "# Extraction Metrics Report",
            f"\nGenerated: {datetime.now().isoformat()}",
            "",
            "## Summary",
            "",
            f"- **Total extractions:** {stats['total']}",
            f"- **Success rate:** {stats['success_rate']:.2%}",
            f"- **Avg time:** {stats['avg_time_ms']:.0f}ms",
            f"- **Avg LLM calls:** {stats['avg_llm_calls']:.1f}",
            f"- **Avg items extracted:** {stats['avg_items_extracted']:.1f}",
            "",
            "## Algorithm Comparison",
            "",
            "| Algorithm | Total | Success Rate | Avg Time |",
            "|-----------|-------|--------------|----------|",
        ]
        
        for alg in algo_compare.get("ranking", []):
            lines.append(
                f"| {alg['algorithm']} | {alg['total']} | "
                f"{alg['success_rate']:.2%} | {alg['avg_time_ms']:.0f}ms |"
            )
        
        lines.extend([
            "",
            f"**Best algorithm:** {algo_compare.get('best_algorithm', 'N/A')}",
            f"**Fastest algorithm:** {algo_compare.get('fastest_algorithm', 'N/A')}",
            "",
            "## Top Domains",
            "",
            "| Domain | Extractions | Success Rate |",
            "|--------|-------------|--------------|",
        ])
        
        for d in domain_stats.get("domains", [])[:10]:
            lines.append(
                f"| {d['domain']} | {d['total']} | {d['success_rate']:.2%} |"
            )
        
        if stats.get("top_errors"):
            lines.extend([
                "",
                "## Top Errors",
                "",
            ])
            for err, count in stats["top_errors"]:
                lines.append(f"- `{err}` ({count}x)")
        
        report = "\n".join(lines)
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)
        
        return output_path


# Global collector instance
_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance."""
    global _collector
    if _collector is None:
        _collector = MetricsCollector()
    return _collector


def record_extraction(
    url: str,
    algorithm: str,
    success: bool,
    items_count: int,
    execution_time_ms: int,
    llm_calls: int = 0,
    errors: List[str] = None,
    **kwargs
):
    """Convenience function to record extraction metrics."""
    collector = get_metrics_collector()
    collector.record(ExtractionMetrics(
        url=url,
        algorithm=algorithm,
        success=success,
        items_count=items_count,
        execution_time_ms=execution_time_ms,
        llm_calls=llm_calls,
        errors=errors or [],
        **kwargs
    ))
