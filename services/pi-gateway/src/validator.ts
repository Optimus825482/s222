/**
 * Tool Schema Registry & AJV Validator (Faz 14.3)
 *
 * Central registry for tool JSON Schemas.
 * Validates tool call arguments against registered schemas.
 * Returns structured validation errors for LLM self-correction.
 */

import Ajv, { type ErrorObject } from "ajv";
import addFormats from "ajv-formats";

// ─── Types ───

export interface ToolSchema {
  name: string;
  description?: string;
  parameters: Record<string, unknown>; // JSON Schema
  registeredAt: number;
}

export interface ValidationResult {
  valid: boolean;
  toolName: string;
  errors?: ValidationError[];
}

export interface ValidationError {
  path: string;
  message: string;
  keyword: string;
  params: Record<string, unknown>;
}

export interface ValidationStats {
  totalValidations: number;
  passed: number;
  failed: number;
  byTool: Record<string, { passed: number; failed: number }>;
}

// ─── Registry ───

const schemas = new Map<string, ToolSchema>();
const ajv = new Ajv({ allErrors: true, coerceTypes: true, strict: false });
addFormats(ajv);

const stats: ValidationStats = {
  totalValidations: 0,
  passed: 0,
  failed: 0,
  byTool: {},
};

/** Register a single tool schema */
export function registerTool(
  name: string,
  parameters: Record<string, unknown>,
  description?: string,
): void {
  schemas.set(name, {
    name,
    description,
    parameters,
    registeredAt: Date.now(),
  });
  // Pre-compile the schema for performance
  try {
    if (ajv.getSchema(name)) ajv.removeSchema(name);
    ajv.addSchema(parameters, name);
  } catch {
    // Schema compilation failed — will validate at call time
  }
}

/** Register multiple tools at once (bulk) */
export function registerTools(
  tools: Array<{
    name: string;
    parameters: Record<string, unknown>;
    description?: string;
  }>,
): { registered: number; errors: string[] } {
  const errors: string[] = [];
  let registered = 0;
  for (const t of tools) {
    try {
      registerTool(t.name, t.parameters, t.description);
      registered++;
    } catch (err: any) {
      errors.push(`${t.name}: ${err?.message ?? "unknown error"}`);
    }
  }
  return { registered, errors };
}

/** Validate tool call arguments against registered schema */
export function validateToolCall(
  toolName: string,
  args: Record<string, unknown>,
): ValidationResult {
  stats.totalValidations++;
  if (!stats.byTool[toolName]) {
    stats.byTool[toolName] = { passed: 0, failed: 0 };
  }

  const schema = schemas.get(toolName);
  if (!schema) {
    // No schema registered — pass through (permissive)
    stats.passed++;
    stats.byTool[toolName].passed++;
    return { valid: true, toolName };
  }

  let validate = ajv.getSchema(toolName);
  if (!validate) {
    try {
      ajv.addSchema(schema.parameters, toolName);
      validate = ajv.getSchema(toolName);
    } catch {
      // Can't compile — pass through
      stats.passed++;
      stats.byTool[toolName].passed++;
      return { valid: true, toolName };
    }
  }

  if (!validate) {
    stats.passed++;
    stats.byTool[toolName].passed++;
    return { valid: true, toolName };
  }

  const valid = validate(args) as boolean;

  if (valid) {
    stats.passed++;
    stats.byTool[toolName].passed++;
    return { valid: true, toolName };
  }

  stats.failed++;
  stats.byTool[toolName].failed++;

  const errors: ValidationError[] = (validate.errors ?? []).map(
    (e: ErrorObject) => ({
      path: e.instancePath || "/",
      message: e.message ?? "validation failed",
      keyword: e.keyword,
      params: e.params as Record<string, unknown>,
    }),
  );

  return { valid: false, toolName, errors };
}

/** Get all registered schemas */
export function getSchemas(): ToolSchema[] {
  return Array.from(schemas.values());
}

/** Get schema for a specific tool */
export function getSchema(toolName: string): ToolSchema | undefined {
  return schemas.get(toolName);
}

/** Get validation statistics */
export function getStats(): ValidationStats {
  return { ...stats };
}

/** Reset stats (for testing) */
export function resetStats(): void {
  stats.totalValidations = 0;
  stats.passed = 0;
  stats.failed = 0;
  stats.byTool = {};
}

/** Check if any schemas are registered */
export function hasSchemas(): boolean {
  return schemas.size > 0;
}
