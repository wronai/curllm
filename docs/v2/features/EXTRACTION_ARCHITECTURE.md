# 🏗️ Dynamic Extraction Architecture

## Overview

**ZERO HARD-CODED SELECTORS!** Complete dynamic pattern detection system for universal e-commerce extraction.

## 🎯 Core Principle

> "Never hard-code selectors. Always detect patterns dynamically from DOM structure."

## 📊 Extraction Pipeline

```
┌─────────────────────────────────────────────────────────┐
│            EXTRACTION PIPELINE (Cascade)                │
│                                                         │
│  1. LLM-Guided Extractor                               │
│     └─ LLM analyzes DOM samples                        │
│     └─ Proposes container selector                     │
│     └─ ❌ Often fails (generic suggestions)           │
│                                                         │
│  2. Dynamic Detector (Python)                          │
│     └─ Finds 100 "signal" elements (prices)            │
│     └─ Analyzes parent structures                      │
│     └─ Forms clusters by similarity                    │
│     └─ ⚠️  May filter everything if too strict         │
│                                                         │
│  3. Iterative Extractor (JavaScript) ✅ MAIN WORKER    │
│     └─ Quick page check (prices, links, structure)     │
│     └─ Dynamic container detection:                    │
│         • Find all elements with prices                │
│         • Analyze parents 1-3 levels up                │
│         • Count repeating patterns                     │
│         • Filter valid CSS class names                 │
│         • Score candidates (see below)                 │
│     └─ Field detection (name, price, url)              │
│     └─ Data extraction                                 │
│     └─ Price filtering                                 │
│     └─ ✅ Most reliable extractor                     │
│                                                         │
│  4. BQL Orchestrator                                   │
│     └─ Query-based extraction                          │
│     └─ Uses LLM for DOM analysis                       │
│                                                         │
│  5. Extraction Orchestrator                            │
│     └─ LLM-guided navigation & extraction              │
│     └─ Form filling if needed                          │
│                                                         │
│  6. Standard Planner (Fallback)                        │
│     └─ Multi-step navigation                           │
│     └─ Scrolling & clicking                            │
│     └─ Calls products.extract repeatedly               │
└─────────────────────────────────────────────────────────┘
```

## 🎯 Iterative Extractor - Smart Scoring System

### Detection Algorithm

```javascript
// 1. FIND SIGNAL ELEMENTS (prices)
const priceRegex = /\d+[\s,.]?\d*[\s,.]?\d{2}\s*(?:zł|PLN|€|\$)/i;
const signalElements = [...document.querySelectorAll('*')]
  .filter(el => priceRegex.test(el.innerText));

// 2. ANALYZE PARENTS
for (const signal of signalElements) {
  for (let depth = 0; depth < 3; depth++) {
    const parent = signal.parentElement;
    
    // Extract valid CSS classes only
    const classes = parent.className
      .split(' ')
      .filter(c => /^[a-zA-Z][a-zA-Z0-9_-]*$/.test(c));  // NO invalid chars!
    
    if (classes.length === 0) continue;  // Skip no classes
    
    const selector = parent.tagName.toLowerCase() + '.' + classes[0];
    const count = document.querySelectorAll(selector).length;
    
    if (count >= 5) {  // Must repeat
      candidates.push({
        selector,
        count,
        specificity: classes.length,
        has_price: true,  // Guaranteed (we started from price)
        has_link: !!parent.querySelector('a[href]'),
        has_image: !!parent.querySelector('img')
      });
    }
  }
}

// 3. SCORE CANDIDATES
for (const c of candidates) {
  let score = 0;
  
  // SPECIFICITY (most important!)
  if (c.specificity >= 3) score += 50;
  else if (c.specificity >= 2) score += 35;
  else if (c.specificity >= 1) score += 20;
  
  // PENALTY for generic layout classes
  const utilityClasses = ['container', 'row', 'col', 'wrapper', 'inner', 'main', ...];
  const tailwindPrefixes = ['mt-', 'mb-', 'p-', 'flex', 'grid', 'border-', ...];
  if (isLayoutClass) score -= 30;  // Heavy penalty!
  
  // SIZE (reduced importance)
  score += Math.min(c.count / 50, 1) * 15;
  
  // STRUCTURE
  score += 25;  // Has price (guaranteed)
  score += c.has_link ? 20 : 0;
  score += c.has_image ? 15 : 0;
  
  // TEXT QUALITY
  const hasProductKeywords = /laptop|phone|notebook/.test(text);
  const hasSpecs = /\d+GB|\d+GHz|Core|Ryzen/.test(text);
  const hasMarketing = /okazja|promocja|rabat/.test(text);
  
  if (hasProductKeywords) score += 15;
  if (hasSpecs) score += 20;
  if (hasMarketing) score -= 15;  // Penalty!
  
  // COMPLETE STRUCTURE bonus
  if (c.has_price && c.has_link && c.has_image) score += 10;
  
  c.score = score;
}

// 4. SELECT WINNER
candidates.sort((a, b) => b.score - a.score);
return candidates[0];  // Highest score wins!
```

