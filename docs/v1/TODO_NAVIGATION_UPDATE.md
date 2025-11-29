# TODO: Navigation Update for Remaining Files

**Priority:** Medium  
**Effort:** 15 minutes  
**Status:** 🟡 In Progress (5/12 complete)

---

## Completed ✅

- [x] INDEX.md (new)
- [x] README.md (new)
- [x] HIERARCHICAL_PLANNER.md (new)
- [x] FORM_FILLING.md (new)
- [x] Installation.md
- [x] EXAMPLES.md
- [x] API.md
- [x] Environment.md

---

## Remaining Files to Update

### Pattern to Replace

**Old navigation (to be removed):**
```markdown
Docs: [Home](../README.md) | [Installation](Installation.md) | [Environment](Environment.md) | [API](API.md) | [Playwright+BQL](Playwright_BQL.md) | [Examples](EXAMPLES.md) | [Docker](Docker.md) | [Devbox](Devbox.md) | [Troubleshooting](Troubleshooting.md) | [Instrukcja](../INSTRUKCJA.md)
```

**New navigation (to be added):**
```markdown
**[📚 Documentation Index](INDEX.md)** | **[⬅️ Back to Main README](../README.md)**

---
```

**Footer to add (at end of file):**
```markdown
---

**[📚 Documentation Index](INDEX.md)** | **[⬆️ Back to Top](#title)** | **[Main README](../README.md)**
```

---

## Files List

### 1. Playwright_BQL.md
- [ ] Update header navigation
- [ ] Add footer navigation
- [ ] Verify all internal links

### 2. DIFFING.md
- [ ] Update header navigation
- [ ] Add footer navigation
- [ ] Add link to EXAMPLES.md

### 3. Docker.md
- [ ] Update header navigation
- [ ] Add footer navigation
- [ ] Link to Installation.md and Devbox.md

### 4. Devbox.md
- [ ] Update header navigation
- [ ] Add footer navigation
- [ ] Link to Installation.md and Docker.md

### 5. Troubleshooting.md
- [ ] Update header navigation
- [ ] Add footer navigation
- [ ] Cross-link to HIERARCHICAL_PLANNER.md and FORM_FILLING.md

### 6. REMOTE_PROXY_TUTORIAL.md
- [ ] Update header navigation
- [ ] Add footer navigation
- [ ] Link to Docker.md

### 7. TODO_DETAILED.md
- [ ] Update header navigation
- [ ] Add footer navigation
- [ ] Link to HIERARCHICAL_PLANNER.md and FORM_FILLING.md

---

## Batch Update Script

```bash
#!/bin/bash
# Run from docs/ directory

FILES=(
    "Playwright_BQL.md"
    "DIFFING.md"
    "Docker.md"
    "Devbox.md"
    "Troubleshooting.md"
    "REMOTE_PROXY_TUTORIAL.md"
    "TODO_DETAILED.md"
)

for file in "${FILES[@]}"; do
    echo "Updating $file..."
    
    # Backup
    cp "$file" "${file}.bak"
    
    # Replace old navigation with new
    sed -i '1,/^$/!b; /^Docs:/d' "$file"
    
    # Add new header navigation after title
    sed -i '2a\\n**[📚 Documentation Index](INDEX.md)** | **[⬅️ Back to Main README](../README.md)**\\n\\n---' "$file"
    
    echo "✓ Updated $file"
done
```

---

## Manual Steps (Recommended)

For each file:

1. Open file
2. Find line starting with `Docs: [Home]...`
3. Replace entire line with new navigation
4. Go to end of file
5. Add footer navigation
6. Save and verify links

**Verification:**
```bash
# Check all files for old navigation pattern
grep -r "Docs: \[Home\]" docs/

# Check all files have new navigation
grep -r "Documentation Index" docs/
```

---

## Testing Checklist

After updating all files:

- [ ] All files have header navigation
- [ ] All files have footer navigation  
- [ ] INDEX.md links work
- [ ] Cross-links between related docs work
- [ ] No broken relative paths
- [ ] All images still load
- [ ] Markdown renders correctly on GitHub

---

**[📚 Documentation Index](INDEX.md)** | **[Main README](../README.md)**
