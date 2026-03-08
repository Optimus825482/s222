import type { KnownProvider } from "@mariozechner/pi-ai";
import { getModels, getEnvApiKey } from "@mariozechner/pi-ai";

/** Providers we actively track with env var mapping */
const TRACKED_PROVIDERS: { provider: KnownProvider; envVar: string }[] = [
  { provider: "openai", envVar: "OPENAI_API_KEY" },
  { provider: "anthropic", envVar: "ANTHROPIC_API_KEY" },
  { provider: "google", envVar: "GEMINI_API_KEY" },
  { provider: "groq", envVar: "GROQ_API_KEY" },
  { provider: "mistral", envVar: "MISTRAL_API_KEY" },
  { provider: "xai", envVar: "XAI_API_KEY" },
  { provider: "openrouter", envVar: "OPENROUTER_API_KEY" },
];

export interface ProviderStatus {
  provider: string;
  configured: boolean;
  envVar: string;
  modelCount: number;
}

/** Check which providers have API keys set */
export function getConfiguredProviders(): ProviderStatus[] {
  return TRACKED_PROVIDERS.map(({ provider, envVar }) => {
    const hasKey = !!getEnvApiKey(provider);
    let modelCount = 0;
    if (hasKey) {
      try {
        modelCount = getModels(provider).length;
      } catch {
        /* skip */
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

  for (const { provider } of TRACKED_PROVIDERS) {
    if (!getEnvApiKey(provider)) continue;
    try {
      const models = getModels(provider);
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
      // Provider not available, skip
    }
  }
  return results;
}
