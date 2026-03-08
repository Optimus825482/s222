import type {
  Context,
  Tool,
  Message,
  AssistantMessage,
} from "@mariozechner/pi-ai";
import { Type } from "@mariozechner/pi-ai";

// ─── OpenAI Request Types ───

export interface OAIMessage {
  role: "system" | "user" | "assistant" | "tool";
  content: string | null;
  tool_calls?: OAIToolCall[];
  tool_call_id?: string;
  name?: string;
}

export interface OAIToolCall {
  id: string;
  type: "function";
  function: { name: string; arguments: string };
}

export interface OAIToolDef {
  type: "function";
  function: {
    name: string;
    description?: string;
    parameters?: Record<string, unknown>;
  };
}

export interface OAIChatRequest {
  model: string;
  messages: OAIMessage[];
  temperature?: number;
  max_tokens?: number;
  stream?: boolean;
  tools?: OAIToolDef[];
  tool_choice?: string | object;
  /** Optional fallback models to try if primary fails (e.g. ["anthropic/claude-sonnet-4-20250514", "openai/gpt-4o"]) */
  fallback_models?: string[];
}

// ─── Convert OpenAI request → pi-ai Context ───

export function oaiRequestToContext(req: OAIChatRequest): Context {
  const messages: Message[] = [];
  let systemPrompt: string | undefined;
  const tools: Tool[] = [];

  for (const msg of req.messages) {
    if (msg.role === "system") {
      systemPrompt =
        (systemPrompt ? systemPrompt + "\n" : "") + (msg.content ?? "");
      continue;
    }

    if (msg.role === "user") {
      messages.push({
        role: "user",
        content: msg.content ?? "",
        timestamp: Date.now(),
      });
    } else if (msg.role === "assistant") {
      const content: AssistantMessage["content"] = [];

      if (msg.content) {
        content.push({ type: "text", text: msg.content });
      }
      if (msg.tool_calls) {
        for (const tc of msg.tool_calls) {
          let args: Record<string, unknown> = {};
          try {
            args = JSON.parse(tc.function.arguments);
          } catch {
            /* empty */
          }
          content.push({
            type: "toolCall",
            id: tc.id,
            name: tc.function.name,
            arguments: args,
          });
        }
      }

      messages.push({
        role: "assistant",
        content,
        api: "openai-completions",
        provider: "openai",
        model: req.model,
        stopReason: msg.tool_calls ? "toolUse" : "stop",
        usage: {
          input: 0,
          output: 0,
          cacheRead: 0,
          cacheWrite: 0,
          totalTokens: 0,
          cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 },
        },
        timestamp: Date.now(),
      });
    } else if (msg.role === "tool") {
      messages.push({
        role: "toolResult",
        toolCallId: msg.tool_call_id ?? "",
        toolName: msg.name ?? "",
        content: [{ type: "text", text: msg.content ?? "" }],
        isError: false,
        timestamp: Date.now(),
      });
    }
  }

  // Convert tools
  if (req.tools) {
    for (const t of req.tools) {
      tools.push({
        name: t.function.name,
        description: t.function.description ?? "",
        parameters: (t.function.parameters as any) ?? Type.Object({}),
      });
    }
  }

  return {
    systemPrompt,
    messages,
    ...(tools.length > 0 ? { tools } : {}),
  };
}

// ─── Convert pi-ai AssistantMessage → OpenAI response ───

export function piMessageToOAIResponse(
  msg: AssistantMessage,
  model: string,
  requestId: string,
) {
  const toolCalls: OAIToolCall[] = [];
  let textContent = "";
  let thinkingContent = "";

  for (const block of msg.content) {
    if (block.type === "text") {
      textContent += block.text;
    } else if (block.type === "toolCall") {
      toolCalls.push({
        id: block.id,
        type: "function",
        function: {
          name: block.name,
          arguments: JSON.stringify(block.arguments),
        },
      });
    } else if (block.type === "thinking") {
      thinkingContent += block.thinking;
    }
  }

  const finishReason =
    msg.stopReason === "toolUse"
      ? "tool_calls"
      : msg.stopReason === "length"
        ? "length"
        : "stop";

  const message: Record<string, unknown> = {
    role: "assistant",
    content: textContent || null,
  };
  if (toolCalls.length > 0) {
    message.tool_calls = toolCalls;
  }

  const response: Record<string, unknown> = {
    id: requestId,
    object: "chat.completion",
    created: Math.floor(Date.now() / 1000),
    model,
    choices: [
      {
        index: 0,
        message,
        finish_reason: finishReason,
      },
    ],
    usage: {
      prompt_tokens: msg.usage.input,
      completion_tokens: msg.usage.output,
      total_tokens: msg.usage.totalTokens,
    },
  };

  if (thinkingContent) {
    response.thinking = thinkingContent;
  }

  return response;
}

// ─── Convert pi-ai streaming events → OpenAI SSE chunks ───

export function piEventToSSEChunk(
  event: { type: string; [key: string]: any },
  model: string,
  requestId: string,
): string | null {
  const base = {
    id: requestId,
    object: "chat.completion.chunk",
    created: Math.floor(Date.now() / 1000),
    model,
  };

  switch (event.type) {
    case "text_delta": {
      return JSON.stringify({
        ...base,
        choices: [
          {
            index: 0,
            delta: { content: event.delta },
            finish_reason: null,
          },
        ],
      });
    }

    case "thinking_delta": {
      return JSON.stringify({
        ...base,
        choices: [
          {
            index: 0,
            delta: { thinking: event.delta },
            finish_reason: null,
          },
        ],
      });
    }

    case "toolcall_start": {
      const tc = event.partial?.content?.[event.contentIndex];
      if (tc?.type !== "toolCall") return null;
      return JSON.stringify({
        ...base,
        choices: [
          {
            index: 0,
            delta: {
              tool_calls: [
                {
                  index: event.contentIndex,
                  id: tc.id ?? "",
                  type: "function",
                  function: { name: tc.name ?? "", arguments: "" },
                },
              ],
            },
            finish_reason: null,
          },
        ],
      });
    }

    case "toolcall_delta": {
      return JSON.stringify({
        ...base,
        choices: [
          {
            index: 0,
            delta: {
              tool_calls: [
                {
                  index: event.contentIndex,
                  function: { arguments: event.delta },
                },
              ],
            },
            finish_reason: null,
          },
        ],
      });
    }

    case "done": {
      const finishReason =
        event.reason === "toolUse"
          ? "tool_calls"
          : event.reason === "length"
            ? "length"
            : "stop";
      const msg = event.message as AssistantMessage | undefined;
      return JSON.stringify({
        ...base,
        choices: [
          {
            index: 0,
            delta: {},
            finish_reason: finishReason,
          },
        ],
        ...(msg
          ? {
              usage: {
                prompt_tokens: msg.usage.input,
                completion_tokens: msg.usage.output,
                total_tokens: msg.usage.totalTokens,
              },
            }
          : {}),
      });
    }

    default:
      return null;
  }
}
