#!/bin/bash
# Script to update navigation in all documentation files

DOCS_DIR="$(cd "$(dirname "$0")" && pwd)"

# Files to update
FILES=(
    "Environment.md"
    "Playwright_BQL.md"
    "DIFFING.md"
    "Docker.md"
    "Devbox.md"
    "Troubleshooting.md"
    "REMOTE_PROXY_TUTORIAL.md"
    "TODO_DETAILED.md"
)

OLD_NAV='Docs: \[Home\]\(\.\./README\.md\) \| \[Installation\]\(Installation\.md\) \| \[Environment\]\(Environment\.md\) \| \[API\]\(API\.md\) \| \[Playwright\+BQL\]\(Playwright_BQL\.md\) \| \[Examples\]\(EXAMPLES\.md\) \| \[Docker\]\(Docker\.md\) \| \[Devbox\]\(Devbox\.md\) \| \[Troubleshooting\]\(Troubleshooting\.md\) \| \[Instrukcja\]\(\.\./INSTRUKCJA\.md\)'

NEW_NAV='**[📚 Documentation Index](INDEX.md)** | **[⬅️ Back to Main README](../README.md)**\n\n---'

for file in "${FILES[@]}"; do
    filepath="$DOCS_DIR/$file"
    if [ -f "$filepath" ]; then
        echo "Updating $file..."
        # Use perl for multi-line regex replacement
        perl -i -0pe "s/$OLD_NAV/$NEW_NAV/g" "$filepath"
        echo "✓ Updated $file"
    else
        echo "⚠ File not found: $file"
    fi
done

echo ""
echo "✅ Navigation update complete!"
