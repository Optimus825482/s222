import { Hono } from "hono";
import { cors } from "hono/cors";
import { serve } from "@hono/node-server";
import { stream as honoStream } from "hono/streaming";
import { getModel, stream, complete } from "@mariozechner/pi-ai";
import {
  oaiRequestToContext,
  piMessageToOAIResponse,
  piEventToSSEChunk,
  type OAIChatRequest,
} from "./converter.js";
import { getConfiguredProviders, getAllAvailableModels } from "./providers.js";
import {
  registerTools,
  validateToolCall,
  getSchemas,
  getSchema,
  getStats,
  resetStats,
  hasSchemas,
} from "./validator.js";
import { parseTextToolCalls, stripToolCallTags } from "./text-parser.js";

const app = new Hono();
app.use("/*", cors());

// ─── Health ───

app.get("/health", (c) =>
  c.json({
    status: "ok",
    service: "pi-gateway",
    timestamp: new Date().toISOString(),
  }),
);

// ─── List configured providers ───

app.get("/api/providers", (c) => {
  const providers = getConfiguredProviders();
  return c.json({
    providers,
    configured: providers.filter((p) => p.configured).length,
    total: providers.length,
  });
});

// ─── List models (OpenAI-compatible) ───

app.get("/v1/models", (c) => {
  const models = getAllAvailableModels();
  return c.json({
    object: "list",
    data: models.map((m) => ({
      id: m.id,
      object: "model",
      created: Math.floor(Date.now() / 1000),
      owned_by: m.provider,
      context_window: m.contextWindow,
      reasoning: m.reasoning,
      supports_images: m.supportsImages,
    })),
  });
});

// ─── Chat Completions ───

function parseModelId(modelStr: string): { provider: string; modelId: string } {
  const slashIdx = modelStr.indexOf("/");
  if (slashIdx === -1) {
    // No provider prefix — try common defaults
    return { provider: "openai", modelId: modelStr };
  }
  return {
    provider: modelStr.slice(0, slashIdx),
    modelId: modelStr.slice(slashIdx + 1),
  };
}

