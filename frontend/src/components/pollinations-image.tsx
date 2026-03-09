"use client";

import React, { useState, useEffect, useRef } from "react";
import { Image as ImageIcon, Loader2 } from "lucide-react";

/**
 * Rate-limit-aware image component for Pollinations.ai.
 *
 * Instead of using a raw <img src=...> (which lets the browser retry
 * infinitely on 429/5xx), this fetches the image as a blob with
 * controlled retry + exponential backoff, then renders via object URL.
 */

const MAX_RETRIES = 2;
const BASE_DELAY_MS = 3000;

type Status = "idle" | "loading" | "loaded" | "error";

interface PollinationsImageProps {
  src: string | undefined;
  alt: string;
  className?: string;
  /** Show a placeholder icon on failure instead of nothing */
  placeholderClassName?: string;
  /** Called when image loads or permanently fails */
  onStatusChange?: (status: Status) => void;
}

export default function PollinationsImage({
  src,
  alt,
  className = "",
  placeholderClassName = "",
  onStatusChange,
}: PollinationsImageProps) {
  const [status, setStatus] = useState<Status>("idle");
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const blobUrlRef = useRef<string | null>(null);

  useEffect(() => {
    // Cleanup previous
    abortRef.current?.abort();
    if (blobUrlRef.current) {
      URL.revokeObjectURL(blobUrlRef.current);
      blobUrlRef.current = null;
    }
    setBlobUrl(null);

    if (!src) {
      setStatus("idle");
      onStatusChange?.("idle");
      return;
    }

    const controller = new AbortController();
    abortRef.current = controller;
    let cancelled = false;

    const load = async () => {
      setStatus("loading");
      onStatusChange?.("loading");

      for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
        if (cancelled) return;

        try {
          const res = await fetch(src, { signal: controller.signal });

          if (res.ok) {
            const blob = await res.blob();
            if (cancelled) return;
            const url = URL.createObjectURL(blob);
            blobUrlRef.current = url;
            setBlobUrl(url);
            setStatus("loaded");
            onStatusChange?.("loaded");
            return;
          }

          // Rate limited or server error — retry with backoff
          if (res.status === 429 || res.status >= 500) {
            if (attempt < MAX_RETRIES) {
              const delay = BASE_DELAY_MS * Math.pow(2, attempt);
              console.warn(
                `⏳ PollinationsImage retry ${attempt + 1}/${MAX_RETRIES} in ${delay}ms (${res.status})`,
              );
              await new Promise((r) => setTimeout(r, delay));
              continue;
            }
          }

          // Non-retryable error or retries exhausted
          throw new Error(`HTTP ${res.status}`);
        } catch (err: any) {
          if (err.name === "AbortError" || cancelled) return;
          if (attempt === MAX_RETRIES) {
            console.warn(
              `❌ PollinationsImage failed: ${src.slice(0, 80)}…`,
              err.message,
            );
            if (!cancelled) {
              setStatus("error");
              onStatusChange?.("error");
            }
            return;
          }
          // Network error — retry
          const delay = BASE_DELAY_MS * Math.pow(2, attempt);
          await new Promise((r) => setTimeout(r, delay));
        }
      }
    };

    load();

    return () => {
      cancelled = true;
      controller.abort();
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current);
        blobUrlRef.current = null;
      }
    };
  }, [src]); // eslint-disable-line react-hooks/exhaustive-deps

  if (status === "loaded" && blobUrl) {
    return <img src={blobUrl} alt={alt} className={className} />;
  }

  if (status === "loading") {
    return (
      <div
        className={`flex items-center justify-center ${placeholderClassName || className}`}
      >
        <Loader2 className="w-8 h-8 text-purple-400/50 animate-spin" />
      </div>
    );
  }

  if (status === "error" || (!src && status === "idle")) {
    return (
      <div
        className={`flex items-center justify-center ${placeholderClassName || className}`}
      >
        <ImageIcon className="w-12 h-12 text-gray-300/50" />
      </div>
    );
  }

  // idle with src — will start loading
  return null;
}
