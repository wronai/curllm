# Vision-Based Form Analysis & Honeypot Detection

**[📚 Documentation Index](INDEX.md)** | **[⬅️ Back to Main README](../README.md)**

---

## 🎯 **Problem**

Traditional DOM-based form detection has serious limitations:

1. **Honeypot Fields** - Hidden fields designed to trap bots:
   - Fields with `display:none` or `visibility:hidden`
   - Fields positioned off-screen (`left: -9999px`)
   - Fields with zero dimensions (`width:0, height:0`)
   - Duplicate fields (e.g., two email fields, one hidden)

2. **DOM Lies** - Element attributes don't reflect actual visibility:
   - `visible:true` in DOM but CSS hides the field
   - Elements exist in DOM tree but aren't rendered
   - Z-index stacking hides fields behind other elements

3. **Field Ambiguity** - Multiple similar fields:
   - Which "email" field is the real one?
   - Confirmation fields vs primary fields
   - Required vs optional fields not always marked in DOM

---

## ✅ **Solution: Vision-Based Analysis**

### **Approach**

Use LLM with vision capabilities (multimodal) to analyze screenshot and:
1. **Verify** which fields are actually visible to users
2. **Detect** honeypot fields (in DOM but not visible)
3. **Prioritize** fields based on visual layout
4. **Map** visual labels to DOM field names

### **Decision Tree**

```
START
  ├─→ Extract page context from DOM
  │    └─→ Detect all form fields (visible: true/false)
  │
  ├─→ Take screenshot of page
  │
  ├─→ [VISION ANALYSIS]
  │    ├─→ LLM analyzes screenshot
  │    ├─→ Identifies visible input fields
  │    ├─→ Reads field labels/placeholders
  │    └─→ Compares with DOM field list
  │
  ├─→ [HONEYPOT DETECTION]
  │    ├─→ For each DOM field:
  │    │    ├─→ In DOM but NOT in screenshot? → HONEYPOT
  │    │    ├─→ Has no visible label? → SUSPICIOUS
  │    │    ├─→ Duplicate of another field? → LIKELY HONEYPOT
  │    │    └─→ Visible in screenshot → SAFE
  │    │
  │    └─→ Build honeypot list
  │
  ├─→ [FIELD PRIORITIZATION]
  │    ├─→ Assign priority scores:
  │    │    ├─→ Visible in screenshot: +100
  │    │    ├─→ Required field: +50
  │    │    ├─→ Matches instruction: +30
  │    │    ├─→ Clear label: +20
  │    │    ├─→ Is honeypot: -100
  │    │    └─→ Suspicious: -50
  │    │
  │    └─→ Sort fields by priority
  │
  ├─→ [FIELD MAPPING]
  │    ├─→ Map visual labels → canonical names
  │    │    ├─→ "Name" / "Imię" → name
  │    │    ├─→ "Email" / "Adres e-mail" → email
  │    │    ├─→ "Phone" / "Telefon" → phone
  │    │    ├─→ "Message" / "Wiadomość" → message
  │    │    └─→ "Subject" / "Temat" → subject
  │    │
  │    └─→ Select highest priority field for each canonical type
  │
  └─→ [GENERATE ACTION]
       ├─→ Build form.fill args with ONLY safe fields
       ├─→ Add metadata (honeypots avoided, warnings)
       └─→ Return action
```

---

## 📊 **Architecture**

### **1. Vision Analysis Module** (`vision_form_analysis.py`)

```python
async def analyze_form_fields_vision(
    llm,                    # LLM with vision capability
    screenshot_path,        # Path to screenshot
    dom_forms,             # Forms extracted from DOM
    instruction,           # User instruction
    run_logger             # Logger
) -> Dict:
    """
    Returns:
    {
        "visible_fields": [
            {
                "field_name": "email-1",
                "field_type": "email",
                "label": "Adres e-mail",
                "canonical": "email",
                "confidence": 0.95,
                "position": {"x": 100, "y": 200},
                "required": true
            }
        ],
        "honeypot_fields": [
            {
                "field_name": "email_address_",
                "reason": "Not visible in screenshot but present in DOM"
            }
        ],
        "recommended_fill_order": ["name-1", "email-1", "message-1"]
    }
    """
```

### **2. Field Enhancement** (`build_vision_enhanced_field_list`)

Combines DOM data with vision analysis:

