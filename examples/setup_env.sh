#!/usr/bin/env bash
set -euo pipefail

# Generate or merge examples/.env from examples/.env.examples
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$SCRIPT_DIR/.env.examples"
DST="$SCRIPT_DIR/.env"

if [ ! -f "$SRC" ]; then
  echo "Missing template: $SRC" >&2
  exit 1
fi

if [ ! -f "$DST" ]; then
  cp "$SRC" "$DST"
  echo "Created $DST from template."
  exit 0
fi

# Merge: append keys from template that are missing in current .env
TMP_FILE="$(mktemp)"
cp "$DST" "$TMP_FILE"
while IFS= read -r line; do
  [ -z "$line" ] && continue
  [[ "$line" =~ ^# ]] && continue
  key="${line%%=*}"
  if ! grep -qE "^${key}=" "$TMP_FILE"; then
    echo "$line" >> "$TMP_FILE"
  fi
done < "$SRC"

mv "$TMP_FILE" "$DST"
echo "Merged missing keys into $DST."