function generateId(): string {
  return `chatcmpl-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

// ─── Fallback helpers ───

/** Errors worth retrying on a different provider */
function isRetryableError(err: any): boolean {
  if (!err) return false;
  const status = err.status ?? err.statusCode ?? 0;
  // 429 rate-limit, 5xx server errors, network timeouts
  if (status === 429 || (status >= 500 && status < 600)) return true;
  const msg = String(err.message ?? "").toLowerCase();
  return (
    msg.includes("timeout") ||
    msg.includes("econnrefused") ||
    msg.includes("econnreset") ||
    msg.includes("fetch failed") ||
    msg.includes("rate limit")
  );
}

/** Try to resolve a model, returns null on failure */
function tryGetModel(provider: string, modelId: string) {
  try {
    return getModel(provider as any, modelId as any);
  } catch {
    return null;
  }
}

/** Build the ordered list of models to attempt: primary + fallbacks */
function buildModelChain(
  primaryModel: string,
  fallbacks?: string[],
): { provider: string; modelId: string; fullId: string }[] {
  const chain: { provider: string; modelId: string; fullId: string }[] = [];
  const { provider, modelId } = parseModelId(primaryModel);
  chain.push({ provider, modelId, fullId: primaryModel });
  if (fallbacks) {
    for (const fb of fallbacks) {
      const parsed = parseModelId(fb);
      chain.push({
        provider: parsed.provider,
        modelId: parsed.modelId,
        fullId: fb,
      });
    }
  }
  return chain;
}

app.post("/v1/chat/completions", async (c) => {
  const body = (await c.req.json()) as OAIChatRequest;
  const requestId = generateId();
  const modelChain = buildModelChain(body.model, body.fallback_models);

  const context = oaiRequestToContext(body);
  const options: any = {};
  if (body.temperature !== undefined) options.temperature = body.temperature;
  if (body.max_tokens !== undefined) options.maxTokens = body.max_tokens;

  // ─── Streaming ───
  if (body.stream) {
    return honoStream(c, async (honoWriter) => {
      c.header("Content-Type", "text/event-stream");
      c.header("Cache-Control", "no-cache");
      c.header("Connection", "keep-alive");

      let served = false;
      for (const candidate of modelChain) {
        const model = tryGetModel(candidate.provider, candidate.modelId);
        if (!model) continue;

        try {
          const s = stream(model, context, options);
          // If this is a fallback, notify via SSE comment
          if (candidate.fullId !== body.model) {
            await honoWriter.write(`: fallback_used=${candidate.fullId}\n\n`);
          }
          for await (const event of s) {
            const chunk = piEventToSSEChunk(event, candidate.fullId, requestId);
            if (chunk) {
              await honoWriter.write(`data: ${chunk}\n\n`);
            }
            if (event.type === "error") {
              const errMsg = event.error?.errorMessage ?? "Stream error";
              // If retryable and we have more candidates, break to try next
              if (
                isRetryableError({ message: errMsg }) &&
                candidate !== modelChain[modelChain.length - 1]
              ) {
                console.warn(
                  `[fallback] Stream error from ${candidate.fullId}: ${errMsg}, trying next`,
                );
                break;
              }
              await honoWriter.write(
                `data: ${JSON.stringify({ error: { message: errMsg } })}\n\n`,
              );
            }
          }
          served = true;
          break; // success — stop trying
        } catch (err: any) {
          console.warn(
            `[fallback] ${candidate.fullId} failed: ${err?.message}`,
          );
          if (
            isRetryableError(err) &&
            candidate !== modelChain[modelChain.length - 1]
          ) {
            continue; // try next fallback
          }
          // Last candidate or non-retryable — emit error
          const errMsg = err?.message ?? "Internal server error";
          await honoWriter.write(
            `data: ${JSON.stringify({ error: { message: errMsg } })}\n\n`,
          );
          served = true;
          break;
        }
      }

      if (!served) {
        await honoWriter.write(
          `data: ${JSON.stringify({ error: { message: "All providers failed" } })}\n\n`,
        );
      }
      await honoWriter.write("data: [DONE]\n\n");
    });
  }

  // ─── Non-streaming with fallback ───
  const errors: string[] = [];
  for (const candidate of modelChain) {
    const model = tryGetModel(candidate.provider, candidate.modelId);
    if (!model) {
      errors.push(`${candidate.fullId}: model not found`);
      continue;
    }

    try {
      const result = await complete(model, context, options);
      const response = piMessageToOAIResponse(
        result,
        candidate.fullId,
        requestId,
      );

      // Faz 14.3: Validate tool call arguments if schemas registered
      if (hasSchemas()) {
        const choices = (response as any).choices;
        if (choices?.[0]?.message?.tool_calls) {
          const validationErrors: any[] = [];
          for (const tc of choices[0].message.tool_calls) {
            if (tc.type === "function" && tc.function) {
              let args: Record<string, unknown> = {};
              try {
                args = JSON.parse(tc.function.arguments);
              } catch {
                /* skip */
              }
              const vr = validateToolCall(tc.function.name, args);
              if (!vr.valid) {
                validationErrors.push({
                  tool_call_id: tc.id,
                  tool_name: tc.function.name,
                  errors: vr.errors,
                });
              }
            }
          }
          if (validationErrors.length > 0) {
            (response as any).tool_validation_errors = validationErrors;
          }
        }
      }

      // Faz 14.3: Parse text-based tool calls if no native ones found
      const msg = (response as any).choices?.[0]?.message;
      if (msg && !msg.tool_calls && msg.content) {
        const textCalls = parseTextToolCalls(msg.content);
        if (textCalls) {
          msg.tool_calls = textCalls;
          msg.content = stripToolCallTags(msg.content);
          (response as any).choices[0].finish_reason = "tool_calls";
          (response as any).text_tool_calls_parsed = true;
        }
      }

      // Indicate if fallback was used
      if (candidate.fullId !== body.model) {
        (response as any).fallback_used = candidate.fullId;
        (response as any).original_model = body.model;
      }
      return c.json(response);
    } catch (err: any) {
      const errMsg = err?.message ?? "unknown error";
      errors.push(`${candidate.fullId}: ${errMsg}`);
      console.warn(`[fallback] ${candidate.fullId} failed: ${errMsg}`);
      if (
        isRetryableError(err) &&
        candidate !== modelChain[modelChain.length - 1]
      ) {
        continue; // try next
      }
      // Non-retryable or last candidate
      break;
    }
  }

  return c.json(
    {
      error: {
        message: `All providers failed: ${errors.join(" | ")}`,
        type: "api_error",
        code: "all_providers_failed",
      },
    },
    502,
  );
});

// ─── Tool Schema Registry (Faz 14.3) ───

app.post("/v1/tools/register", async (c) => {
  const body = await c.req.json();
  const tools: Array<{
    name: string;
    parameters: Record<string, unknown>;
    description?: string;
  }> = [];

  // Accept OpenAI tool format or flat format
  const items: any[] = Array.isArray(body) ? body : (body.tools ?? []);
  for (const item of items) {
    if (item.type === "function" && item.function) {
      tools.push({
        name: item.function.name,
        parameters: item.function.parameters ?? {},
        description: item.function.description,
      });
    } else if (item.name && item.parameters) {
      tools.push(item);
    }
  }

  const result = registerTools(tools);
  return c.json({
    status: "ok",
    registered: result.registered,
    errors: result.errors,
    total_schemas: getSchemas().length,
  });
});

app.get("/v1/tools/schemas", (c) => {
  const name = c.req.query("name");
  if (name) {
    const schema = getSchema(name);
    return schema
      ? c.json(schema)
      : c.json({ error: `Tool '${name}' not found` }, 404);
  }
  return c.json({
    schemas: getSchemas(),
    total: getSchemas().length,
  });
});

app.get("/v1/tools/validation-stats", (c) => c.json(getStats()));

app.post("/v1/tools/validation-stats/reset", (c) => {
  resetStats();
  return c.json({ status: "ok" });
});

app.post("/v1/tools/validate", async (c) => {
  const { tool_name, arguments: args } = await c.req.json();
  if (!tool_name) return c.json({ error: "tool_name required" }, 400);
  const result = validateToolCall(tool_name, args ?? {});
  return c.json(result);
});

// ─── Text Tool Call Parse endpoint (Faz 14.3) ───

app.post("/v1/tools/parse-text", async (c) => {
  const { content } = await c.req.json();
  const calls = parseTextToolCalls(content);
  return c.json({
    found: calls !== null,
    tool_calls: calls ?? [],
    cleaned_content: calls ? stripToolCallTags(content ?? "") : content,
  });
});

// ─── CORS Proxy (Faz 14.5) — browser'dan doğrudan provider çağrısı ───

app.post("/v1/cors-proxy", async (c) => {
  const { url, method, headers, body: proxyBody } = await c.req.json();
  if (!url || typeof url !== "string") {
    return c.json({ error: "url required" }, 400);
  }

  // Whitelist: only allow known LLM provider domains
  const allowed = [
    "api.openai.com",
    "api.anthropic.com",
    "generativelanguage.googleapis.com",
    "api.groq.com",
    "api.mistral.ai",
    "api.x.ai",
    "openrouter.ai",
  ];
  let hostname: string;
  try {
    hostname = new URL(url).hostname;
  } catch {
    return c.json({ error: "Invalid URL" }, 400);
  }
  if (!allowed.some((d) => hostname === d || hostname.endsWith(`.${d}`))) {
    return c.json(
      {
        error: `Domain not allowed: ${hostname}. Allowed: ${allowed.join(", ")}`,
      },
      403,
    );
  }

  try {
    const resp = await fetch(url, {
      method: method || "POST",
      headers: headers || {},
      body: proxyBody ? JSON.stringify(proxyBody) : undefined,
    });
    const data = await resp.json();
    return c.json(data, resp.status as any);
  } catch (err: any) {
    return c.json({ error: `Proxy failed: ${err?.message}` }, 502);
  }
});

// ─── Start ───

const PORT = parseInt(process.env.PORT ?? "3100", 10);

serve({ fetch: app.fetch, port: PORT }, (info) => {
  console.log(`🚀 pi-gateway listening on http://localhost:${info.port}`);
  const configured = getConfiguredProviders().filter((p) => p.configured);
  console.log(
    `   Providers: ${configured.map((p) => p.provider).join(", ") || "none"}`,
  );
});
