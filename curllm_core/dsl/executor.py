"""
DSL Executor - Execute DSL Strategies with Knowledge Base Integration

Orchestrates:
1. Strategy lookup from knowledge base
2. Algorithm execution with fallbacks
3. Result validation
4. Learning from execution results

Integrates:
- DOM Toolkit analyzers
- Multiple extraction algorithms
- Form filling
- Result validation
"""

import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse

from .parser import DSLParser, DSLStrategy
from .knowledge_base import KnowledgeBase, StrategyRecord
from .validator import ResultValidator


@dataclass
class ExecutionResult:
    """Result of DSL execution."""
    
    success: bool
    data: Any
    strategy_used: DSLStrategy
    algorithm_used: str
    execution_time_ms: int
    validation_score: float
    issues: List[str]
    suggestions: List[str]
    fallbacks_tried: List[str]


class DSLExecutor:
    """
    Execute DSL strategies with intelligent algorithm selection.
    
    Pipeline:
    1. Load/find strategy for URL
    2. Try algorithms in order of expected success
    3. Validate results
    4. Learn from execution
    5. Save successful strategy to DSL file
    """
    
    # Available algorithms
    ALGORITHMS = {
        'statistical_containers': '_execute_statistical',
        'pattern_detection': '_execute_pattern',
        'llm_guided': '_execute_llm_guided',
        'fallback_table': '_execute_fallback_table',
        'fallback_links': '_execute_fallback_links',
        'form_fill': '_execute_form_fill',
    }
    
    def __init__(
        self,
        page,
        llm_client,
        run_logger=None,
        kb_path: str = "dsl/knowledge.db",
        dsl_dir: str = "dsl"
    ):
        self.page = page
        self.llm = llm_client
        self.logger = run_logger
        
        self.parser = DSLParser()
        self.kb = KnowledgeBase(kb_path)
        self.validator = ResultValidator(llm_client)
        self.dsl_dir = dsl_dir
        
        # Import DOM toolkit
        try:
            from ..dom_toolkit.analyzers import (
                DOMStructureAnalyzer, PatternDetector, 
                SelectorGenerator, PriceDetector
            )
            from ..dom_toolkit.statistics import (
                FrequencyAnalyzer, ElementClusterer, CandidateScorer
            )
            from ..dom_toolkit.orchestrator import ExtractionOrchestrator
            
            self.structure = DOMStructureAnalyzer
            self.patterns = PatternDetector
            self.selectors = SelectorGenerator
            self.prices = PriceDetector
            self.frequency = FrequencyAnalyzer
            self.clustering = ElementClusterer
            self.scoring = CandidateScorer
            self.orchestrator_class = ExtractionOrchestrator
            self.toolkit_available = True
        except ImportError:
            self.toolkit_available = False
    
    def _log(self, msg: str, data: Any = None):
        if self.logger:
            self.logger.log_text(msg)
            if data:
                self.logger.log_code("json", json.dumps(data, indent=2, ensure_ascii=False)[:1000])
    
    async def execute(
        self,
        url: str,
        instruction: str,
        strategy: DSLStrategy = None,
        max_fallbacks: int = 3
    ) -> ExecutionResult:
        """
        Execute extraction/form filling for URL.
        
        If no strategy provided, looks up from knowledge base.
        """
        start_time = time.time()
        fallbacks_tried = []
        
        # Determine task type from instruction
        task = self._detect_task_type(instruction)
        
        self._log(f"🚀 DSL Executor: {task} on {url}")
        
        # 1. Get or create strategy
        if strategy is None:
            strategy = await self._get_strategy(url, task, instruction)
        
        self._log("📋 Strategy", strategy.to_dict())
        
        # 2. Get algorithm order
        algorithms = self._get_algorithm_order(strategy, url, task)
        self._log(f"🔧 Algorithm order: {algorithms}")
        
        # 3. Try algorithms in order
        result_data = None
        algorithm_used = None
        issues = []
        
        for algorithm in algorithms[:max_fallbacks + 1]:
            self._log(f"⚡ Trying algorithm: {algorithm}")
            
            try:
                result_data = await self._execute_algorithm(
                    algorithm, url, instruction, strategy
                )
                
                if result_data:
                    algorithm_used = algorithm
                    self._log(f"✅ Success with {algorithm}")
                    break
                else:
                    fallbacks_tried.append(algorithm)
                    self._log(f"⚠️ No results from {algorithm}")
                    
            except Exception as e:
                fallbacks_tried.append(algorithm)
                issues.append(f"{algorithm}: {str(e)}")
                self._log(f"❌ Error in {algorithm}: {e}")
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # 4. Validate results
        validation_score = 0.0
        suggestions = []
        
        if result_data:
            validation = await self.validator.validate(
                result_data,
                instruction,
                expected_fields=strategy.expected_fields or ['name', 'price', 'url'],
                min_items=strategy.min_items,
                use_llm=True
            )
            validation_score = validation.score
            issues.extend(validation.issues)
            suggestions = validation.suggestions
            
            self._log(f"📊 Validation score: {validation_score:.2f}")
        
        # 5. Record execution
        success = result_data is not None and validation_score >= 0.5
        
        record = StrategyRecord(
            url=url,
            domain=urlparse(url).netloc,
            task=task,
            algorithm=algorithm_used or algorithms[0],
            selector=strategy.selector,
            fields=strategy.fields,
            success=success,
            items_extracted=len(result_data) if isinstance(result_data, list) else 1 if result_data else 0,
            execution_time_ms=execution_time_ms,
            error_message="; ".join(issues[:3]) if issues else "",
        )
        
        self.kb.record_execution(record)
        
        # 6. Save successful strategy to DSL file
        if success and algorithm_used:
            strategy.algorithm = algorithm_used
            strategy.success_rate = (strategy.success_rate * strategy.use_count + 1.0) / (strategy.use_count + 1)
            strategy.use_count += 1
            strategy.last_used = datetime.now().isoformat()
            
            dsl_path = self.parser.save_strategy(strategy, self.dsl_dir)
            self._log(f"💾 Saved strategy to {dsl_path}")
            
            record.dsl_file = dsl_path
        
        return ExecutionResult(
            success=success,
            data=result_data,
            strategy_used=strategy,
            algorithm_used=algorithm_used or "none",
            execution_time_ms=execution_time_ms,
            validation_score=validation_score,
            issues=issues,
            suggestions=suggestions,
            fallbacks_tried=fallbacks_tried
        )
    
    def _detect_task_type(self, instruction: str) -> str:
        """Detect task type from instruction."""
        instruction_lower = instruction.lower()
        
        if any(kw in instruction_lower for kw in ['fill', 'wypełnij', 'form', 'formularz', 'submit']):
            return 'fill_form'
        elif any(kw in instruction_lower for kw in ['product', 'produkt', 'price', 'cena', 'extract']):
            return 'extract_products'
        elif any(kw in instruction_lower for kw in ['link', 'url', 'href']):
            return 'extract_links'
        elif any(kw in instruction_lower for kw in ['screenshot', 'zrzut']):
            return 'screenshot'
        else:
            return 'extract'
    
    async def _get_strategy(
        self, 
        url: str, 
        task: str, 
        instruction: str
    ) -> DSLStrategy:
        """Get strategy from knowledge base or create new one."""
        
        # Try knowledge base first
        kb_strategy = self.kb.get_best_strategy(url, task)
        
        if kb_strategy:
            self._log(f"📚 Found strategy in KB (success_rate: {kb_strategy['success_rate']:.2f})")
            return DSLStrategy(
                url_pattern=kb_strategy['url_pattern'],
                task=task,
                algorithm=kb_strategy['algorithm'],
                selector=kb_strategy['selector'],
                fields=kb_strategy['fields'],
                success_rate=kb_strategy['success_rate'],
                use_count=kb_strategy['use_count'],
                source_file=kb_strategy.get('dsl_file', '')
            )
        
        # Try to load from DSL file
        dsl_files = self._find_dsl_files(url, task)
        if dsl_files:
            strategy = self.parser.parse_file(dsl_files[0])
            self._log(f"📄 Loaded from DSL file: {dsl_files[0]}")
            return strategy
        
        # Create new strategy
        self._log("🆕 Creating new strategy")
        
        # Parse instruction for fields and filters
        fields, filter_expr = self._parse_instruction(instruction)
        
        return DSLStrategy(
            url_pattern=f"*{urlparse(url).netloc}/*",
            task=task,
            algorithm="auto",
            fields=fields,
            filter_expr=filter_expr,
            expected_fields=list(fields.keys()) or ['name', 'price', 'url']
        )
    
    def _find_dsl_files(self, url: str, task: str) -> List[str]:
        """Find DSL files matching URL pattern."""
        from pathlib import Path
        import fnmatch
        
        dsl_path = Path(self.dsl_dir)
        if not dsl_path.exists():
            return []
        
        domain = urlparse(url).netloc
        matching = []
        
        for dsl_file in list(dsl_path.glob("*.yaml")) + list(dsl_path.glob("*.dsl")):
            try:
                strategy = self.parser.parse_file(str(dsl_file))
                
                # Check if URL matches pattern
                if fnmatch.fnmatch(domain, strategy.url_pattern.replace('*', '')):
                    if strategy.task == task or strategy.task == 'extract':
                        matching.append(str(dsl_file))
            except Exception:
                continue
        
        return matching
    
    def _parse_instruction(self, instruction: str) -> tuple:
        """Parse instruction for fields and filters."""
        import re
        
        fields = {}
        filter_expr = ""
        
        # Detect fields from instruction
        instruction_lower = instruction.lower()
        
        if 'product' in instruction_lower or 'produkt' in instruction_lower:
            fields = {'name': '', 'price': '', 'url': ''}
        if 'price' in instruction_lower or 'cena' in instruction_lower:
            fields['price'] = ''
        if 'name' in instruction_lower or 'nazwa' in instruction_lower:
            fields['name'] = ''
        if 'link' in instruction_lower or 'url' in instruction_lower:
            fields['url'] = ''
        if 'image' in instruction_lower or 'obrazek' in instruction_lower:
            fields['image'] = ''
        
        # Detect filter from instruction
        price_filter = re.search(r'(?:under|below|pod|ponizej|<)\s*(\d+)', instruction_lower)
        if price_filter:
            filter_expr = f"price < {price_filter.group(1)}"
        
        price_filter_above = re.search(r'(?:over|above|powyzej|>)\s*(\d+)', instruction_lower)
        if price_filter_above:
            filter_expr = f"price > {price_filter_above.group(1)}"
        
        return fields, filter_expr
    
    def _get_algorithm_order(
        self, 
        strategy: DSLStrategy, 
        url: str, 
        task: str
    ) -> List[str]:
        """Get algorithm execution order based on strategy and KB."""
        
        # If strategy specifies algorithm, use it first
        algorithms = []
        
        if strategy.algorithm and strategy.algorithm != "auto":
            algorithms.append(strategy.algorithm)
        
        # Add fallbacks from strategy
        algorithms.extend(strategy.fallback_algorithms)
        
        # Add KB suggestions
        kb_suggestions = self.kb.suggest_algorithms(url, task)
        for alg in kb_suggestions:
            if alg not in algorithms:
                algorithms.append(alg)
        
        # Ensure at least default algorithms
        defaults = ['statistical_containers', 'pattern_detection', 'fallback_links']
        for alg in defaults:
            if alg not in algorithms:
                algorithms.append(alg)
        
        return algorithms
    
    # =========================================================================
    # ALGORITHM IMPLEMENTATIONS
    # =========================================================================
    
    async def _execute_algorithm(
        self,
        algorithm: str,
        url: str,
        instruction: str,
        strategy: DSLStrategy
    ) -> Optional[Any]:
        """Execute specific algorithm."""
        
        method_name = self.ALGORITHMS.get(algorithm)
        if method_name and hasattr(self, method_name):
            method = getattr(self, method_name)
            return await method(url, instruction, strategy)
        
        return None
    
    async def _execute_statistical(
        self,
        url: str,
        instruction: str,
        strategy: DSLStrategy
    ) -> Optional[List[Dict]]:
        """Execute statistical container detection."""
        if not self.toolkit_available:
            return None
        
        # Find repeating containers
        containers = await self.patterns.find_repeating_containers(
            self.page,
            min_count=5,
            require_links=True,
            require_price_signals=True
        )
        
        if not containers:
            return None
        
        # Score and select best
        selectors = [c['selector'] for c in containers if c.get('selector')]
        scored = await self.scoring.score_containers(self.page, selectors)
        
        if not scored:
            return None
        
        best = scored[0]
        strategy.selector = best['selector']
        
        # Extract field selectors
        field_info = await self.selectors.extract_field_selectors(
            self.page, best['selector']
        )
        
        if field_info.get('found'):
            strategy.fields = {
                k: v['selector'] 
                for k, v in field_info.get('fields', {}).items() 
                if v
            }
        
        # Extract data
        return await self._extract_items(
            best['selector'],
            strategy.fields
        )
    
    async def _execute_pattern(
        self,
        url: str,
        instruction: str,
        strategy: DSLStrategy
    ) -> Optional[List[Dict]]:
        """Execute pattern-based detection."""
        if not self.toolkit_available:
            return None
        
        # Try different pattern methods
        methods = [
            self.patterns.find_list_structures,
            self.patterns.find_sibling_groups,
        ]
        
        for method in methods:
            results = await method(self.page)
            
            if results:
                # Pick best result
                best = max(results, key=lambda x: x.get('item_count', 0))
                
                if best.get('selector'):
                    strategy.selector = best['selector']
                    return await self._extract_items(best['selector'], {})
        
        return None
    
    async def _execute_llm_guided(
        self,
        url: str,
        instruction: str,
        strategy: DSLStrategy
    ) -> Optional[List[Dict]]:
        """Execute LLM-guided extraction."""
        if not self.toolkit_available:
            return None
        
        orchestrator = self.orchestrator_class(self.llm, self.logger)
        
        result = await orchestrator.extract(
            self.page,
            instruction,
            use_llm_selection=True,
            max_items=50
        )
        
        if result.get('items'):
            strategy.selector = result.get('selector_used', '')
            return result['items']
        
        return None
    
    async def _execute_fallback_table(
        self,
        url: str,
        instruction: str,
        strategy: DSLStrategy
    ) -> Optional[List[Dict]]:
        """Execute table-based extraction."""
        return await self.page.evaluate("""
            () => {
                const items = [];
                const tables = document.querySelectorAll('table');
                
                for (const table of tables) {
                    const rows = table.querySelectorAll('tr');
                    if (rows.length < 3) continue;
                    
                    for (const row of rows) {
                        const cells = row.querySelectorAll('td');
                        if (cells.length < 2) continue;
                        
                        const text = row.textContent || '';
                        const priceMatch = text.match(/(\\d+[,.]\\d{2})\\s*(?:zł|PLN)/);
                        
                        if (priceMatch) {
                            const link = row.querySelector('a[href]');
                            items.push({
                                name: cells[0]?.textContent?.trim().slice(0, 200) || '',
                                price: parseFloat(priceMatch[1].replace(',', '.')),
                                url: link?.href || ''
                            });
                        }
                    }
                }
                
                return items.length > 0 ? items : null;
            }
        """)
    
    async def _execute_fallback_links(
        self,
        url: str,
        instruction: str,
        strategy: DSLStrategy
    ) -> Optional[List[Dict]]:
        """Execute link-based extraction."""
        return await self.page.evaluate("""
            () => {
                const items = [];
                const productPatterns = [
                    /\\/\\d{4,}$/,
                    /\\/offers\\//,
                    /[_-]\\d+\\.html$/,
                    /\\/(product|produkt)\\//i
                ];
                
                for (const link of document.links) {
                    const pathname = link.pathname || '';
                    
                    if (productPatterns.some(p => p.test(pathname))) {
                        const text = link.textContent?.trim();
                        if (text && text.length > 5 && text.length < 200) {
                            items.push({
                                name: text,
                                url: link.href,
                                price: null
                            });
                        }
                    }
                }
                
                // Dedupe by URL
                const seen = new Set();
                return items.filter(item => {
                    if (seen.has(item.url)) return false;
                    seen.add(item.url);
                    return true;
                }).slice(0, 50);
            }
        """)
    
    async def _execute_form_fill(
        self,
        url: str,
        instruction: str,
        strategy: DSLStrategy
    ) -> Optional[Dict]:
        """Execute form filling."""
        # Parse form data from instruction
        import re
        
        form_data = {}
        
        # Parse key=value pairs
        pairs = re.findall(r'(\w+)\s*[=:]\s*([^,;]+)', instruction)
        for key, value in pairs:
            form_data[key.strip()] = value.strip()
        
        if not form_data:
            return None
        
        # Fill form using existing form filler
        try:
            from ..form_filler import detect_form, fill_form_with_mapping
            
            form_info = await detect_form(self.page)
            if not form_info.get('found'):
                return None
            
            result = await fill_form_with_mapping(
                self.page,
                form_data,
                self.llm
            )
            
            return result
        except Exception as e:
            self._log(f"Form fill error: {e}")
            return None
    
    async def _extract_items(
        self,
        selector: str,
        field_selectors: Dict[str, str],
        max_items: int = 50
    ) -> List[Dict]:
        """Extract items using selector and field mappings."""
        return await self.page.evaluate("""
            (args) => {
                const containers = document.querySelectorAll(args.selector);
                const items = [];
                const pricePattern = /(\\d+[\\d\\s]*[,.]\\d{2})\\s*(?:zł|PLN|€|\\$)/i;
                
                for (let i = 0; i < Math.min(containers.length, args.maxItems); i++) {
                    const el = containers[i];
                    const item = {};
                    
                    // Name
                    if (args.fields.name) {
                        try {
                            const nameEl = el.querySelector(args.fields.name);
                            if (nameEl) item.name = nameEl.textContent?.trim();
                        } catch (e) {}
                    }
                    if (!item.name) {
                        const textEls = el.querySelectorAll('h1, h2, h3, h4, a');
                        for (const t of textEls) {
                            const txt = t.textContent?.trim();
                            if (txt && txt.length > 10 && txt.length < 200) {
                                if (!pricePattern.test(txt)) {
                                    item.name = txt;
                                    break;
                                }
                            }
                        }
                    }
                    
                    // Price
                    if (args.fields.price) {
                        try {
                            const priceEl = el.querySelector(args.fields.price);
                            if (priceEl) {
                                const match = priceEl.textContent?.match(pricePattern);
                                if (match) {
                                    item.price = parseFloat(match[1].replace(/\\s/g, '').replace(',', '.'));
                                }
                            }
                        } catch (e) {}
                    }
                    if (!item.price) {
                        const match = (el.textContent || '').match(pricePattern);
                        if (match) {
                            item.price = parseFloat(match[1].replace(/\\s/g, '').replace(',', '.'));
                        }
                    }
                    
                    // URL
                    if (args.fields.url) {
                        try {
                            const urlEl = el.querySelector(args.fields.url);
                            if (urlEl?.href) item.url = urlEl.href;
                        } catch (e) {}
                    }
                    if (!item.url) {
                        const link = el.querySelector('a[href]');
                        if (link?.href) item.url = link.href;
                    }
                    
                    // Image
                    const img = el.querySelector('img[src]');
                    if (img?.src) item.image = img.src;
                    
                    if (item.name || item.url) {
                        items.push(item);
                    }
                }
                
                return items;
            }
        """, {
            "selector": selector,
            "fields": field_selectors,
            "maxItems": max_items
        })