### Scoring Examples

**✅ Good Product Container:**
```
li.product (e-commerce)
  + specificity(13 classes): 50
  - layout penalty: 0
  + count(49): 15
  + structure: 60
  + keywords("laptop"): 15
  + specs("16GB"): 20
  + complete: 10
  ────────────────
  = 170 points ✅
```

**❌ Generic Layout Container:**
```
div.container (layout)
  + specificity(4): 35
  - layout penalty: -30  ← KEY!
  + count(9): 6
  + structure: 60
  - marketing: -15
  ────────────────
  = 66 points ❌
```

## 🛡️ Filters & Safety

### 1. CSS Class Name Validation
```javascript
// Only allow valid CSS class names
/^[a-zA-Z][a-zA-Z0-9_-]*$/

// ❌ REJECT:
// !mt-4, xl:grid, @apply, #id, $var, [attr]

// ✅ ACCEPT:
// product-box, cat-prod-row, item123
```

### 2. Generic Selector Filter
```javascript
// Skip if no classes and generic tag
if (classes.length === 0 && tag in ['div', 'span', 'article', 'section', 'li'])
  continue;
```

### 3. Minimum Count Filter
```javascript
if (count < 5) continue;  // Must repeat at least 5 times
```

### 4. Must Have Price
```javascript
if (!has_price) continue;  // Products must have prices!
```

### 5. SVG Element Handling
```javascript
// Handle SVGAnimatedString (not plain string)
const classNameStr = typeof parent.className === 'string'
  ? parent.className
  : (parent.className?.baseVal || '');
```

## 📈 Test Results

| Site | Container Found | Products | Specificity | Score |
|------|----------------|----------|-------------|-------|
| **Komputronik** | `div.border-transparent` | 15 | 5 | 115.1 |
| **Skapiec** | `div.product-box-wide-d` | 3 | 1 | 90.0 |
| **Ceneo** | `div.cat-prod-row` | 14 | 3 | 96.0 |
| **Balta** | `li.product` | 32 | 13 | 169.7 |
| **Lidl** | `div.odsc-tile` | 10 | 4 | 124.5 |

## 🔧 Key Files

```
curllm_core/
├── extraction_registry.py      ← NEW: Transparency & tracking
├── iterative_extractor.py      ← MAIN: Dynamic detection
├── dynamic_detector.py         ← Python-based pattern detection
├── llm_guided_extractor.py     ← LLM-based container selection
├── extraction_orchestrator.py  ← High-level orchestration
├── bql_extraction_orchestrator.py
└── extraction.py               ← Legacy (redirects to new system)
```

## 🚀 Usage

### For Products:
```python
from curllm_core.iterative_extractor import IterativeExtractor

extractor = IterativeExtractor(page, run_logger)
result = await extractor.extract(
    instruction="Find products under 950zł",
    page_type="product_listing"  # or "single_product" or None (auto-detect)
)

print(f"Found: {len(result['products'])} products")
```

### With Transparency:
```python
from curllm_core.extraction_registry import ExtractionPipeline, ExtractorType

pipeline = ExtractionPipeline("Find products under 950zł", page.url)

# Try extractor
attempt = pipeline.start_attempt(ExtractorType.ITERATIVE)
# ... run extraction ...
attempt.add_detected_selector("div.product-box", 95.0, 3, 50, {...})
attempt.set_chosen_selector("div.product-box", "Highest score", {...})
attempt.set_result(ExtractorStatus.SUCCESS, products_found=50)

# Generate report
report = pipeline.get_transparency_report()
pipeline.print_transparency_log()
```

## 📝 Migration Guide

### ❌ OLD (Hard-Coded):
```python
products = await quick_extract_products(
    page,
    container_selector=".product-box",  # ← NEVER DO THIS!
    name_selector="h3",
    price_selector=".price"
)
```

### ✅ NEW (Dynamic):
```python
extractor = IterativeExtractor(page)
result = await extractor.extract(instruction="Find products")
products = result['products']
# Selectors detected automatically!
```

## 🎯 Design Principles

1. **No Hard-Coded Selectors** - Everything detected dynamically
2. **Specificity Over Count** - Prefer specific classes over generic tags
3. **Penalty-Based Filtering** - Penalize utility/layout classes
4. **Context-Aware Scoring** - Use product keywords, specs, marketing text
5. **Full Transparency** - Log everything for debugging
6. **Graceful Degradation** - Multiple fallback extractors
7. **Universal Compatibility** - Works on any e-commerce site

## 🔮 Future Enhancements

- [ ] Machine learning-based selector ranking
- [ ] Cross-page pattern learning
- [ ] Automatic schema detection
- [ ] Multi-language product recognition
- [ ] Visual element clustering

---

**Built with ❤️ for universal web extraction without configuration.**
