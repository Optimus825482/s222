/**
 * Pollinations.ai image URL generator.
 * Keeps prompt ≤200 chars and URL length safe (~1800) to avoid 400 errors.
 */

const POLLINATIONS_IMAGE_URL = "https://image.pollinations.ai/prompt";

const ALLOWED_MODELS = ["flux", "zimage", "turbo", "imagen-4", "grok-imagine"] as const;
const DEFAULT_MODEL = "flux";

export interface PollinationsOptions {
  width?: number;
  height?: number;
  model?: string;
  seed?: number;
  nologo?: boolean;
  enhance?: boolean;
}

function normalizeModel(model: string): string {
  const m = (model || "").toLowerCase().trim();
  if (ALLOWED_MODELS.includes(m as (typeof ALLOWED_MODELS)[number])) return m;
  return DEFAULT_MODEL;
}

function buildPollinationsParams(options: PollinationsOptions): URLSearchParams {
  const { width = 1200, height = 630, model, seed, nologo, enhance } = options;
  const params = new URLSearchParams();
  params.set("model", normalizeModel(model ?? DEFAULT_MODEL));
  params.set("width", String(Math.max(512, Math.min(2048, width))));
  params.set("height", String(Math.max(512, Math.min(2048, height))));
  if (seed != null) params.set("seed", String(seed));
  if (nologo === true) params.set("nologo", "true");
  if (enhance === true) params.set("enhance", "true");
  return params;
}

/**
 * Build a Pollinations.ai image URL from a prompt.
 * Truncates prompt to 200 chars to stay under URL length limits (~2000).
 */
export function generateImageUrl(
  prompt: string,
  options: PollinationsOptions = {},
): string {
  if (!prompt || typeof prompt !== "string") {
    throw new Error("Prompt is required and must be a string");
  }

  let cleanPrompt = prompt.trim();
  if (cleanPrompt.length === 0) {
    throw new Error("Prompt cannot be empty");
  }

  if (cleanPrompt.length > 200) {
    if (typeof console !== "undefined" && console.warn) {
      console.warn(
        `⚠️ Prompt too long (${cleanPrompt.length} chars), truncating to 200`,
      );
    }
    cleanPrompt = cleanPrompt.substring(0, 197) + "...";
  }

  const {
    width = 1200,
    height = 630,
    model = DEFAULT_MODEL,
  } = options;

  const normalizedModel = normalizeModel(model);
  const encodedPrompt = encodeURIComponent(cleanPrompt);
  const params = buildPollinationsParams({
    ...options,
    width,
    height,
    model: normalizedModel,
  });

  const baseUrl = `${POLLINATIONS_IMAGE_URL}/${encodedPrompt}`;
  if (baseUrl.length > 1800) {
    if (typeof console !== "undefined" && console.error) {
      console.error(
        `❌ URL too long even after truncation: ${baseUrl.length} chars`,
      );
    }
    const fallbackPrompt = "artificial intelligence technology digital art";
    return generateImageUrl(fallbackPrompt, options);
  }

  return `${baseUrl}?${params.toString()}`;
}
