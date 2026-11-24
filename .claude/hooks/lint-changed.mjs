#!/usr/bin/env node
/**
 * PostToolUse hook: Edit|Write amalga oshirilganda o'zgargan Python faylni tekshiradi.
 * stdin'dan JSON o'qib tool_input.file_path ni oladi, keyin:
 *   1. py_compile — sintaks xatosi bormi?
 *   2. bare `except:` yoki `except Exception:` ishlatilganmi?
 *   3. `print(` chaqiruvi bormi?
 */

import { execSync } from "child_process";
import { readFileSync } from "fs";

let raw = "";
process.stdin.setEncoding("utf8");
for await (const chunk of process.stdin) {
  raw += chunk;
}

let filePath;
try {
  const data = JSON.parse(raw);
  filePath = data?.tool_input?.file_path ?? data?.tool_response?.file_path;
} catch {
  process.exit(0);
}

if (!filePath || !filePath.endsWith(".py")) process.exit(0);

const issues = [];

// 1. Sintaks tekshiruvi
try {
  execSync(`python -m py_compile "${filePath}"`, { stdio: "pipe" });
} catch (err) {
  const msg = err.stderr?.toString().trim() || err.stdout?.toString().trim();
  issues.push(`SINTAKS XATO: ${msg}`);
}

// 2. bare except tekshiruvi
try {
  const src = readFileSync(filePath, "utf8");
  const lines = src.split("\n");
  lines.forEach((line, i) => {
    const trimmed = line.trim();
    if (trimmed === "except:" || trimmed === "except Exception:") {
      issues.push(`QOIDA: bot/rules/errors.md — bare 'except' qoilamaydi: ${filePath}:${i + 1}`);
    }
    if (/^\s*print\s*\(/.test(line) && !line.includes("#")) {
      issues.push(`QOIDA: bot/rules/errors.md — print() o'rniga logging ishlatilsin: ${filePath}:${i + 1}`);
    }
  });
} catch {
  // faylni o'qib bo'lmasa — o'tkazib yuboramiz
}

if (issues.length > 0) {
  console.error("=== lint-changed.mjs topilmalar ===");
  issues.forEach((msg) => console.error(" •", msg));
  console.error("===================================");
}

process.exit(0);
