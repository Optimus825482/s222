"use client";

import { useState } from "react";
import { fetcher } from "@/lib/api";
import { FeatherIcon } from "@/components/xp/xp-feather-icon";

export default function YoutubeSummarizerPanel() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{
    title?: string;
    duration?: string;
    author?: string;
    transcript?: string;
    summary?: string;
    error?: string;
  } | null>(null);

  const handleSummarize = async () => {
    if (!url.trim()) return;
    setLoading(true);
    setResult(null);

    try {
      const data = await fetcher<{
        title?: string;
        duration?: string;
        author?: string;
        duration_seconds?: number;
        channel?: string;
        transcript?: string;
        summary?: string;
        error?: string;
      }>("/api/youtube/summarize", {
        method: "POST",
        body: JSON.stringify({
          url,
          language: "tr",
          target_language: "tr",
          use_agent_summary: true,
          max_summary_length: 1800,
        }),
      });
      setResult({
        ...data,
        duration:
          data.duration ??
          (typeof data.duration_seconds === "number"
            ? `${Math.floor(data.duration_seconds / 60)}:${String(
                data.duration_seconds % 60,
              ).padStart(2, "0")}`
            : undefined),
        author: data.author ?? data.channel,
      });
    } catch (err) {
      setResult({ error: (err as Error).message || "İstek başarısız oldu" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#ECE9D8] p-4 overflow-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4 pb-3 border-b border-[#d6d2c2]">
        <div className="w-10 h-10 rounded-lg bg-red-500 flex items-center justify-center">
          <FeatherIcon name="play" color="white" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-gray-800">
            YouTube Özetleyici
          </h2>
          <p className="text-xs text-gray-600">
            Video transkripsiyonu ve AI özeti
          </p>
        </div>
      </div>

      {/* URL Input */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          YouTube URL
        </label>
        <div className="flex gap-2">
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://www.youtube.com/watch?v=..."
            className="flex-1 px-3 py-2 border border-gray-400 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={async () => {
              try {
                const text = await navigator.clipboard.readText();
                if (text) setUrl(text.trim());
              } catch {
                /* clipboard permission denied */
              }
            }}
            title="Panodaki linki yapıştır"
            className="px-3 py-2 bg-gray-200 border border-gray-400 rounded text-sm hover:bg-gray-300"
          >
            📋
          </button>
          <button
            onClick={handleSummarize}
            disabled={loading || !url.trim()}
            className="px-4 py-2 bg-red-500 text-white rounded font-medium hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "İşleniyor..." : "Özetle"}
          </button>
        </div>
      </div>

      {/* Result */}
      {result && (
        <div className="flex-1 overflow-auto">
          {result.error ? (
            <div className="p-4 bg-red-100 border border-red-400 rounded text-red-700">
              {result.error}
            </div>
          ) : (
            <div className="space-y-4">
              {/* Video Info */}
              {result.title && (
                <div className="p-3 bg-white border border-gray-300 rounded">
                  <h3 className="font-bold text-gray-800 mb-2">
                    {result.title}
                  </h3>
                  <div className="flex gap-4 text-sm text-gray-600">
                    {result.author && <span>👤 {result.author}</span>}
                    {result.duration && <span>⏱️ {result.duration}</span>}
                  </div>
                </div>
              )}

              {/* Summary */}
              {result.summary && (
                <div className="p-3 bg-blue-50 border border-blue-300 rounded">
                  <h4 className="font-bold text-blue-800 mb-2 flex items-center gap-2">
                    <span>📋</span> AI Özeti
                  </h4>
                  <p className="text-sm text-gray-700 whitespace-pre-wrap">
                    {result.summary}
                  </p>
                </div>
              )}

              {/* Transcript */}
              {result.transcript && (
                <div className="p-3 bg-gray-50 border border-gray-300 rounded">
                  <h4 className="font-bold text-gray-800 mb-2 flex items-center gap-2">
                    <span>📝</span> Transkripsiyon
                  </h4>
                  <p className="text-sm text-gray-600 whitespace-pre-wrap max-h-60 overflow-auto">
                    {result.transcript}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {!result && !loading && (
        <div className="flex-1 flex items-center justify-center text-gray-500">
          <div className="text-center">
            <div className="text-4xl mb-2">🎬</div>
            <p>Bir YouTube URL'si girin</p>
            <p className="text-xs mt-1">
              Video transkripsiyonu ve AI özeti alın
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
