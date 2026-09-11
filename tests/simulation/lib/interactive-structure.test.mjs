import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const root = join(import.meta.dirname, "..", "..", "..");

test("Sidebar project option keeps project actions outside the option", () => {
  const source = readFileSync(join(root, "frontend/src/components/layout/Sidebar.tsx"), "utf8");
  assert.doesNotMatch(
    source,
    /role="option"[\s\S]{0,260}<button[\s\S]{0,120}aria-label="Project options"/,
  );
});

test("Sidebar projects do not use a listbox around action buttons", () => {
  const source = readFileSync(join(root, "frontend/src/components/layout/Sidebar.tsx"), "utf8");
  assert.doesNotMatch(source, /role="listbox"[\s\S]{0,320}role="option"/);
  assert.match(source, /aria-current=\{activeProjectId === project\.id \? "page" : undefined\}/);
});

test("Kanban task cards do not expose a button role around nested controls", () => {
  const source = readFileSync(join(root, "frontend/src/components/kanban/KanbanBoard.tsx"), "utf8");
  assert.doesNotMatch(source, /role="button"\s+tabIndex=\{0\}[\s\S]{0,220}aria-label="Change assigned agent"/);
  assert.match(source, /aria-label=\{`Open \$\{task\.title\}`\}/);
});
