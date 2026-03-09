/**
 * Pollinations.ai image URL generator with rate-limit-aware loading.
 * Keeps prompt ≤200 chars and URL length safe (~1800) to avoid 400 errors.
 * Provides staggered loading to avoid 429 (Too Many Requests).
 */

const POLLINATIONS_IMAGE_URL = "https://image.pollinations.ai/prompt";

const ALLOWED_MODELS = [
  "flux",
  "zimage",
  "turbo",
  "imagen-4",
  "grok-imagine",
] as const;
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

function buildPollinationsParams(
  options: PollinationsOptions,
): URLSearchParams {
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
    console.warn?.(
      `⚠️ Prompt too long (${cleanPrompt.length} chars), truncating to 200`,
    );
    cleanPrompt = cleanPrompt.substring(0, 197) + "...";
  }

  const { width = 1200, height = 630, model = DEFAULT_MODEL } = options;
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
    console.error?.(
      `❌ URL too long even after truncation: ${baseUrl.length} chars`,
    );
    return generateImageUrl(
      "artificial intelligence technology digital art",
      options,
    );
  }

  return `${baseUrl}?${params.toString()}`;
}

/* ─── Rate-limit-aware staggered image loading ─────────────────── */

const STAGGER_DELAY_MS = 1500; // delay between each image request
const MAX_RETRIES = 2;
const RETRY_BASE_DELAY_MS = 3000;

/**
 * Preload a single image with retry + exponential backoff.
 * Returns the URL on success, undefined on failure.
 */
function preloadImage(
  url: string,
  retries = MAX_RETRIES,
): Promise<string | undefined> {
  return new Promise((resolve) => {
    const img = new Image();
    let attempt = 0;

    const tryLoad = () => {
      img.onload = () => resolve(url);
      img.onerror = () => {
        attempt++;
        if (attempt <= retries) {
          const delay = RETRY_BASE_DELAY_MS * Math.pow(2, attempt - 1);
          console.warn(
            `⏳ Image retry ${attempt}/${retries} in ${delay}ms: ${url.slice(0, 80)}…`,
          );
          setTimeout(tryLoad, delay);
        } else {
          console.warn(
            `❌ Image failed after ${retries} retries: ${url.slice(0, 80)}…`,
          );
          resolve(undefined);
        }
      };
      img.src = url;
    };

    tryLoad();
  });
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export interface StaggeredResult {
  index: number;
  url: string | undefined;
}

/**
 * Load multiple Pollinations images with staggered timing to avoid 429.
 * Calls `onProgress` after each image resolves so UI can update incrementally.
 */
export async function loadImagesStaggered(
  prompts: (string | undefined)[],
  options: PollinationsOptions = {},
  onProgress?: (result: StaggeredResult) => void,
): Promise<(string | undefined)[]> {
  const results: (string | undefined)[] = new Array(prompts.length).fill(
    undefined,
  );

  for (let i = 0; i < prompts.length; i++) {
    const prompt = prompts[i];
    if (!prompt) {
      onProgress?.({ index: i, url: undefined });
      continue;
    }

    if (i > 0) await sleep(STAGGER_DELAY_MS);

    const url = generateImageUrl(prompt, options);
    const loaded = await preloadImage(url);
    results[i] = loaded;
    onProgress?.({ index: i, url: loaded });
  }

  return results;
}
