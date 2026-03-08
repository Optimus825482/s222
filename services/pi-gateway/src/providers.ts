import type { KnownProvider } from "@mariozechner/pi-ai";
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
  return TRACKED_PROVIDERS.map(({ provider, envVar }) => {
    const hasKey = hasApiKey(provider, envVar);
    let modelCount = 0;
    if (hasKey) {
      try {
        modelCount = getModels(provider as KnownProvider).length;
      } catch {
        /* not a native provider or no models */
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

  for (const { provider, envVar } of TRACKED_PROVIDERS) {
    if (!hasApiKey(provider, envVar)) continue;
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
    } catch {
      // Provider not natively supported or unavailable, skip
    }
  }
  return results;
}