```python
enhanced_field = {
    "form_id": "contact-form",
    "name": "email-1",
    "type": "email",
    "required": true,
    "visible_in_dom": true,
    "visible_in_screenshot": true,   # ← from vision
    "is_honeypot": false,             # ← from vision
    "priority": 150,                  # ← calculated
    "canonical": "email",             # ← from vision mapping
    "label": "Adres e-mail",          # ← from vision
    "confidence": 0.95                # ← from vision
}
```

### **3. Decision Tree** (`create_vision_decision_tree`)

```python
decision_tree = {
    "strategy": "vision_guided",
    "total_fields": 12,
    "safe_fields": 4,
    "honeypots_avoided": 8,
    "field_selection": {
        "name": {field_data},      # Best name field
        "email": {field_data},     # Best email field
        "phone": {field_data},     # Best phone field
        "message": {field_data}    # Best message field
    },
    "fill_order": ["name-1", "email-1", "phone-1", "message-1"],
    "warnings": ["Avoided 8 honeypot field(s)"]
}
```

---

## 🔍 **Honeypot Detection Patterns**

### **1. CSS-Hidden Fields**
```html
<!-- Visible in DOM, hidden by CSS -->
<input name="email_trap" style="display:none">
<input name="phone" style="visibility:hidden">
<input name="name" style="opacity:0">
```
**Detection:** Not visible in screenshot

### **2. Off-Screen Fields**
```html
<!-- Positioned outside viewport -->
<input name="honeypot" style="position:absolute; left:-9999px">
<input name="trap" style="position:fixed; top:-1000px">
```
**Detection:** Position outside visible area in screenshot

### **3. Zero-Size Fields**
```html
<!-- Zero dimensions -->
<input name="bot_trap" style="width:0; height:0">
<input name="hidden" style="font-size:0">
```
**Detection:** No visible input box in screenshot

### **4. Duplicate Fields**
```html
<!-- Two email fields, one is honeypot -->
<input name="email" type="email" style="display:none">
<input name="email-1" type="email">  <!-- Real field -->
```
**Detection:** Vision sees only one email field

### **5. Suspicious Names**
```
email_address_
phone_number_confirm
website_url_
user_name_trap
```
**Detection:** Unusual suffixes, "trap" in name

---

## 🚀 **Usage**

### **Automatic (Recommended)**

Vision analysis is automatically used when:
1. `--visual` flag is enabled
2. LLM supports vision (llava, minicpm-v, qwen2-vl, etc.)
3. Hierarchical planner is active
4. Screenshot is available

```bash
curllm --visual --stealth \
  --model llava:latest \
  "https://example.com/contact" \
  -d '{"instruction":"Fill contact form: name=John, email=john@example.com"}'
```

### **Manual Control**

```bash
# Enable vision analysis
export CURLLM_VISION_FORM_ANALYSIS=true

# Specify vision model (if different from main model)
export CURLLM_VISION_MODEL=llava:13b

curllm --visual "https://example.com/contact" \
  -d '{"instruction":"..."}'
```

### **Python API**

```python
from curllm_core.hierarchical_planner import hierarchical_plan_with_vision

action = await hierarchical_plan_with_vision(
    instruction="Fill contact form: ...",
    page_context=page_context,
    screenshot_path="screenshots/page.png",
    llm=llm_client,
    run_logger=logger
)

# Returns
{
    "type": "tool",
    "tool_name": "form.fill",
    "args": {"name": "John", "email": "john@example.com"},
    "hierarchical": true,
    "vision_enhanced": true,
    "vision_metadata": {
        "honeypots_avoided": 3,
        "safe_fields": 4,
        "warnings": ["Avoided 3 honeypot field(s)"]
    }
}
```

---

## 📝 **Configuration**

### **Environment Variables**

```bash
# Enable vision form analysis (default: auto if --visual)
CURLLM_VISION_FORM_ANALYSIS=true

# Vision model (default: same as CURLLM_MODEL)
CURLLM_VISION_MODEL=llava:13b

# Minimum confidence for field detection (0.0-1.0, default: 0.7)
CURLLM_VISION_CONFIDENCE_THRESHOLD=0.7

# Enable honeypot detection (default: true)
CURLLM_VISION_DETECT_HONEYPOTS=true
```

### **`.env` Example**

```bash
CURLLM_MODEL=qwen2.5:14b
CURLLM_VISION_MODEL=llava:13b
CURLLM_VISION_FORM_ANALYSIS=true
CURLLM_VISION_CONFIDENCE_THRESHOLD=0.75
CURLLM_VISION_DETECT_HONEYPOTS=true
```

---

