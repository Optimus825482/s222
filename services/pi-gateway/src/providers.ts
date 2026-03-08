import { readFileSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";
import type { KnownProvider, Model, Api } from "@mariozechner/pi-ai";
import { getModels, getEnvApiKey } from "@mariozechner/pi-ai";

/** Provider entry — KnownProvider for native ones, string for custom/OpenAI-compatible */
interface TrackedProvider {
  provider: string;
  envVar: string;
}

/** Providers we actively track with env var mapping */
const TRACKED_PROVIDERS: TrackedProvider[] = [
  { provider: "google", envVar: "GEMINI_API_KEY" },
  { provider: "groq", envVar: "GROQ_API_KEY" },
  { provider: "mistral", envVar: "MISTRAL_API_KEY" },
  { provider: "deepseek", envVar: "DEEPSEEK_API_KEY" },
  { provider: "nvidia", envVar: "NVIDIA_API_KEY" },
  { provider: "openrouter", envVar: "OPENROUTER_API_KEY" },
];

/* ── Custom models.json loader ─────────────────────────────────── */

interface CustomProviderConfig {
  baseUrl: string;
  api: string;
  apiKey: string;
  models: Array<{
    id: string;
    name?: string;
    reasoning?: boolean;
    input?: string[];
    contextWindow?: number;
    maxTokens?: number;
    cost?: {
      input: number;
      output: number;
      cacheRead: number;
      cacheWrite: number;
    };
  }>;
}

let _customConfigCache: Record<string, CustomProviderConfig> | null = null;

function loadCustomProviderConfigs(): Record<string, CustomProviderConfig> {
  if (_customConfigCache) return _customConfigCache;
  try {
    const raw = readFileSync(
      join(homedir(), ".pi", "agent", "models.json"),
      "utf-8",
    );
    const parsed = JSON.parse(raw);
    _customConfigCache = parsed.providers ?? {};
    return _customConfigCache!;
  } catch {
    _customConfigCache = {};
    return {};
  }
}

/**
 * Build a pi-ai Model object from a custom provider config entry.
 * This allows stream()/complete() to work with custom providers.
 */
function buildCustomModel(
  providerName: string,
  cfg: CustomProviderConfig,
  modelDef: CustomProviderConfig["models"][number],
): Model<Api> {
  const defaultCost = { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 };
  return {
    id: modelDef.id,
    name: modelDef.name ?? modelDef.id,
    api: (cfg.api ?? "openai-completions") as Api,
    provider: providerName,
    baseUrl: cfg.baseUrl,
    reasoning: modelDef.reasoning ?? false,
    input: (modelDef.input ?? ["text"]) as ("text" | "image")[],
    cost: modelDef.cost ?? defaultCost,
    contextWindow: modelDef.contextWindow ?? 128000,
    maxTokens: modelDef.maxTokens ?? 16384,
  } as Model<Api>;
}

/* ── Public API ────────────────────────────────────────────────── */

export interface ProviderStatus {
  provider: string;
  configured: boolean;
  envVar: string;
  modelCount: number;
}

/** Check if a provider API key is set (native or env-based) */
function hasApiKey(provider: string, envVar: string): boolean {
  try {
    return !!getEnvApiKey(provider as KnownProvider);
  } catch {
    // Not a KnownProvider — check env directly
    return !!process.env[envVar];
  }
}

/** Check which providers have API keys set */
export function getConfiguredProviders(): ProviderStatus[] {
  const custom = loadCustomProviderConfigs();
  return TRACKED_PROVIDERS.map(({ provider, envVar }) => {
    const hasKey = hasApiKey(provider, envVar);
    let modelCount = 0;
    if (hasKey) {
      try {
        modelCount = getModels(provider as KnownProvider).length;
      } catch {
        // Not a native provider — count from models.json
        modelCount = custom[provider]?.models?.length ?? 0;
      }
    }
    return { provider, configured: hasKey, envVar, modelCount };
  });
}

/** Get all models from all configured providers, prefixed as "provider/model-id" */
export function getAllAvailableModels() {
  const results: Array<{
    id: string;
    provider: string;
    name: string;
    contextWindow: number;
    reasoning: boolean;
    supportsImages: boolean;
  }> = [];

  const custom = loadCustomProviderConfigs();

  for (const { provider, envVar } of TRACKED_PROVIDERS) {
    if (!hasApiKey(provider, envVar)) continue;

    let found = false;
    try {
      const models = getModels(provider as KnownProvider);
      for (const m of models) {
        results.push({
          id: `${provider}/${m.id}`,
          provider,
          name: m.name,
          contextWindow: m.contextWindow,
          reasoning: m.reasoning,
          supportsImages: m.input.includes("image"),
        });
      }
      found = models.length > 0;
    } catch {
      // Not a native KnownProvider
    }

    // Fallback: load from models.json for custom providers
    if (!found && custom[provider]?.models) {
      for (const m of custom[provider].models) {
        results.push({
          id: `${provider}/${m.id}`,
          provider,
          name: m.name ?? m.id,
          contextWindow: m.contextWindow ?? 128000,
          reasoning: m.reasoning ?? false,
          supportsImages: Array.isArray(m.input) && m.input.includes("image"),
        });
      }
    }
  }
  return results;
}

/**
 * Resolve a Model object for a given provider + modelId.
 * Works for both native KnownProviders (via getModel) and
 * custom providers defined in models.json.
 */
export function resolveModel(
  provider: string,
  modelId: string,
): Model<Api> | null {
  // Try native first
  try {
    const nativeModels = getModels(provider as KnownProvider);
    const found = nativeModels.find((m) => m.id === modelId);
    if (found) return found as Model<Api>;
  } catch {
    // Not a native provider or model
  }

  // Fallback: build from models.json
  const custom = loadCustomProviderConfigs();
  const cfg = custom[provider];
  if (!cfg?.models) return null;

  const modelDef = cfg.models.find((m) => m.id === modelId);
  if (!modelDef) return null;

  return buildCustomModel(provider, cfg, modelDef);
}

/**
 * Get the API key for a provider — checks native env-api-keys first,
 * then falls back to the env var name defined in models.json.
 */
export function getProviderApiKey(provider: string): string | undefined {
  // Try native first
  try {
    const key = getEnvApiKey(provider as KnownProvider);
    if (key) return key;
  } catch {
    // Not a KnownProvider
  }

  // Fallback: read env var name from models.json config
  const custom = loadCustomProviderConfigs();
  const cfg = custom[provider];
  if (cfg?.apiKey) {
    return process.env[cfg.apiKey];
  }

  // Last resort: check TRACKED_PROVIDERS envVar mapping
  const tracked = TRACKED_PROVIDERS.find((t) => t.provider === provider);
  if (tracked) {
    return process.env[tracked.envVar];
  }

  return undefined;
}
