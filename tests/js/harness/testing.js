/**
 * A minimal test registry that runs inside the browser page.
 *
 * Tests declare themselves with `test(name, fn)`; the generated entry point
 * runs them in order and publishes the results for the Playwright runner.
 * Every assertion failure carries the test name, so the terminal output is
 * readable without a reporter.
 */
import React from "react";

const registry = [];

export function test(name, fn) {
  registry.push({ name, fn });
}

export function h(type, props, ...children) {
  return React.createElement(type, props, ...children);
}

export function assert(condition, message = "assertion failed") {
  if (!condition) throw new Error(message);
}

function stringify(value) {
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

export function assertEqual(actual, expected, message = "values differ") {
  if (stringify(actual) !== stringify(expected)) {
    throw new Error(`${message}\n  expected: ${stringify(expected)}\n  actual:   ${stringify(actual)}`);
  }
}

export function assertIncludes(haystack, needle, message = "value not found") {
  const found = Array.isArray(haystack)
    ? haystack.some((item) => stringify(item) === stringify(needle))
    : String(haystack).includes(String(needle));
  if (!found) {
    throw new Error(`${message}\n  looking for: ${stringify(needle)}\n  in:          ${stringify(haystack)}`);
  }
}

export async function assertThrows(fn, message = "expected a throw") {
  try {
    await fn();
  } catch (error) {
    return error;
  }
  throw new Error(message);
}

/** Collect `console.warn` output produced while `fn` runs. */
export async function withWarnings(fn) {
  const original = console.warn;
  const warnings = [];
  console.warn = (...args) => {
    warnings.push(args.map(String).join(" "));
  };
  try {
    await fn();
  } finally {
    console.warn = original;
  }
  return warnings;
}

export async function runAll() {
  const results = [];
  for (const { name, fn } of registry) {
    const started = performance.now();
    try {
      await fn();
      results.push({ name, ok: true, ms: performance.now() - started });
    } catch (error) {
      results.push({
        name,
        ok: false,
        ms: performance.now() - started,
        error: error?.stack || String(error),
      });
    }
  }
  return results;
}
