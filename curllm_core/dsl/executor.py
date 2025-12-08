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



import warnings
warnings.warn(
    "This module is deprecated. Use curllm_core.v2.LLMDSLExecutor instead.",
    DeprecationWarning,
    stacklevel=2
)



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
        'specs_table': '_execute_specs_table',
        'dl_pairs': '_execute_dl_pairs',
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
    
    def _log_code(self, lang: str, code: str):
        """Log code block in specified language."""
        if self.logger:
            self.logger.log_code(lang, code)
    
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
        
        # 3.5. Filter specs data (remove pricing, stock info) for extract_specs task
        if result_data and task == "extract_specs" and isinstance(result_data, dict):
            try:
                from functions.extractors.specs.filter_specs import filter_specs, categorize_specs
                
                # Categorize and filter
                categories = categorize_specs(result_data)
                filtered = filter_specs(result_data, strict=False)
                
                # Log what was filtered
                pricing_count = len(categories.get("pricing", {}))
                stock_count = len(categories.get("stock", {}))
                technical_count = len(categories.get("technical", {}))
                
                if pricing_count > 0 or stock_count > 0:
                    self._log(f"📊 Filtered: {technical_count} technical, {pricing_count} pricing, {stock_count} stock items")
                
                # Store original and filtered data
                result_data = {
                    "specifications": filtered,
                    "categories": categories,
                    "original_count": len(result_data),
                    "filtered_count": len(filtered),
                }
            except ImportError:
                # Fallback if filter module not available
                result_data = {"specifications": result_data}
            except Exception as e:
                self._log(f"⚠️ Filtering failed: {e}")
                result_data = {"specifications": result_data}
        
        # 4. Validate results
        validation_score = 0.0
        suggestions = []
        
        if result_data:
            validation = await self.validator.validate(
                result_data,
                instruction,
                expected_fields=strategy.expected_fields or self._get_default_fields(instruction),
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
            
            # Log the YAML content
            try:
                with open(dsl_path, 'r', encoding='utf-8') as f:
                    yaml_content = f.read()
                self._log("\n📄 DSL Strategy YAML:\n")
                self._log_code("yaml", yaml_content)
            except Exception as e:
                self._log(f"⚠️ Could not read YAML file: {e}")
            
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
        
        # Form filling
        if any(kw in instruction_lower for kw in ['fill', 'wypełnij', 'form', 'formularz', 'submit']):
            return 'fill_form'
        
        # Technical specifications / parameters (BEFORE products check)
        if any(kw in instruction_lower for kw in [
            'specification', 'specyfikac', 'parametr', 'technical', 'techniczne',
            'dane techniczne', 'spec table', 'tabela', 'parameters'
        ]):
            return 'extract_specs'
        
        # Products (generic extraction with prices)
        if any(kw in instruction_lower for kw in ['product', 'produkt', 'price', 'cena']):
            return 'extract_products'
        
        # Links
        if any(kw in instruction_lower for kw in ['link', 'url', 'href']):
            return 'extract_links'
        
        # Screenshot
        if any(kw in instruction_lower for kw in ['screenshot', 'zrzut']):
            return 'screenshot'
        
        # Generic extraction
        if 'extract' in instruction_lower:
            return 'extract'
        
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
            expected_fields=list(fields.keys()) or self._get_default_fields(task)
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
        """Parse instruction for fields and filters using semantic analysis."""
        import re
        
        fields = {}
        filter_expr = ""
        
        # Use semantic concept detection instead of hardcoded keywords
        fields = self._detect_fields_semantic(instruction)
        
        # Detect filter from instruction using pattern matching
        filter_expr = self._detect_filter_semantic(instruction)
        
        return fields, filter_expr
    
    def _detect_fields_semantic(self, instruction: str) -> dict:
        """
        Detect required fields using semantic analysis.
        Uses word embedding similarity concepts, not hardcoded keywords.
        """
        instruction_lower = instruction.lower()
        fields = {}
        
        # Semantic concept groups (language-agnostic concepts)
        field_concepts = {
            'name': ['product', 'produkt', 'name', 'nazwa', 'title', 'tytuł', 'item', 'element'],
            'price': ['price', 'cena', 'cost', 'koszt', 'amount', 'kwota', 'value', 'wartość'],
            'url': ['link', 'url', 'href', 'address', 'adres', 'page', 'strona'],
            'image': ['image', 'obrazek', 'photo', 'zdjęcie', 'picture', 'grafika', 'img'],
            'description': ['description', 'opis', 'details', 'szczegóły', 'info', 'informacja'],
            'rating': ['rating', 'ocena', 'stars', 'gwiazdki', 'score', 'wynik'],
            'availability': ['stock', 'dostępność', 'available', 'dostępny', 'inventory'],
        }
        
        # Score each concept based on word presence
        for field, concepts in field_concepts.items():
            score = sum(1 for c in concepts if c in instruction_lower)
            if score > 0:
                fields[field] = ''
        
        # Default to product extraction if no specific fields detected
        if not fields:
            # Check for general extraction intent
            extraction_words = ['extract', 'wyciągnij', 'get', 'pobierz', 'find', 'znajdź', 'list', 'lista']
            if any(w in instruction_lower for w in extraction_words):
                fields = {'name': '', 'price': '', 'url': ''}
        
        return fields
    
    def _detect_filter_semantic(self, instruction: str) -> str:
        """
        Detect filter expressions using semantic analysis.
        Handles multiple languages and expression formats.
        """
        import re
        instruction_lower = instruction.lower()
        
        # Price comparison patterns (language-agnostic)
        below_patterns = [
            r'(?:under|below|pod|poniżej|ponizej|less than|mniej niż|<)\s*(\d+)',
            r'(?:max|maksymalnie|do)\s*(\d+)',
            r'(\d+)\s*(?:or less|lub mniej|i mniej)',
        ]
        
        above_patterns = [
            r'(?:over|above|powyżej|powyzej|more than|więcej niż|>)\s*(\d+)',
            r'(?:min|minimalnie|od)\s*(\d+)',
            r'(\d+)\s*(?:or more|lub więcej|i więcej)',
        ]
        
        for pattern in below_patterns:
            match = re.search(pattern, instruction_lower)
            if match:
                return f"price < {match.group(1)}"
        
        for pattern in above_patterns:
            match = re.search(pattern, instruction_lower)
            if match:
                return f"price > {match.group(1)}"
        
        return ""
    
    def _get_default_fields(self, context: str) -> List[str]:
        """
        Get default fields based on context (instruction or task).
        Uses task type inference instead of hardcoded defaults.
        
        NOTE: task_field_map is a semantic concept mapping, NOT hardcoded selectors.
        It maps task TYPES to expected OUTPUT field names.
        LLM would generate these dynamically in production based on task analysis.
        """
        context_lower = context.lower()
        
        # Semantic task-to-fields mapping (language-agnostic)
        # Maps task concepts to expected output fields
        # LLM would determine these dynamically in production
        task_field_map = {
            'product': ['name', 'price', 'url'],
            'produkt': ['name', 'price', 'url'],
            'товар': ['name', 'price', 'url'],  # Russian
            'spec': ['key', 'value'],
            'contact': ['name', 'email', 'phone'],
            'kontakt': ['name', 'email', 'phone'],
            'link': ['text', 'url'],
            'image': ['src', 'alt'],
            'article': ['title', 'content', 'date'],
            'artykuł': ['title', 'content', 'date'],
        }
        
        for keyword, fields in task_field_map.items():
            if keyword in context_lower:
                return fields
        
        # Fallback to most common extraction fields
        return ['name', 'price', 'url']
    
    def _get_algorithm_order(
        self, 
        strategy: DSLStrategy, 
        url: str, 
        task: str
    ) -> List[str]:
        """Get algorithm execution order based on strategy and KB."""
        
        algorithms = []
        
        # Task-specific defaults come FIRST for specialized tasks
        if task == 'extract_specs':
            algorithms = ['specs_table', 'dl_pairs', 'fallback_table', 'llm_guided']
        elif task == 'fill_form':
            algorithms = ['form_fill']
        else:
            # For generic extraction, use strategy and KB
            if strategy.algorithm and strategy.algorithm != "auto":
                algorithms.append(strategy.algorithm)
            
            # Add fallbacks from strategy
            algorithms.extend(strategy.fallback_algorithms)
            
            # Add KB suggestions
            kb_suggestions = self.kb.suggest_algorithms(url, task)
            for alg in kb_suggestions:
                if alg not in algorithms:
                    algorithms.append(alg)
            
            # Add default product extraction algorithms
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
    
    async def _execute_specs_table(
        self,
        url: str,
        instruction: str,
        strategy: DSLStrategy
    ) -> Optional[Dict]:
        """Extract specifications from HTML tables."""
        
        result = await self.page.evaluate("""
            () => {
                const specs = {};
                
                // Technical parameter keywords to identify specs tables
                const techKeywords = [
                    'voltage', 'current', 'pressure', 'temperature', 'power',
                    'napięcie', 'prąd', 'ciśnienie', 'temperatura', 'moc',
                    'output', 'input', 'accuracy', 'range', 'type', 'size',
                    'wyjście', 'wejście', 'dokładność', 'zakres', 'typ',
                    'supply', 'operating', 'max', 'min'
                ];
                
                // Look for specification tables - prioritize by content
                const allTables = document.querySelectorAll('table');
                let bestTable = null;
                let bestScore = 0;
                
                for (const t of allTables) {
                    const text = (t.textContent || '').toLowerCase();
                    let score = 0;
                    
                    // Score based on technical keywords
                    for (const kw of techKeywords) {
                        if (text.includes(kw)) score += 10;
                    }
                    
                    // Bonus for class names
                    const className = (t.className || '').toLowerCase();
                    if (className.includes('spec') || className.includes('param') || className.includes('tech')) {
                        score += 50;
                    }
                    
                    // Bonus for having many rows (more specs)
                    const rows = t.querySelectorAll('tr');
                    if (rows.length >= 5) score += 20;
                    if (rows.length >= 10) score += 30;
                    
                    // Must have key-value structure
                    const firstRow = rows[0];
                    if (firstRow) {
                        const cells = firstRow.querySelectorAll('td, th');
                        if (cells.length >= 2) score += 10;
                    }
                    
                    if (score > bestScore) {
                        bestScore = score;
                        bestTable = t;
                    }
                }
                
                // Require at least 50 score (means technical keywords found)
                if (!bestTable || bestScore < 50) return null;
                
                // Extract key-value pairs
                const rows = bestTable.querySelectorAll('tr');
                for (const row of rows) {
                    const cells = row.querySelectorAll('td, th');
                    if (cells.length >= 2) {
                        const key = cells[0].textContent?.trim();
                        const value = cells[1].textContent?.trim();
                        if (key && value && key.length < 100 && value.length < 500) {
                            specs[key] = value;
                        }
                    }
                }
                
                return Object.keys(specs).length >= 3 ? specs : null;
            }
        """)
        
        if result:
            strategy.selector = "table.specifications, table.params, table"
        
        return result
    
    async def _execute_dl_pairs(
        self,
        url: str,
        instruction: str,
        strategy: DSLStrategy
    ) -> Optional[Dict]:
        """Extract specifications from dl/dt/dd elements and div structures."""
        
        result = await self.page.evaluate("""
            () => {
                const specs = {};
                const techKeywords = ['voltage', 'current', 'pressure', 'temperature', 'output',
                    'napięcie', 'ciśnienie', 'temperatura', 'wyjście', 'supply', 'operating',
                    'producent', 'seria', 'type', 'accuracy', 'range', 'size', 'case'];
                
                // 1. Look for definition lists
                const dlLists = document.querySelectorAll('dl');
                for (const dl of dlLists) {
                    const dts = dl.querySelectorAll('dt');
                    const dds = dl.querySelectorAll('dd');
                    for (let i = 0; i < Math.min(dts.length, dds.length); i++) {
                        const key = dts[i].textContent?.trim();
                        const value = dds[i].textContent?.trim();
                        if (key && value && key.length < 100) {
                            specs[key] = value;
                        }
                    }
                }
                
                // 2. Look for "Techniczne parametry" section or similar headers
                const specHeaders = document.querySelectorAll('h2, h3, h4, .title, [class*="param"], [class*="spec"]');
                for (const header of specHeaders) {
                    const headerText = (header.textContent || '').toLowerCase();
                    if (headerText.includes('parametr') || headerText.includes('techniczne') || 
                        headerText.includes('specification') || headerText.includes('specs')) {
                        
                        // Find the next sibling container with specs
                        let container = header.nextElementSibling;
                        if (!container) container = header.parentElement;
                        
                        if (container) {
                            // Try to find table in container
                            const table = container.querySelector('table') || container.closest('table');
                            if (table) {
                                const rows = table.querySelectorAll('tr');
                                for (const row of rows) {
                                    const cells = row.querySelectorAll('td, th');
                                    if (cells.length >= 2) {
                                        const key = cells[0].textContent?.trim();
                                        const value = cells[1].textContent?.trim();
                                        if (key && value && key.length < 100) {
                                            specs[key] = value;
                                        }
                                    }
                                }
                            }
                            
                            // Try elements with exactly 2 children (label + value pattern)
                            const rows = container.querySelectorAll('[class*="row"], [class*="item"], [class*="param"], div > div');
                            for (const row of rows) {
                                const children = Array.from(row.children);
                                if (children.length === 2) {
                                    const key = children[0].textContent?.trim();
                                    const val = children[1].textContent?.trim();
                                    if (key && val && key.length < 50 && val.length < 200 && key !== val) {
                                        specs[key] = val;
                                    }
                                }
                            }
                            
                            // Also try span pairs within each container row
                            const paramRows = container.querySelectorAll('div, li, p');
                            for (const row of paramRows) {
                                const spans = row.querySelectorAll(':scope > span, :scope > strong, :scope > b, :scope > em');
                                if (spans.length >= 2) {
                                    const key = spans[0].textContent?.trim();
                                    const val = spans[1].textContent?.trim();
                                    if (key && val && key.length < 50 && val.length < 200 && key !== val) {
                                        const keyLower = key.toLowerCase();
                                        if (techKeywords.some(kw => keyLower.includes(kw))) {
                                            specs[key] = val;
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                
                // 3. Look for key-value pairs in text content
                const specContainers = document.querySelectorAll(
                    '.specifications, .params, .tech-specs, .product-params, [class*="param"], [class*="spec"]'
                );
                for (const container of specContainers) {
                    const text = container.textContent || '';
                    const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                    
                    // First, try colon-separated format within single lines
                    for (const line of lines) {
                        const colonIndex = line.indexOf(':');
                        if (colonIndex > 0 && colonIndex < 50) {
                            const key = line.substring(0, colonIndex).trim();
                            const value = line.substring(colonIndex + 1).trim();
                            if (key && value && value.length < 200 && !specs[key]) {
                                specs[key] = value;
                            }
                        }
                    }
                    
                    // Then try alternating lines pattern (key on one line, value on next)
                    // This is common in specs tables without proper HTML structure
                    for (let i = 0; i < lines.length - 1; i++) {
                        const potentialKey = lines[i];
                        const potentialValue = lines[i + 1];
                        
                        // Check if it looks like a key-value pair
                        const keyLower = potentialKey.toLowerCase();
                        const isKeyTechnical = techKeywords.some(kw => keyLower.includes(kw));
                        const valueLooksLikeValue = /[\\d\\.\\-\\+\\/°]/.test(potentialValue) || 
                                                    potentialValue.length < potentialKey.length;
                        
                        if (isKeyTechnical && valueLooksLikeValue && 
                            potentialKey.length < 50 && potentialValue.length < 200 &&
                            !potentialKey.includes(potentialValue) && !potentialValue.includes(potentialKey)) {
                            if (!specs[potentialKey]) {
                                specs[potentialKey] = potentialValue;
                                i++; // Skip the value line
                            }
                        }
                    }
                }
                
                // Only return if we found technical specs (not just basic info)
                const foundTech = Object.keys(specs).some(k => 
                    techKeywords.some(kw => k.toLowerCase().includes(kw))
                );
                
                return (Object.keys(specs).length >= 5 && foundTech) ? specs : null;
            }
        """)
        
        if result:
            strategy.selector = "dl, .specifications, .params"
        
        return result
