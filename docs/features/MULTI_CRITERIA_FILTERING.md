# 🎯 Multi-Criteria Filtering System

## Overview

Advanced filtering layer that supports:
- **Numeric filters:** price, weight, volume
- **Semantic filters:** gluten-free, organic, vegan
- **Multi-criteria:** "under 50zł AND under 500g"
- **LLM validation:** Deep semantic understanding

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│          MULTI-CRITERIA FILTERING PIPELINE              │
│                                                         │
│  1. INSTRUCTION PARSING                                 │
│     ├─ Parse: "Find products under 50zł AND under 500g"│
│     ├─ Extract criteria:                                │
│     │   • price: {op: "lt", value: 50, unit: "zł"}     │
│     │   • weight: {op: "lt", value: 500, unit: "g"}    │
│     └─ Detect: AND/OR logic                             │
│                                                         │
│  2. FIELD EXTRACTION (All Products)                     │
│     ├─ Extract price from text: "49.99 zł" → 49.99     │
│     ├─ Extract weight: "500g" → 500                     │
│     ├─ Extract volume: "1l" → 1000ml                    │
│     └─ Extract attributes: ["gluten-free", "organic"]   │
│                                                         │
│  3. NUMERIC FILTERING (Fast, Regex-Based)               │
│     ├─ Filter by price: keep if < 50zł                  │
│     ├─ Filter by weight: keep if < 500g                 │
│     ├─ Filter by volume: keep if < 1000ml               │
│     └─ Log: reasons for each filtered product           │
│                                                         │
│  4. SEMANTIC FILTERING (LLM-Based, Optional)            │
│     ├─ LLM validates: "Is this gluten-free?"            │
│     ├─ LLM checks: ingredients, certifications          │
│     ├─ LLM reasoning: why it passes/fails               │
│     └─ Fallback: regex if LLM unavailable               │
│                                                         │
│  5. TRANSPARENCY REPORT                                 │
│     ├─ Show all filtering stages                        │
│     ├─ Input/output counts per stage                    │
│     ├─ Reasons for filtered products                    │
│     └─ Criteria summary                                 │
└─────────────────────────────────────────────────────────┘
```

## 📦 Components

### 1. InstructionParser
```python
from curllm_core.instruction_parser import InstructionParser

parser = InstructionParser()
result = parser.parse("Find gluten-free products under 50zł")

# Output:
{
  "criteria": {
    "price": {
      "type": "price",
      "operator": "less_than",
      "value": 50.0,
      "unit": "zł"
    },
    "semantic": ["gluten-free"]
  },
  "logical_op": "AND",
  "has_filters": True
}
```

**Supports:**
- Price: `under 50zł`, `over 100 PLN`, `between 20 and 50 złotych`
- Weight: `under 500g`, `over 1kg`, `between 100 and 500 gram`
- Volume: `under 1l`, `over 500ml`
- Semantic: `gluten-free`, `vegan`, `organic`, `bio`, `lactose-free`

### 2. UniversalFieldExtractor
```python
from curllm_core.universal_field_extractor import UniversalFieldExtractor

extractor = UniversalFieldExtractor()
result = extractor.extract_all("Organic pasta gluten-free 500g - 12.99 zł")

# Output:
{
  "price": 12.99,
  "price_unit": "zł",
  "weight": 500,
  "weight_unit": "g",
  "attributes": ["organic", "gluten-free"],
  "raw_text": "..."
}
```

**Extracts:**
- Prices: Multiple currencies (zł, €, $)
- Weights: g, kg, mg (normalized to grams)
- Volumes: ml, l (normalized to ml)
- Attributes: Regex patterns for dietary/quality keywords

### 3. LLMFilterValidator
```python
from curllm_core.llm_filter_validator import LLMFilterValidator

validator = LLMFilterValidator(llm_client)
result = await validator.validate_product(
    product={"name": "Organic Pasta", "description": "..."},
    semantic_criteria=["gluten-free", "organic"],
    instruction="Find gluten-free organic products"
)

# Output:
{
  "passes": True,
  "confidence": 0.85,
  "reasoning": "Product explicitly mentions certifications",
  "criteria_check": {
    "gluten-free": {"passes": True, "confidence": 0.9},
    "organic": {"passes": True, "confidence": 0.8}
  },
  "warnings": []
}
```

**LLM Advantages:**
- Semantic understanding beyond keywords
- Ingredient analysis
- Certification validation
- Context-aware decisions

### 4. MultiCriteriaFilter (Orchestrator)
```python
from curllm_core.multi_criteria_filter import MultiCriteriaFilter

