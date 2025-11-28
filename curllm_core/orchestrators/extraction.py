"""
Extraction Orchestrator - Specialized orchestrator for data extraction tasks

Handles:
- Product extraction (prices, names, URLs)
- Link extraction
- Article/content extraction
- Email/phone extraction
- Table data extraction
"""

import json
import re
from typing import Any, Dict, List, Optional


class ExtractionOrchestrator:
    """
    Specialized orchestrator for data extraction tasks.
    
    Workflow:
    1. Detect extraction type from instruction
    2. Analyze page structure
    3. Apply extraction strategy
    4. Filter by constraints (price, count, etc.)
    5. Validate extracted data
    """
    
    def __init__(self, llm=None, page=None, run_logger=None):
        self.llm = llm
        self.page = page
        self.run_logger = run_logger
    
    async def orchestrate(
        self,
        instruction: str,
        page_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute extraction workflow.
        
        Args:
            instruction: User's extraction instruction
            page_context: Current page state
            
        Returns:
            Extracted data with validation
        """
        self._log("📊 EXTRACTION ORCHESTRATOR", "header")
        
        result = {
            'success': True,
            'extraction_type': None,
            'count': 0
        }
        
        try:
            # Phase 1: Detect extraction type
            extraction_type = self._detect_extraction_type(instruction)
            result['extraction_type'] = extraction_type
            self._log(f"Extraction type: {extraction_type}")
            
            # Phase 2: Parse constraints
            constraints = self._parse_constraints(instruction)
            self._log(f"Constraints: {constraints}")
            
            # Phase 3: Scroll to load content if needed
            if self._needs_scroll(instruction):
                await self._scroll_page(times=6)
            
            # Phase 4: Execute extraction
            if extraction_type == 'products':
                data = await self._extract_products(constraints)
            elif extraction_type == 'links':
                data = await self._extract_links(constraints)
            elif extraction_type == 'articles':
                data = await self._extract_articles(constraints)
            elif extraction_type == 'emails':
                data = await self._extract_emails()
            elif extraction_type == 'phones':
                data = await self._extract_phones()
            elif extraction_type == 'tables':
                data = await self._extract_tables()
            else:
                data = await self._extract_generic(instruction)
            
            result[extraction_type] = data
            result['count'] = len(data) if isinstance(data, list) else 1
            
            # Phase 5: Apply constraints
            if constraints and isinstance(data, list):
                filtered = self._apply_constraints(data, constraints)
                result[extraction_type] = filtered
                result['count'] = len(filtered)
                result['filtered_from'] = len(data)
            
            self._log(f"Extracted {result['count']} items")
            
        except Exception as e:
            result['success'] = False
            result['error'] = str(e)
            self._log(f"Extraction failed: {e}", "error")
        
        return result
    
    def _detect_extraction_type(self, instruction: str) -> str:
        """Detect type of data to extract"""
        instr_lower = instruction.lower()
        
        if any(kw in instr_lower for kw in ['product', 'produkt', 'price', 'cena', 'shop', 'sklep']):
            return 'products'
        elif any(kw in instr_lower for kw in ['email', 'e-mail', 'mail']):
            return 'emails'
        elif any(kw in instr_lower for kw in ['phone', 'telefon', 'tel', 'number']):
            return 'phones'
        elif any(kw in instr_lower for kw in ['article', 'artykuł', 'news', 'post', 'blog']):
            return 'articles'
        elif any(kw in instr_lower for kw in ['table', 'tabela', 'data', 'dane']):
            return 'tables'
        elif any(kw in instr_lower for kw in ['link', 'url', 'href']):
            return 'links'
        else:
            return 'generic'
    
    def _parse_constraints(self, instruction: str) -> Dict[str, Any]:
        """Parse extraction constraints from instruction"""
        constraints = {}
        instr_lower = instruction.lower()
        
        # Price constraints
        price_max = re.search(r'(under|below|max|poniżej|do|maksymalnie)\s*(\d+)', instr_lower)
        if price_max:
            constraints['max_price'] = int(price_max.group(2))
        
        price_min = re.search(r'(above|over|min|powyżej|od|minimalnie)\s*(\d+)', instr_lower)
        if price_min:
            constraints['min_price'] = int(price_min.group(2))
        
        # Count constraints
        count_match = re.search(r'(first|top|pierwsz\w+)\s*(\d+)', instr_lower)
        if count_match:
            constraints['max_count'] = int(count_match.group(2))
        
        # Domain constraint
        domain_match = re.search(r'from\s+([\w.-]+\.\w+)', instr_lower)
        if domain_match:
            constraints['domain'] = domain_match.group(1)
        
        return constraints
    
    def _needs_scroll(self, instruction: str) -> bool:
        """Check if page needs scrolling to load content"""
        keywords = ['all', 'wszystkie', 'load', 'scroll', 'więcej', 'more']
        return any(kw in instruction.lower() for kw in keywords)
    
    async def _scroll_page(self, times: int = 5):
        """Scroll page to load dynamic content"""
        if not self.page:
            return
        
        for i in range(times):
            await self.page.evaluate('window.scrollBy(0, window.innerHeight)')
            await self.page.wait_for_timeout(800)
    
    async def _extract_products(self, constraints: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract product data from page"""
        if not self.page:
            return []
        
        try:
            products = await self.page.evaluate('''() => {
                const containers = document.querySelectorAll(
                    '[class*="product"], [class*="item"], [class*="card"], ' +
                    '[data-product], article, .offer, .listing-item'
                );
                
                return Array.from(containers).slice(0, 100).map(el => {
                    // Find name
                    const nameEl = el.querySelector('h2, h3, h4, .name, .title, [class*="name"], [class*="title"]');
                    const name = nameEl?.textContent?.trim() || '';
                    
                    // Find price
                    const priceEl = el.querySelector('.price, [class*="price"], [data-price]');
                    let price = priceEl?.textContent?.trim() || '';
                    
                    // Extract numeric price
                    const priceMatch = price.match(/([\\d\\s,.]+)/);
                    const priceNum = priceMatch ? 
                        parseFloat(priceMatch[1].replace(/\\s/g, '').replace(',', '.')) : null;
                    
                    // Find URL
                    const linkEl = el.querySelector('a[href]');
                    const url = linkEl?.href || '';
                    
                    // Find image
                    const imgEl = el.querySelector('img');
                    const image = imgEl?.src || '';
                    
                    return {
                        name: name.substring(0, 200),
                        price: price,
                        price_numeric: priceNum,
                        url,
                        image
                    };
                }).filter(p => p.name && p.name.length > 3);
            }''')
            
            return products
        except Exception as e:
            self._log(f"Product extraction failed: {e}", "error")
            return []
    
    async def _extract_links(self, constraints: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract links from page"""
        if not self.page:
            return []
        
        try:
            links = await self.page.evaluate('''() => {
                return Array.from(document.querySelectorAll('a[href]'))
                    .slice(0, 200)
                    .map(a => ({
                        text: a.textContent?.trim().substring(0, 200) || '',
                        href: a.href
                    }))
                    .filter(l => l.href && !l.href.startsWith('javascript:'));
            }''')
            
            return links
        except Exception:
            return []
    
    async def _extract_articles(self, constraints: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract article data from page"""
        if not self.page:
            return []
        
        try:
            articles = await self.page.evaluate('''() => {
                const containers = document.querySelectorAll(
                    'article, .post, .article, .entry, .blog-post, ' +
                    '[class*="article"], [class*="post"]'
                );
                
                return Array.from(containers).slice(0, 50).map(el => {
                    const titleEl = el.querySelector('h1, h2, h3, .title, [class*="title"]');
                    const dateEl = el.querySelector('time, .date, [class*="date"]');
                    const excerptEl = el.querySelector('p, .excerpt, .summary, [class*="excerpt"]');
                    const linkEl = el.querySelector('a[href]');
                    
                    return {
                        title: titleEl?.textContent?.trim() || '',
                        date: dateEl?.textContent?.trim() || dateEl?.getAttribute('datetime') || '',
                        excerpt: excerptEl?.textContent?.trim().substring(0, 300) || '',
                        url: linkEl?.href || ''
                    };
                }).filter(a => a.title);
            }''')
            
            return articles
        except Exception:
            return []
    
    async def _extract_emails(self) -> List[str]:
        """Extract email addresses from page"""
        if not self.page:
            return []
        
        try:
            text = await self.page.evaluate('() => document.body.textContent')
            emails = list(set(re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', text)))
            return emails[:50]
        except Exception:
            return []
    
    async def _extract_phones(self) -> List[str]:
        """Extract phone numbers from page"""
        if not self.page:
            return []
        
        try:
            text = await self.page.evaluate('() => document.body.textContent')
            # Polish and international phone patterns
            patterns = [
                r'\+48\s?\d{3}\s?\d{3}\s?\d{3}',
                r'\d{3}[\s-]?\d{3}[\s-]?\d{3}',
                r'\(\d{2,3}\)\s?\d{3}[\s-]?\d{2}[\s-]?\d{2}'
            ]
            phones = []
            for pattern in patterns:
                phones.extend(re.findall(pattern, text))
            return list(set(phones))[:30]
        except Exception:
            return []
    
    async def _extract_tables(self) -> List[Dict[str, Any]]:
        """Extract table data from page"""
        if not self.page:
            return []
        
        try:
            tables = await self.page.evaluate('''() => {
                return Array.from(document.querySelectorAll('table')).map(table => {
                    const headers = Array.from(table.querySelectorAll('th'))
                        .map(th => th.textContent?.trim() || '');
                    
                    const rows = Array.from(table.querySelectorAll('tbody tr')).map(tr => {
                        return Array.from(tr.querySelectorAll('td'))
                            .map(td => td.textContent?.trim() || '');
                    });
                    
                    return { headers, rows };
                });
            }''')
            
            return tables
        except Exception:
            return []
    
    async def _extract_generic(self, instruction: str) -> Dict[str, Any]:
        """Generic extraction based on instruction"""
        if not self.page:
            return {}
        
        try:
            data = await self.page.evaluate('''() => {
                return {
                    title: document.title,
                    url: window.location.href,
                    headings: Array.from(document.querySelectorAll('h1, h2, h3'))
                        .slice(0, 10)
                        .map(h => h.textContent?.trim()),
                    paragraphs: Array.from(document.querySelectorAll('p'))
                        .slice(0, 10)
                        .map(p => p.textContent?.trim().substring(0, 200))
                };
            }''')
            
            return data
        except Exception:
            return {}
    
    def _apply_constraints(
        self,
        data: List[Dict[str, Any]],
        constraints: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply constraints to filter extracted data"""
        filtered = data
        
        # Price filter
        if 'max_price' in constraints:
            max_price = constraints['max_price']
            filtered = [
                item for item in filtered
                if item.get('price_numeric') is None or item.get('price_numeric') <= max_price
            ]
        
        if 'min_price' in constraints:
            min_price = constraints['min_price']
            filtered = [
                item for item in filtered
                if item.get('price_numeric') is None or item.get('price_numeric') >= min_price
            ]
        
        # Count limit
        if 'max_count' in constraints:
            filtered = filtered[:constraints['max_count']]
        
        # Domain filter
        if 'domain' in constraints:
            domain = constraints['domain'].lower()
            filtered = [
                item for item in filtered
                if domain in item.get('url', '').lower() or domain in item.get('href', '').lower()
            ]
        
        return filtered
    
    def _log(self, message: str, level: str = "info"):
        """Log message"""
        if self.run_logger:
            if level == "header":
                self.run_logger.log_text(f"\n{'='*50}")
                self.run_logger.log_text(message)
                self.run_logger.log_text(f"{'='*50}\n")
            elif level == "error":
                self.run_logger.log_text(f"❌ {message}")
            else:
                self.run_logger.log_text(f"   {message}")

