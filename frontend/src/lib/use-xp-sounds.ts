"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import startupSrc from "@/assets/sounds/startup.mp3";
import errorSrc from "@/assets/sounds/error.mp3";
import shutdownSrc from "@/assets/sounds/shutdown.mp3";

const SOUNDS = {
  startup: startupSrc,
  error: errorSrc,
  shutdown: shutdownSrc,
} as const;

type SoundName = keyof typeof SOUNDS;

interface XpSoundState {
  volume: number;
  muted: boolean;
}

const STORAGE_KEY = "xp-sound-settings";

function loadSettings(): XpSoundState {
  if (typeof window === "undefined") return { volume: 50, muted: false };
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      return {
        volume:
          typeof parsed.volume === "number"
            ? Math.max(0, Math.min(100, parsed.volume))
            : 50,
        muted: typeof parsed.muted === "boolean" ? parsed.muted : false,
      };
    }
  } catch {
    /* ignore */
  }
  return { volume: 50, muted: false };
}

export function useXpSounds() {
  const [state, setState] = useState<XpSoundState>(loadSettings);
  const audioCache = useRef<Map<string, HTMLAudioElement>>(new Map());

  // Persist settings
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }, [state]);

  // Preload sounds
  useEffect(() => {
    Object.entries(SOUNDS).forEach(([key, src]) => {
      if (!audioCache.current.has(key)) {
        const audio = new Audio(src);
        audio.preload = "auto";
        audioCache.current.set(key, audio);
      }
    });
  }, []);

  const play = useCallback((name: SoundName) => {
    const audio = audioCache.current.get(name);
    if (!audio) return;
    const settings = loadSettings();
    if (settings.muted) return;
    audio.volume = settings.volume / 100;
    audio.currentTime = 0;
    audio.play().catch(() => {
      /* autoplay blocked */
    });
  }, []);

  const setVolume = useCallback((v: number) => {
    const clamped = Math.max(0, Math.min(100, Math.round(v)));
    setState((prev) => ({ ...prev, volume: clamped }));
  }, []);

  const toggleMute = useCallback(() => {
    setState((prev) => ({ ...prev, muted: !prev.muted }));
  }, []);

  return {
    volume: state.volume,
    muted: state.muted,
    play,
    setVolume,
    toggleMute,
  };
}
