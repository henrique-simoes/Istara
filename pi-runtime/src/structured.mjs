// Forced structured-output support for the Pi runtime worker (protocol v2).
//
// pi-ai has no `response_format`, so `turn.prompt.output_schema` is implemented
// as a forced `emit_structured_output` tool call: the JSON Schema is
// mechanically translated to a TypeBox parameters schema, the provider is
// forced to call exactly that tool (per-family `toolChoice`), and the tool's
// `execute` CAPTURES the arguments instead of executing anything host-side
// (see session.mjs). Only a mechanical subset of JSON Schema is supported —
// anything else (refs, combinators, schema-valued additionalProperties, ...)
// is rejected up front with a typed error so a schema the worker cannot force
// never reaches the model as a vague prompt hint. The TypeBox translation is a
// model-side aid only; Python revalidates the captured object against the
// ORIGINAL schema before accepting it (backend/app/core/pi_runtime/engine.py).

import { Type } from "@earendil-works/pi-ai";

export const STRUCTURED_TOOL_NAME = "emit_structured_output";

// Keep in sync with _SCHEMA_NODE_KEYS / _SCHEMA_TYPES in
// backend/app/core/pi_runtime/engine.py — both sides reject the same
// constructs so an unsupported schema fails closed no matter which side sees
// it first.
const SUPPORTED_NODE_KEYS = new Set([
  "type",
  "properties",
  "required",
  "additionalProperties",
  "items",
  "enum",
  "const",
  "description",
  "title",
  "minimum",
  "maximum",
  "exclusiveMinimum",
  "exclusiveMaximum",
  "multipleOf",
  "minLength",
  "maxLength",
  "pattern",
  "minItems",
  "maxItems",
  "uniqueItems",
  "minProperties",
  "maxProperties",
]);
const SUPPORTED_TYPES = new Set(["object", "string", "number", "integer", "boolean", "array", "null"]);

const NUMBER_OPTIONS = ["minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf"];
const STRING_OPTIONS = ["minLength", "maxLength", "pattern"];
const ARRAY_OPTIONS = ["minItems", "maxItems", "uniqueItems"];
const OBJECT_OPTIONS = ["minProperties", "maxProperties"];

function unsupported(detail) {
  return new Error(`structured_output_schema_unsupported:${detail}`);
}

