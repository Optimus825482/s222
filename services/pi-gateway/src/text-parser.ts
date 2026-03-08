/**
 * Text-based Tool Call Parser (Faz 14.3)
 *
 * Extracts tool calls from text when models return them as
 * <tool_call>{"name": ..., "arguments": ...}</tool_call>
 * instead of native OpenAI tool_calls format.
 *
 * Moved from Python agents/base.py _parse_text_tool_calls to gateway
 * for centralized handling across all providers.
 */

export interface ParsedToolCall {
  id: string;
  type: "function";
  function: {
    name: string;
    arguments: string;
  };
}

const TOOL_CALL_RE = /<tool_call>\s*([\s\S]*?)\s*<\/tool_call>/gi;

/** Generate a unique tool call ID */
function generateCallId(): string {
  const hex = Math.random().toString(16).slice(2, 10);
  return `text_call_${hex}`;
}

/**
 * Parse tool calls from text content.
 * Returns null if no tool calls found.
 */
export function parseTextToolCalls(
  content: string | null | undefined,
): ParsedToolCall[] | null {
  if (!content) return null;

  const matches: string[] = [];
  let match: RegExpExecArray | null;

  // Reset regex state
  TOOL_CALL_RE.lastIndex = 0;
  while ((match = TOOL_CALL_RE.exec(content)) !== null) {
    matches.push(match[1]);
  }

  if (matches.length === 0) return null;

  const parsed: ParsedToolCall[] = [];

  for (const raw of matches) {
    try {
      const data = JSON.parse(raw);
      const fnName: string | undefined = data.name ?? data.function?.name;
      let fnArgs: unknown =
        data.arguments ?? data.parameters ?? data.function?.arguments ?? {};

      if (!fnName) continue;

      const argsStr =
        typeof fnArgs === "string" ? fnArgs : JSON.stringify(fnArgs);

      parsed.push({
        id: generateCallId(),
        type: "function",
        function: { name: fnName, arguments: argsStr },
      });
    } catch {
      // Invalid JSON — skip
      continue;
    }
  }

  return parsed.length > 0 ? parsed : null;
}

/**
 * Strip tool_call tags from content after parsing.
 */
export function stripToolCallTags(content: string): string {
  return content.replace(TOOL_CALL_RE, "").trim();
}