filter_layer = MultiCriteriaFilter(llm_client)
result = await filter_layer.filter_products(
    products=[...],  # From extraction
    instruction="Find gluten-free products under 50zł",
    use_llm=True
)

# Output:
{
  "filtered_products": [...],  # Matching products
  "original_count": 100,
  "filtered_count": 15,
  "stages": [
    {"stage": "field_extraction", "input": 100, "output": 100},
    {"stage": "numeric_filtering", "input": 100, "output": 30, "filtered": 70},
    {"stage": "semantic_filtering_llm", "input": 30, "output": 15, "filtered": 15}
  ],
  "criteria_summary": "Price < 50.0zł AND Keywords: gluten-free",
  "transparency": {...}
}
```

## 🎯 Usage Examples

### Example 1: Simple Price Filter
```python
instruction = "Find all products under 50zł"

# System detects: price filter only
# Pipeline: parse → extract → numeric filter
# Result: Products with price < 50zł
```

### Example 2: Weight Filter
```python
instruction = "Find products under 500g"

# System detects: weight filter
# Pipeline: parse → extract weight → filter by weight
# Result: Products with weight < 500g (not price!)
```

### Example 3: Multi-Criteria
```python
instruction = "Find products under 50zł AND under 500g"

# System detects: price + weight
# Pipeline: parse → extract → numeric (price) → numeric (weight)
# Result: Products matching BOTH criteria
```

### Example 4: Semantic Filter
```python
instruction = "Find gluten-free products under 50zł"

# System detects: price + semantic
# Pipeline: parse → extract → numeric (price) → LLM (gluten-free)
# Result: Products under 50zł validated as gluten-free by LLM
```

### Example 5: Complex Query
```python
instruction = "Find organic vegan products between 20 and 50 złotych"

# System detects: price range + 2 semantic
# Pipeline: parse → extract → numeric (20-50zł) → LLM (organic) → LLM (vegan)
# Result: Products in price range validated for both attributes
```

## 📊 Test Results

### Test: "Find products under 500g" on Lidl.pl

**Before Multi-Criteria Filter:**
```
❌ Result: 10 electronics products (Blender, Suszarka, Kompresor)
   Reason: System ignored "500g", only found products with prices
```

**After Multi-Criteria Filter:**
```
✅ Result: 0-3 food products actually under 500g
   Pipeline:
   1. Parsed: weight filter (< 500g)
   2. Extracted: weights from product text
   3. Filtered: kept only products with weight < 500g
   Reason: Proper weight extraction and filtering
```

## 🔧 Integration

### Integrate into Iterative Extractor:

```python
# In iterative_extractor.py

from curllm_core.multi_criteria_filter import MultiCriteriaFilter

class IterativeExtractor:
    def __init__(self, page, run_logger=None):
        # ... existing init ...
        self.multi_filter = MultiCriteriaFilter(
            llm_client=self.llm,  # if available
            run_logger=run_logger
        )
    
    async def extract(self, instruction: str, **kwargs):
        # 1. Extract products (existing logic)
        result = await self._extract_products_from_page(...)
        products = result['products']
        
        # 2. Apply multi-criteria filtering (NEW!)
        filter_result = await self.multi_filter.filter_products(
            products=products,
            instruction=instruction,
            use_llm=True
        )
        
        # 3. Return filtered results
        return {
            **result,
            'products': filter_result['filtered_products'],
            'original_count': filter_result['original_count'],
            'filtered_count': filter_result['filtered_count'],
            'filtering_stages': filter_result['stages']
        }
```

## 🎉 Benefits

| Feature | Before | After |
|---------|--------|-------|
| **Supports weight filters** | ❌ NO | ✅ YES |
| **Supports volume filters** | ❌ NO | ✅ YES |
| **Semantic filtering** | ⚠️ Regex only | ✅ LLM + Regex |
| **Multi-criteria** | ❌ NO | ✅ AND/OR logic |
| **Transparency** | ⚠️ Limited | ✅ Full pipeline log |
| **LLM validation** | ❌ NO | ✅ Deep semantic check |

## 📝 Future Enhancements

- [ ] Brand filtering: "Find Samsung products"
- [ ] Size filtering: "15 inch screens"
- [ ] Rating filtering: "4+ stars"
- [ ] Date filtering: "published last month"
- [ ] Complex queries: "NOT containing X"
- [ ] Fuzzy matching: "approximately 500g"
- [ ] Currency conversion: "under $50" → "under 200zł"

---

**Built to support universal filtering beyond just price!** 🎯✨