function isPlainObject(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function pickOptions(node, keys) {
  const options = {};
  for (const key of keys) {
    if (node[key] !== undefined) options[key] = node[key];
  }
  if (typeof node.description === "string") options.description = node.description;
  if (typeof node.title === "string") options.title = node.title;
  return options;
}

function translateSingleType(node, type, path) {
  switch (type) {
    case "object": {
      const properties = node.properties ?? {};
      if (!isPlainObject(properties)) throw unsupported(`${path}:properties`);
      const required = node.required ?? [];
      if (!Array.isArray(required) || required.some((name) => typeof name !== "string")) {
        throw unsupported(`${path}:required`);
      }
      const additional = node.additionalProperties;
      if (additional !== undefined && typeof additional !== "boolean") {
        // A schema-valued additionalProperties is not mechanical; reject it
        // rather than silently weakening the model-side contract.
        throw unsupported(`${path}:additionalProperties`);
      }
      const requiredSet = new Set(required);
      const props = {};
      for (const [name, sub] of Object.entries(properties)) {
        const translated = translateNode(sub, `${path}.properties.${name}`);
        props[name] = requiredSet.has(name) ? translated : Type.Optional(translated);
      }
      const options = pickOptions(node, OBJECT_OPTIONS);
      if (additional === false) options.additionalProperties = false;
      return Type.Object(props, options);
    }
    case "array": {
      const items = node.items;
      if (!isPlainObject(items)) throw unsupported(`${path}:items`);
      return Type.Array(translateNode(items, `${path}.items`), pickOptions(node, ARRAY_OPTIONS));
    }
    case "string":
      return Type.String(pickOptions(node, STRING_OPTIONS));
    case "number":
      return Type.Number(pickOptions(node, NUMBER_OPTIONS));
    case "integer":
      return Type.Integer(pickOptions(node, NUMBER_OPTIONS));
    case "boolean":
      return Type.Boolean(pickOptions(node, []));
    case "null":
      return Type.Null(pickOptions(node, []));
    default:
      throw unsupported(`${path}:type:${type}`);
  }
}

function translateNode(node, path) {
  if (!isPlainObject(node)) throw unsupported(`${path}:not_a_schema_object`);
  for (const key of Object.keys(node)) {
    if (!SUPPORTED_NODE_KEYS.has(key)) throw unsupported(`${path}:${key}`);
  }
  if (node.const !== undefined) return Type.Literal(node.const);
  if (node.enum !== undefined) {
    if (!Array.isArray(node.enum) || node.enum.length === 0) throw unsupported(`${path}:enum`);
    const literals = node.enum.map((value) => Type.Literal(value));
    return literals.length === 1 ? literals[0] : Type.Union(literals);
  }
  const raw = node.type;
  const types = typeof raw === "string" ? [raw] : Array.isArray(raw) ? raw : [];
  if (types.length === 0) throw unsupported(`${path}:missing_type`);
  for (const type of types) {
    if (typeof type !== "string" || !SUPPORTED_TYPES.has(type)) throw unsupported(`${path}:type:${type}`);
  }
  const translated = types.map((type) => translateSingleType(node, type, path));
  return translated.length === 1 ? translated[0] : Type.Union(translated);
}

/**
 * Mechanically translate a supported JSON Schema into a TypeBox parameters
 * schema for `emit_structured_output`. The root must be an object (the
 * structured contract carries one object). Throws an Error whose message is
 * the typed `structured_output_schema_unsupported:<detail>` failure.
 */
export function translateOutputSchema(schema) {
  const translated = translateNode(schema, "$");
  // The structured contract carries one object; mirror the Python precheck
  // (enum/const roots defer to literal validation).
  if (schema.enum === undefined && schema.const === undefined) {
    const raw = schema.type;
    const types = typeof raw === "string" ? [raw] : Array.isArray(raw) ? raw : [];
    if (!types.includes("object")) throw unsupported("$:root_not_object");
  }
  return translated;
}

/**
 * The agent-core `parameters` for the forced capture tool: the translated
 * schema as the FIRST union arm (the model sees the full schema and is
 * guided toward it), with a catch-all second arm. The catch-all is
 * deliberate: pi-agent-core validates arguments against `parameters` BEFORE
 * `execute`, and a strict schema would make the worker silently pre-reject
 * invalid objects — the capture must be faithful so PYTHON's revalidation
 * against the original schema (the contract) sees exactly what the model
 * emitted and can apply its one-bounded-repair / typed-failure rule. The
 * TypeBox translation is a model-side aid, never the authority.
 */
export function captureParameters(translated) {
  return Type.Union([translated, Type.Any()]);
}

/**
 * Validate a `tool_choice` protocol value: "auto" | "required" | {"name": ...}.
 * Returns a normalized {kind, name?} or throws `invalid_tool_choice:<detail>`.
 */
export function normalizeToolChoice(toolChoice) {
  if (toolChoice === "auto" || toolChoice === "required") return { kind: toolChoice };
  if (isPlainObject(toolChoice) && typeof toolChoice.name === "string" && toolChoice.name) {
    return { kind: "tool", name: toolChoice.name };
  }
  throw new Error("invalid_tool_choice");
}

/**
 * Map a normalized tool choice onto the provider family's native forcing
 * shape. Returns null when the family cannot express it — the caller fails
 * the run closed for real bindings (faux test bindings are scripted and need
 * no forcing).
 */
export function mapToolChoiceForApi(api, choice) {
  if (api === "openai-completions") {
    if (choice.kind === "auto") return "auto";
    if (choice.kind === "required") return "required";
    return { type: "function", function: { name: choice.name } };
  }
  if (api === "anthropic-messages") {
    if (choice.kind === "auto") return { type: "auto" };
    if (choice.kind === "required") return { type: "any" };
    return { type: "tool", name: choice.name };
  }
  return null;
}
