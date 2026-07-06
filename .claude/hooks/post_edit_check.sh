#!/bin/bash
# PostToolUse hook — har bir Edit/Write amalidan keyin ishga tushadi.
# Maqsad: taqiqlangan naqshlarni (bare except, print-debug, .bak fayllar) erta ushlash.

set -e

CHANGED_FILE="$1"

if [ -z "$CHANGED_FILE" ]; then
  exit 0
fi

# 1) Bare except tekshiruvi
if grep -nE "except\s*:\s*$" "$CHANGED_FILE" 2>/dev/null; then
  echo "⚠️  Ogohlantirish: $CHANGED_FILE faylida 'bare except' topildi. .claude/rules/database.md ga qarang."
fi

# 2) print() orqali debug qoldirilganini tekshirish (services/ va bot/ ichida)
if [[ "$CHANGED_FILE" == services/* || "$CHANGED_FILE" == bot/* ]]; then
  if grep -n "print(" "$CHANGED_FILE" 2>/dev/null; then
    echo "⚠️  Ogohlantirish: $CHANGED_FILE da print() bor. logging ishlatilsin."
  fi
fi

# 3) .bak yoki commented-out katta bloklarni oldini olish (informatsion)
if [[ "$CHANGED_FILE" == *.bak ]]; then
  echo "❌ .bak fayllar repo'ga qo'shilmasligi kerak (.gitignore ga qarang)."
fi

exit 0