## 🎯 **Benefits**

### **1. Honeypot Avoidance**
- ✅ Detects hidden fields that trap bots
- ✅ Avoids filling suspicious fields
- ✅ Reduces bot detection risk

### **2. Accuracy**
- ✅ Verifies field visibility visually
- ✅ Maps labels to correct fields
- ✅ Handles complex CSS layouts

### **3. Robustness**
- ✅ Works with dynamic forms
- ✅ Handles z-index stacking
- ✅ Detects overlay elements

### **4. Intelligence**
- ✅ Prioritizes required fields
- ✅ Follows visual fill order (top→bottom)
- ✅ Adapts to different layouts

---

## 🔬 **Example: Honeypot Detection**

### **Scenario**

Website has anti-bot honeypot:

```html
<form id="contact">
  <!-- Honeypot (hidden by CSS) -->
  <input name="email_address_" type="email" style="display:none">
  
  <!-- Real fields -->
  <input name="name-1" type="text" placeholder="Name">
  <input name="email-1" type="email" placeholder="Email">
  <input name="message-1" type="textarea" placeholder="Message">
</form>
```

### **Without Vision Analysis**

```python
# DOM sees 4 fields
fields = ["email_address_", "name-1", "email-1", "message-1"]

# Bot might fill ALL fields including honeypot
form.fill(email_address_="bot@example.com", ...)  # ❌ DETECTED AS BOT
```

### **With Vision Analysis**

```python
# Vision sees only 3 visible fields
visible_fields = ["name-1", "email-1", "message-1"]
honeypots = ["email_address_"]  # Not visible in screenshot

# Only fills visible fields
form.fill(name="John", email="john@example.com", message="...")  # ✅ SAFE
```

### **Log Output**

```
🔍 Vision-enhanced hierarchical planner starting...
🔍 Vision form analysis: analyzing screenshot for visible fields
   ✓ Vision analysis: 3 visible fields, 1 honeypots detected
   ⚠️  Honeypot fields detected:
      - email_address_: Not visible in screenshot but present in DOM
   Enhanced field list: 3 safe fields, 1 honeypots avoided
   Decision tree strategy: vision_guided
   ⚠️  Avoided 1 honeypot field(s)
   ✓ Mapping name: name-1 (priority: 150)
   ✓ Mapping email: email-1 (priority: 170)
   ✓ Mapping message: message-1 (priority: 100)
✓ Vision-enhanced action generated: form.fill
   Args: {'name': 'John', 'email': 'john@example.com', 'message': '...'}
   Honeypots avoided: 1
```

---

## 🧪 **Testing**

### **Test Honeypot Detection**

```python
# Create test HTML with honeypot
html = """
<form>
  <input name="trap" style="display:none">
  <input name="name" placeholder="Name">
</form>
"""

# Run vision analysis
vision_analysis = await analyze_form_fields_vision(...)

assert "trap" in [h["field_name"] for h in vision_analysis["honeypot_fields"]]
assert "name" in [v["field_name"] for v in vision_analysis["visible_fields"]]
```

### **Test Field Prioritization**

```python
enhanced_fields = build_vision_enhanced_field_list(dom_forms, vision_analysis)

# Check priorities
assert enhanced_fields[0]["priority"] > 0  # Safe field first
assert enhanced_fields[-1]["priority"] < 0  # Honeypot last
```

---

## 🐛 **Troubleshooting**

### **Vision analysis not working?**

Check:
1. ✅ `--visual` flag enabled
2. ✅ Model supports vision (llava, minicpm-v, qwen2-vl)
3. ✅ Screenshot exists
4. ✅ `CURLLM_VISION_FORM_ANALYSIS=true`

### **Too many false positives?**

Adjust confidence threshold:
```bash
CURLLM_VISION_CONFIDENCE_THRESHOLD=0.8  # More strict
```

### **Missing visible fields?**

Check screenshot quality:
- Resolution sufficient?
- Fields scrolled into view?
- Overlays closed?

---

## 📚 **Related Documentation**

- **[Hierarchical Planner](HIERARCHICAL_PLANNER.md)** - Token optimization
- **[Form Filling](FORM_FILLING.md)** - Form automation
- **[Examples](EXAMPLES.md)** - Usage examples
- **[Troubleshooting](Troubleshooting.md)** - Common issues

---

**[📚 Documentation Index](INDEX.md)** | **[⬆️ Back to Top](#vision-based-form-analysis--honeypot-detection)** | **[Main README](../README.md)**
