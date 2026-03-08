"use client";

import { useState, useCallback, useEffect } from "react";
import { imageStudioApi, IMAGE_MODELS, type ImageListItem } from "@/lib/api";
import { Download, Sparkles, ImageIcon, Trash2, ImagePlus, FolderOpen } from "lucide-react";

type TabId = "create" | "gallery";

export function ImageStudioPanel() {
  const [tab, setTab] = useState<TabId>("create");
  const [prompt, setPrompt] = useState("");
  const [model, setModel] = useState<string>("flux");
  const [improving, setImproving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{
    filename: string;
    download_url: string;
    image_url: string;
    image_base64: string;
    model: string;
    prompt: string;
  } | null>(null);

  const [galleryList, setGalleryList] = useState<ImageListItem[]>([]);
  const [galleryLoading, setGalleryLoading] = useState(false);
  const [galleryError, setGalleryError] = useState<string | null>(null);

  const loadGallery = useCallback(async () => {
    setGalleryLoading(true);
    setGalleryError(null);
    try {
      const list = await imageStudioApi.list();
      setGalleryList(list);
    } catch (e) {
      setGalleryError(e instanceof Error ? e.message : "Liste yüklenemedi");
      setGalleryList([]);
    } finally {
      setGalleryLoading(false);
    }
  }, []);

  useEffect(() => {
    if (tab === "gallery") loadGallery();
  }, [tab, loadGallery]);

  const handleImprove = async () => {
    const p = prompt.trim();
    if (!p) {
      setError("Önce bir prompt yazın.");
      return;
    }
    setError(null);
    setImproving(true);
    try {
      const { improved_prompt } = await imageStudioApi.improvePrompt(p);
      setPrompt(improved_prompt);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Prompt iyileştirilemedi.");
    } finally {
      setImproving(false);
    }
  };

  const handleGenerate = async () => {
    const p = prompt.trim();
    if (!p) {
      setError("Önce bir prompt yazın.");
      return;
    }
    setError(null);
    setGenerating(true);
    setResult(null);
    try {
      const data = await imageStudioApi.generate(p, model, 1024, 1024);
      setResult(data);
      loadGallery();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Görsel oluşturulamadı.");
    } finally {
      setGenerating(false);
    }
  };

  const downloadViaBase64 = () => {
    if (!result?.image_base64) return;
    const link = document.createElement("a");
    link.href = `data:image/png;base64,${result.image_base64}`;
    link.download = result.filename.replace(/\.[^.]+$/, ".png") || "image.png";
    link.click();
  };

  const handleDownloadSaved = async (filename: string) => {
    try {
      const blob = await imageStudioApi.downloadBlob(filename);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setGalleryError(e instanceof Error ? e.message : "İndirilemedi");
    }
  };

  const handleDeleteSaved = async (filename: string) => {
    if (!confirm(`"${filename}" silinsin mi?`)) return;
    try {
      await imageStudioApi.delete(filename);
      setGalleryList((prev) => prev.filter((i) => i.filename !== filename));
    } catch (e) {
      setGalleryError(e instanceof Error ? e.message : "Silinemedi");
    }
  };

  const formatDate = (ts: number) => {
    try {
      return new Date(ts * 1000).toLocaleString("tr-TR", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return "";
    }
  };

  return (
    <div className="flex flex-col h-full bg-surface rounded-lg border border-border overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-border bg-surface-raised">
        <ImageIcon className="w-5 h-5 text-violet-400" />
        <h2 className="text-base font-semibold text-slate-200">Görsel Stüdyo</h2>
      </div>

      <div className="flex border-b border-border">
        <button
          type="button"
          onClick={() => setTab("create")}
          className={`flex items-center gap-1.5 px-4 py-2 text-xs font-medium transition-colors ${tab === "create" ? "border-b-2 border-violet-400 text-violet-400" : "text-slate-500 hover:text-slate-300"}`}
        >
          <ImagePlus className="w-4 h-4" />
          Oluştur
        </button>
        <button
          type="button"
          onClick={() => setTab("gallery")}
          className={`flex items-center gap-1.5 px-4 py-2 text-xs font-medium transition-colors ${tab === "gallery" ? "border-b-2 border-violet-400 text-violet-400" : "text-slate-500 hover:text-slate-300"}`}
        >
          <FolderOpen className="w-4 h-4" />
          Kaydedilenler
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {tab === "create" && (
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">Prompt (görsel açıklaması)</label>
              <div className="flex gap-2">
                <textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Örn: A professional diagram of a multi-agent system architecture..."
                  maxLength={250}
                  className="flex-1 min-h-[88px] px-3 py-2 text-sm bg-surface-overlay border border-border rounded-lg text-slate-200 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-violet-500/50 resize-y"
                  rows={3}
                />
                <button
                  type="button"
                  onClick={handleImprove}
                  disabled={improving || !prompt.trim()}
                  className="shrink-0 self-start flex items-center gap-1.5 px-3 py-2 rounded-lg bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 disabled:opacity-50 disabled:pointer-events-none text-xs font-medium transition-colors"
                  title="DeepSeek ile promptu iyileştir"
                >
                  <Sparkles className="w-4 h-4" />
                  {improving ? "İyileştiriliyor…" : "Geliştir"}
                </button>
              </div>
              <p className="text-[10px] text-slate-500 mt-1">
                &quot;Geliştir&quot; ile DeepSeek promptu iyileştirir. Prompt en fazla 200 karakter.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Model</label>
                <select
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="px-3 py-2 text-sm bg-surface-overlay border border-border rounded-lg text-slate-200 focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                >
                  {IMAGE_MODELS.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              </div>
              <button
                type="button"
                onClick={handleGenerate}
                disabled={generating || !prompt.trim()}
                className="mt-6 px-4 py-2 rounded-lg bg-violet-500 hover:bg-violet-600 text-white text-sm font-medium disabled:opacity-50 disabled:pointer-events-none transition-colors"
              >
                {generating ? "Oluşturuluyor…" : "Görsel Oluştur"}
              </button>
            </div>

            {error && (
              <div className="px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                {error}
              </div>
            )}

            {result && (
              <div className="rounded-lg border border-border bg-surface-raised overflow-hidden">
                <div className="p-2 border-b border-border flex flex-wrap items-center justify-between gap-2">
                  <span className="text-xs text-slate-500">
                    Model: {result.model} · {result.prompt.slice(0, 40)}…
                  </span>
                  <div className="flex items-center gap-2">
                    {result.image_url && (
                      <a
                        href={result.image_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-cyan-400 hover:underline truncate max-w-[180px]"
                        title={result.image_url}
                      >
                        Görsel URL
                      </a>
                    )}
                    <button
                      type="button"
                      onClick={downloadViaBase64}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-violet-500/20 text-violet-400 hover:bg-violet-500/30 text-xs font-medium transition-colors"
                    >
                      <Download className="w-4 h-4" />
                      İndir
                    </button>
                  </div>
                </div>
                <div className="relative w-full aspect-square max-h-[70vh] bg-slate-900">
                  <img
                    src={`data:image/png;base64,${result.image_base64}`}
                    alt={result.prompt}
                    className="w-full h-full object-contain"
                  />
                </div>
              </div>
            )}

            {generating && (
              <div className="flex items-center justify-center py-8 text-slate-500 text-sm">
                Görsel oluşturuluyor, lütfen bekleyin…
              </div>
            )}
          </div>
        )}

        {tab === "gallery" && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-500">data/images/ içindeki görseller</span>
              <button
                type="button"
                onClick={loadGallery}
                disabled={galleryLoading}
                className="text-xs text-violet-400 hover:underline disabled:opacity-50"
              >
                {galleryLoading ? "Yükleniyor…" : "Yenile"}
              </button>
            </div>
            {galleryError && (
              <div className="px-3 py-2 rounded-lg bg-red-500/10 text-red-400 text-sm">
                {galleryError}
              </div>
            )}
            {galleryList.length === 0 && !galleryLoading && (
              <p className="text-sm text-slate-500 py-6 text-center">
                Henüz kaydedilmiş görsel yok. &quot;Oluştur&quot; sekmesinden yeni görsel üretebilirsiniz.
              </p>
            )}
            <ul className="space-y-2">
              {galleryList.map((item) => (
                <li
                  key={item.filename}
                  className="flex items-center gap-3 px-3 py-2 rounded-lg bg-surface-raised border border-border"
                >
                  <span className="flex-1 min-w-0 truncate text-sm text-slate-200" title={item.filename}>
                    {item.filename}
                  </span>
                  <span className="text-xs text-slate-500 shrink-0">{item.size_kb} KB</span>
                  <span className="text-xs text-slate-500 shrink-0">{formatDate(item.created_at)}</span>
                  <button
                    type="button"
                    onClick={() => handleDownloadSaved(item.filename)}
                    className="p-1.5 rounded-lg text-slate-400 hover:bg-violet-500/20 hover:text-violet-400 transition-colors"
                    title="İndir"
                  >
                    <Download className="w-4 h-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDeleteSaved(item.filename)}
                    className="p-1.5 rounded-lg text-slate-400 hover:bg-red-500/20 hover:text-red-400 transition-colors"
                    title="Sil"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
