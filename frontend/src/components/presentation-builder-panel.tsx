"use client";

import React, { useState, useCallback, useRef } from "react";
import {
  Presentation,
  Sparkles,
  Plus,
  Trash2,
  ChevronLeft,
  ChevronRight,
  Download,
  Image as ImageIcon,
  RefreshCw,
  Loader2,
  Wand2,
  Eye,
  Edit3,
  Layout,
  FileText,
  X,
  Maximize2,
  Minimize2,
  MessageSquare,
} from "lucide-react";
import { fetcher } from "@/lib/api";
import { generateImageUrl, loadImagesStaggered } from "@/lib/pollinations";
import PollinationsImage from "./pollinations-image";

/* ─── Types ─────────────────────────────────────────────────── */

interface Slide {
  id: number;
  title: string;
  content: string;
  bullets: string[];
  notes: string;
  image_prompt: string;
  layout:
    | "title"
    | "content"
    | "two-column"
    | "image-focus"
    | "quote"
    | "closing";
  imageUrl?: string;
}

type ViewMode = "edit" | "preview";

const LAYOUT_OPTIONS = [
  { value: "title", label: "Başlık", icon: "🎯" },
  { value: "content", label: "İçerik", icon: "📝" },
  { value: "two-column", label: "İki Sütun", icon: "📊" },
  { value: "image-focus", label: "Görsel Odak", icon: "🖼️" },
  { value: "quote", label: "Alıntı", icon: "💬" },
  { value: "closing", label: "Kapanış", icon: "🎬" },
] as const;

const STYLE_OPTIONS = [
  { value: "professional", label: "Profesyonel" },
  { value: "creative", label: "Yaratıcı" },
  { value: "minimal", label: "Minimal" },
  { value: "academic", label: "Akademik" },
  { value: "corporate", label: "Kurumsal" },
];

/* ─── Main Component ────────────────────────────────────────── */

export default function PresentationBuilderPanel() {
  // State
  const [slides, setSlides] = useState<Slide[]>([]);
  const [currentSlideIndex, setCurrentSlideIndex] = useState(0);
  const [prompt, setPrompt] = useState("");
  const [slideCount, setSlideCount] = useState(8);
  const [style, setStyle] = useState("professional");
  const [viewMode, setViewMode] = useState<ViewMode>("edit");
  const [isGenerating, setIsGenerating] = useState(false);
  const [isEnhancing, setIsEnhancing] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [imageDialogOpen, setImageDialogOpen] = useState(false);
  const [imageInstruction, setImageInstruction] = useState("");
  const [isGeneratingImage, setIsGeneratingImage] = useState(false);
  const [error, setError] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

  const currentSlide = slides[currentSlideIndex] || null;

  /* ─── API Calls ───────────────────────────────────────────── */

  const enhancePrompt = useCallback(async () => {
    if (!prompt.trim()) return;
    setIsEnhancing(true);
    setError("");
    try {
      const res = await fetcher<{
        enhanced_prompt: string;
        suggested_slide_count: number;
        suggested_style: string;
      }>("/api/presentations/enhance-prompt", {
        method: "POST",
        body: JSON.stringify({ prompt: prompt.trim() }),
      });
      setPrompt(res.enhanced_prompt);
      setSlideCount(res.suggested_slide_count);
      setStyle(res.suggested_style);
    } catch (e: any) {
      setError(e.message || "Prompt geliştirme başarısız");
    } finally {
      setIsEnhancing(false);
    }
  }, [prompt]);

  const generatePresentation = useCallback(async () => {
    if (!prompt.trim()) return;
    setIsGenerating(true);
    setError("");
    try {
      const res = await fetcher<{ slides: Slide[] }>(
        "/api/presentations/generate",
        {
          method: "POST",
          body: JSON.stringify({
            prompt: prompt.trim(),
            slide_count: slideCount,
            language: "tr",
            style,
          }),
        },
      );
      // Set slides immediately without images, then load images staggered
      const initialSlides = res.slides.map((s) => ({
        ...s,
        imageUrl: undefined as string | undefined,
      }));
      setSlides(initialSlides);
      setCurrentSlideIndex(0);
      setViewMode("edit");

      // Staggered image loading to avoid Pollinations 429 rate limit
      const prompts = res.slides.map((s) => s.image_prompt || undefined);
      loadImagesStaggered(
        prompts,
        { width: 1200, height: 675, model: "flux", nologo: true },
        ({ index, url }) => {
          setSlides((prev) => {
            const next = [...prev];
            if (next[index]) next[index] = { ...next[index], imageUrl: url };
            return next;
          });
        },
      );
    } catch (e: any) {
      setError(e.message || "Sunum oluşturma başarısız");
    } finally {
      setIsGenerating(false);
    }
  }, [prompt, slideCount, style]);

  const regenerateSlide = useCallback(
    async (instruction: string) => {
      if (!currentSlide) return;
      setIsRegenerating(true);
      setError("");
      try {
        const context = slides.map((s) => s.title).join(", ");
        const res = await fetcher<{ slide: Slide }>(
          "/api/presentations/regenerate-slide",
          {
            method: "POST",
            body: JSON.stringify({
              presentation_context: `Topic: ${prompt}. Slides: ${context}`,
              slide_index: currentSlideIndex,
              instruction,
            }),
          },
        );
        const updated = {
          ...res.slide,
          imageUrl: res.slide.image_prompt
            ? generateImageUrl(res.slide.image_prompt, {
                width: 1200,
                height: 675,
                model: "flux",
                nologo: true,
              })
            : currentSlide.imageUrl,
        };
        setSlides((prev) => {
          const next = [...prev];
          next[currentSlideIndex] = updated;
          return next;
        });
      } catch (e: any) {
        setError(e.message || "Slayt yenileme başarısız");
      } finally {
        setIsRegenerating(false);
      }
    },
    [currentSlide, currentSlideIndex, slides, prompt],
  );

  const regenerateImage = useCallback(async () => {
    if (!currentSlide) return;
    setIsGeneratingImage(true);
    setError("");
    try {
      const res = await fetcher<{ image_prompt: string }>(
        "/api/presentations/generate-image-prompt",
        {
          method: "POST",
          body: JSON.stringify({
            slide_title: currentSlide.title,
            slide_content: currentSlide.content,
            user_instruction: imageInstruction,
          }),
        },
      );
      const newUrl = generateImageUrl(res.image_prompt, {
        width: 1200,
        height: 675,
        model: "flux",
        nologo: true,
      });
      setSlides((prev) => {
        const next = [...prev];
        next[currentSlideIndex] = {
          ...next[currentSlideIndex],
          image_prompt: res.image_prompt,
          imageUrl: newUrl,
        };
        return next;
      });
      setImageDialogOpen(false);
      setImageInstruction("");
    } catch (e: any) {
      setError(e.message || "Görsel oluşturma başarısız");
    } finally {
      setIsGeneratingImage(false);
    }
  }, [currentSlide, currentSlideIndex, imageInstruction]);

  /* ─── Slide Edit Helpers ──────────────────────────────────── */

  const updateSlide = useCallback(
    (field: keyof Slide, value: any) => {
      setSlides((prev) => {
        const next = [...prev];
        next[currentSlideIndex] = {
          ...next[currentSlideIndex],
          [field]: value,
        };
        return next;
      });
    },
    [currentSlideIndex],
  );

  const updateBullet = useCallback(
    (bulletIndex: number, value: string) => {
      setSlides((prev) => {
        const next = [...prev];
        const bullets = [...next[currentSlideIndex].bullets];
        bullets[bulletIndex] = value;
        next[currentSlideIndex] = { ...next[currentSlideIndex], bullets };
        return next;
      });
    },
    [currentSlideIndex],
  );

  const addBullet = useCallback(() => {
    setSlides((prev) => {
      const next = [...prev];
      next[currentSlideIndex] = {
        ...next[currentSlideIndex],
        bullets: [...next[currentSlideIndex].bullets, ""],
      };
      return next;
    });
  }, [currentSlideIndex]);

  const removeBullet = useCallback(
    (bulletIndex: number) => {
      setSlides((prev) => {
        const next = [...prev];
        const bullets = next[currentSlideIndex].bullets.filter(
          (_, i) => i !== bulletIndex,
        );
        next[currentSlideIndex] = { ...next[currentSlideIndex], bullets };
        return next;
      });
    },
    [currentSlideIndex],
  );

  const addSlide = useCallback(() => {
    const newSlide: Slide = {
      id: slides.length + 1,
      title: "Yeni Slayt",
      content: "",
      bullets: [""],
      notes: "",
      image_prompt: "",
      layout: "content",
    };
    setSlides((prev) => [...prev, newSlide]);
    setCurrentSlideIndex(slides.length);
  }, [slides.length]);

  const deleteSlide = useCallback(() => {
    if (slides.length <= 1) return;
    setSlides((prev) => prev.filter((_, i) => i !== currentSlideIndex));
    setCurrentSlideIndex((prev) => Math.max(0, prev - 1));
  }, [currentSlideIndex, slides.length]);

  /* ─── Export as HTML ──────────────────────────────────────── */

  const exportAsHtml = useCallback(() => {
    if (slides.length === 0) return;
    const slidesHtml = slides
      .map(
        (s, i) => `
      <div class="slide" style="page-break-after:always;padding:60px;min-height:100vh;display:flex;flex-direction:column;justify-content:center;font-family:system-ui,sans-serif;background:${
        s.layout === "title" || s.layout === "closing"
          ? "linear-gradient(135deg,#1e293b,#0f172a)"
          : "#ffffff"
      };color:${s.layout === "title" || s.layout === "closing" ? "#f1f5f9" : "#1e293b"}">
        <h1 style="font-size:2.5em;margin-bottom:0.5em">${s.title}</h1>
        ${s.content ? `<p style="font-size:1.2em;line-height:1.6;margin-bottom:1em">${s.content}</p>` : ""}
        ${
          s.bullets.length > 0
            ? `<ul style="font-size:1.1em;line-height:1.8">${s.bullets.map((b) => `<li>${b}</li>`).join("")}</ul>`
            : ""
        }
        ${s.imageUrl ? `<img src="${s.imageUrl}" style="max-width:80%;margin:1em auto;border-radius:12px" alt="${s.title}" />` : ""}
        <div style="position:absolute;bottom:30px;right:40px;font-size:0.8em;opacity:0.5">${i + 1} / ${slides.length}</div>
      </div>`,
      )
      .join("\n");

    const html = `<!DOCTYPE html>
<html lang="tr"><head><meta charset="UTF-8"><title>${slides[0]?.title || "Sunum"}</title>
<style>*{margin:0;padding:0;box-sizing:border-box}.slide{position:relative}</style>
</head><body>${slidesHtml}</body></html>`;

    const blob = new Blob([html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "presentation.html";
    a.click();
    URL.revokeObjectURL(url);
  }, [slides]);

  /* ─── Fullscreen Presentation Mode ───────────────────────── */

  const toggleFullscreen = useCallback(() => {
    if (!isFullscreen) {
      containerRef.current?.requestFullscreen?.();
      setIsFullscreen(true);
      setViewMode("preview");
    } else {
      document.exitFullscreen?.();
      setIsFullscreen(false);
    }
  }, [isFullscreen]);

  React.useEffect(() => {
    const handler = () => {
      if (!document.fullscreenElement) setIsFullscreen(false);
    };
    document.addEventListener("fullscreenchange", handler);
    return () => document.removeEventListener("fullscreenchange", handler);
  }, []);

  // Keyboard navigation in fullscreen
  React.useEffect(() => {
    if (!isFullscreen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === " ") {
        e.preventDefault();
        setCurrentSlideIndex((p) => Math.min(p + 1, slides.length - 1));
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        setCurrentSlideIndex((p) => Math.max(p - 1, 0));
      } else if (e.key === "Escape") {
        document.exitFullscreen?.();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isFullscreen, slides.length]);

  /* ─── Render: Empty State (Prompt Input) ──────────────────── */

  if (slides.length === 0) {
    return (
      <div className="flex flex-col h-full bg-surface-alt">
        <div className="flex items-center gap-2 px-4 py-3 border-b border-white/10">
          <Presentation className="w-5 h-5 text-purple-400" />
          <span className="font-semibold text-sm text-white/90">
            AI Sunum Oluşturucu
          </span>
        </div>

        <div className="flex-1 flex items-center justify-center p-6">
          <div className="w-full max-w-lg space-y-5">
            <div className="text-center space-y-2">
              <div className="w-16 h-16 mx-auto rounded-2xl bg-purple-500/20 flex items-center justify-center">
                <Sparkles className="w-8 h-8 text-purple-400" />
              </div>
              <h2 className="text-xl font-bold text-white/90">Sunum Oluştur</h2>
              <p className="text-sm text-white/50">
                Konunuzu yazın, AI araştırma yaparak slaytlarınızı hazırlasın
              </p>
            </div>

            {error && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-300 text-sm">
                {error}
              </div>
            )}

            <div className="space-y-3">
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Örn: Yapay zeka ve eğitimde dönüşüm hakkında bir sunum hazırla..."
                className="w-full h-28 px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white/90 text-sm placeholder:text-white/30 resize-none focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/30"
                disabled={isGenerating || isEnhancing}
              />

              <div className="flex gap-3">
                <div className="flex-1">
                  <label className="text-xs text-white/40 mb-1 block">
                    Slayt Sayısı
                  </label>
                  <input
                    type="number"
                    min={3}
                    max={30}
                    value={slideCount}
                    onChange={(e) =>
                      setSlideCount(
                        Math.max(3, Math.min(30, Number(e.target.value) || 8)),
                      )
                    }
                    className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white/90 text-sm focus:outline-none focus:border-purple-500/50"
                    disabled={isGenerating}
                  />
                </div>
                <div className="flex-1">
                  <label className="text-xs text-white/40 mb-1 block">
                    Stil
                  </label>
                  <select
                    value={style}
                    onChange={(e) => setStyle(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white/90 text-sm focus:outline-none focus:border-purple-500/50"
                    disabled={isGenerating}
                  >
                    {STYLE_OPTIONS.map((s) => (
                      <option key={s.value} value={s.value}>
                        {s.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={enhancePrompt}
                  disabled={!prompt.trim() || isEnhancing || isGenerating}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white/70 text-sm hover:bg-white/10 disabled:opacity-40 transition-colors"
                >
                  {isEnhancing ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Wand2 className="w-4 h-4" />
                  )}
                  Prompt Geliştir
                </button>
                <button
                  onClick={generatePresentation}
                  disabled={!prompt.trim() || isGenerating}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-sm font-medium disabled:opacity-40 transition-colors"
                >
                  {isGenerating ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Araştırılıyor & Oluşturuluyor...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      Sunum Oluştur
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  /* ─── Render: Slide Editor ────────────────────────────────── */

  return (
    <div ref={containerRef} className="flex flex-col h-full bg-surface-alt">
      {/* Top Bar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/10 shrink-0">
        <div className="flex items-center gap-2">
          <Presentation className="w-4 h-4 text-purple-400" />
          <span className="text-sm font-semibold text-white/90">AI Sunum</span>
          <span className="text-xs text-white/40">{slides.length} slayt</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() =>
              setViewMode(viewMode === "edit" ? "preview" : "edit")
            }
            className="p-1.5 rounded-lg hover:bg-white/10 text-white/60 hover:text-white/90 transition-colors"
            title={viewMode === "edit" ? "Önizleme" : "Düzenle"}
          >
            {viewMode === "edit" ? (
              <Eye className="w-4 h-4" />
            ) : (
              <Edit3 className="w-4 h-4" />
            )}
          </button>
          <button
            onClick={toggleFullscreen}
            className="p-1.5 rounded-lg hover:bg-white/10 text-white/60 hover:text-white/90 transition-colors"
            title="Tam Ekran"
          >
            {isFullscreen ? (
              <Minimize2 className="w-4 h-4" />
            ) : (
              <Maximize2 className="w-4 h-4" />
            )}
          </button>
          <button
            onClick={exportAsHtml}
            className="p-1.5 rounded-lg hover:bg-white/10 text-white/60 hover:text-white/90 transition-colors"
            title="HTML İndir"
          >
            <Download className="w-4 h-4" />
          </button>
          <button
            onClick={() => {
              setSlides([]);
              setCurrentSlideIndex(0);
            }}
            className="p-1.5 rounded-lg hover:bg-white/10 text-red-400/70 hover:text-red-400 transition-colors"
            title="Yeni Sunum"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {error && (
        <div className="mx-4 mt-2 p-2 rounded-lg bg-red-500/10 border border-red-500/30 text-red-300 text-xs">
          {error}
          <button onClick={() => setError("")} className="ml-2 underline">
            kapat
          </button>
        </div>
      )}

      <div className="flex flex-1 min-h-0">
        {/* Slide Thumbnails Sidebar */}
        <div className="w-44 border-r border-white/10 overflow-y-auto shrink-0 p-2 space-y-1.5">
          {slides.map((s, i) => (
            <button
              key={s.id}
              onClick={() => setCurrentSlideIndex(i)}
              className={`w-full text-left p-2 rounded-lg transition-colors ${
                i === currentSlideIndex
                  ? "bg-purple-500/20 border border-purple-500/40"
                  : "bg-white/5 border border-transparent hover:bg-white/10"
              }`}
            >
              <div className="flex items-center gap-1.5 mb-1">
                <span className="text-[10px] text-white/40 font-mono">
                  {i + 1}
                </span>
                <span className="text-[10px] text-white/30">
                  {LAYOUT_OPTIONS.find((l) => l.value === s.layout)?.icon}
                </span>
              </div>
              <p className="text-xs text-white/70 truncate">{s.title}</p>
            </button>
          ))}
          <button
            onClick={addSlide}
            className="w-full flex items-center justify-center gap-1 p-2 rounded-lg border border-dashed border-white/20 text-white/40 hover:text-white/60 hover:border-white/30 transition-colors text-xs"
          >
            <Plus className="w-3 h-3" /> Slayt Ekle
          </button>
        </div>

        {/* Main Canvas Area */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Slide Preview / Canvas */}
          <div className="flex-1 p-4 overflow-auto">
            {currentSlide && (
              <SlideCanvas
                slide={currentSlide}
                viewMode={viewMode}
                onUpdate={updateSlide}
                slideNumber={currentSlideIndex + 1}
                totalSlides={slides.length}
              />
            )}
          </div>

          {/* Bottom Controls */}
          <div className="shrink-0 border-t border-white/10 px-4 py-2 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentSlideIndex((p) => Math.max(0, p - 1))}
                disabled={currentSlideIndex === 0}
                className="p-1.5 rounded-lg hover:bg-white/10 text-white/60 disabled:opacity-30 transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-xs text-white/50 font-mono min-w-[60px] text-center">
                {currentSlideIndex + 1} / {slides.length}
              </span>
              <button
                onClick={() =>
                  setCurrentSlideIndex((p) =>
                    Math.min(slides.length - 1, p + 1),
                  )
                }
                disabled={currentSlideIndex === slides.length - 1}
                className="p-1.5 rounded-lg hover:bg-white/10 text-white/60 disabled:opacity-30 transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>

            {viewMode === "edit" && currentSlide && (
              <div className="flex items-center gap-1.5">
                {/* Layout selector */}
                <select
                  value={currentSlide.layout}
                  onChange={(e) => updateSlide("layout", e.target.value)}
                  className="px-2 py-1 rounded-lg bg-white/5 border border-white/10 text-white/70 text-xs focus:outline-none"
                >
                  {LAYOUT_OPTIONS.map((l) => (
                    <option key={l.value} value={l.value}>
                      {l.icon} {l.label}
                    </option>
                  ))}
                </select>

                {/* Regenerate slide */}
                <button
                  onClick={() => {
                    const instruction = window.prompt(
                      "Bu slaytı nasıl değiştirmek istiyorsunuz?",
                    );
                    if (instruction) regenerateSlide(instruction);
                  }}
                  disabled={isRegenerating}
                  className="flex items-center gap-1 px-2 py-1 rounded-lg bg-white/5 border border-white/10 text-white/60 text-xs hover:bg-white/10 disabled:opacity-40 transition-colors"
                  title="AI ile Slaytı Yenile"
                >
                  {isRegenerating ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    <RefreshCw className="w-3 h-3" />
                  )}
                  Yenile
                </button>

                {/* Image regenerate */}
                <button
                  onClick={() => setImageDialogOpen(true)}
                  className="flex items-center gap-1 px-2 py-1 rounded-lg bg-white/5 border border-white/10 text-white/60 text-xs hover:bg-white/10 transition-colors"
                  title="Görseli Değiştir"
                >
                  <ImageIcon className="w-3 h-3" />
                  Görsel
                </button>

                {/* Delete slide */}
                <button
                  onClick={deleteSlide}
                  disabled={slides.length <= 1}
                  className="p-1 rounded-lg hover:bg-red-500/20 text-red-400/60 hover:text-red-400 disabled:opacity-30 transition-colors"
                  title="Slaytı Sil"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Right Panel: Notes & Edit Fields (edit mode only) */}
        {viewMode === "edit" && currentSlide && (
          <div className="w-64 border-l border-white/10 overflow-y-auto shrink-0 p-3 space-y-3">
            <div>
              <label className="text-[10px] uppercase tracking-wider text-white/30 mb-1 block">
                Başlık
              </label>
              <input
                value={currentSlide.title}
                onChange={(e) => updateSlide("title", e.target.value)}
                className="w-full px-2 py-1.5 rounded-lg bg-white/5 border border-white/10 text-white/90 text-xs focus:outline-none focus:border-purple-500/50"
              />
            </div>

            <div>
              <label className="text-[10px] uppercase tracking-wider text-white/30 mb-1 block">
                İçerik
              </label>
              <textarea
                value={currentSlide.content}
                onChange={(e) => updateSlide("content", e.target.value)}
                rows={3}
                className="w-full px-2 py-1.5 rounded-lg bg-white/5 border border-white/10 text-white/90 text-xs resize-none focus:outline-none focus:border-purple-500/50"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-[10px] uppercase tracking-wider text-white/30">
                  Maddeler
                </label>
                <button
                  onClick={addBullet}
                  className="text-[10px] text-purple-400 hover:text-purple-300"
                >
                  + Ekle
                </button>
              </div>
              <div className="space-y-1">
                {currentSlide.bullets.map((b, bi) => (
                  <div key={bi} className="flex gap-1">
                    <input
                      value={b}
                      onChange={(e) => updateBullet(bi, e.target.value)}
                      className="flex-1 px-2 py-1 rounded bg-white/5 border border-white/10 text-white/80 text-xs focus:outline-none focus:border-purple-500/50"
                      placeholder={`Madde ${bi + 1}`}
                    />
                    <button
                      onClick={() => removeBullet(bi)}
                      className="p-1 text-red-400/50 hover:text-red-400"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <label className="text-[10px] uppercase tracking-wider text-white/30 mb-1 block">
                <MessageSquare className="w-3 h-3 inline mr-1" />
                Konuşmacı Notları
              </label>
              <textarea
                value={currentSlide.notes}
                onChange={(e) => updateSlide("notes", e.target.value)}
                rows={3}
                className="w-full px-2 py-1.5 rounded-lg bg-white/5 border border-white/10 text-white/70 text-xs resize-none focus:outline-none focus:border-purple-500/50"
                placeholder="Sunum sırasında hatırlatmalar..."
              />
            </div>

            <div>
              <label className="text-[10px] uppercase tracking-wider text-white/30 mb-1 block">
                Görsel Prompt
              </label>
              <textarea
                value={currentSlide.image_prompt}
                onChange={(e) => updateSlide("image_prompt", e.target.value)}
                rows={2}
                className="w-full px-2 py-1.5 rounded-lg bg-white/5 border border-white/10 text-white/60 text-xs resize-none focus:outline-none focus:border-purple-500/50 font-mono"
                placeholder="English image prompt..."
              />
            </div>
          </div>
        )}
      </div>

      {/* Image Regeneration Dialog */}
      {imageDialogOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-[#1a1f2e] border border-white/10 rounded-2xl p-6 w-full max-w-md shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-white/90 flex items-center gap-2">
                <ImageIcon className="w-4 h-4 text-purple-400" />
                Görseli Değiştir
              </h3>
              <button
                onClick={() => {
                  setImageDialogOpen(false);
                  setImageInstruction("");
                }}
                className="p-1 rounded-lg hover:bg-white/10 text-white/40"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {currentSlide?.imageUrl && (
              <div className="mb-3 rounded-lg overflow-hidden border border-white/10">
                <PollinationsImage
                  src={currentSlide.imageUrl}
                  alt="Mevcut görsel"
                  className="w-full h-32 object-cover"
                  placeholderClassName="w-full h-32"
                />
              </div>
            )}

            <textarea
              value={imageInstruction}
              onChange={(e) => setImageInstruction(e.target.value)}
              placeholder="Görselin nasıl değişmesini istiyorsunuz? Örn: Daha modern ve teknolojik bir görsel olsun, mavi tonlarında..."
              className="w-full h-24 px-3 py-2 rounded-xl bg-white/5 border border-white/10 text-white/90 text-sm placeholder:text-white/30 resize-none focus:outline-none focus:border-purple-500/50 mb-3"
              disabled={isGeneratingImage}
            />

            <div className="flex gap-2">
              <button
                onClick={() => {
                  setImageDialogOpen(false);
                  setImageInstruction("");
                }}
                className="flex-1 px-4 py-2 rounded-xl bg-white/5 border border-white/10 text-white/60 text-sm hover:bg-white/10 transition-colors"
              >
                İptal
              </button>
              <button
                onClick={regenerateImage}
                disabled={isGeneratingImage}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-sm font-medium disabled:opacity-40 transition-colors"
              >
                {isGeneratingImage ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Sparkles className="w-4 h-4" />
                )}
                Oluştur
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ─── Slide Canvas Component ────────────────────────────────── */

function SlideCanvas({
  slide,
  viewMode,
  onUpdate,
  slideNumber,
  totalSlides,
}: {
  slide: Slide;
  viewMode: ViewMode;
  onUpdate: (field: keyof Slide, value: any) => void;
  slideNumber: number;
  totalSlides: number;
}) {
  const isDark = slide.layout === "title" || slide.layout === "closing";

  const bgStyle: React.CSSProperties =
    slide.layout === "title"
      ? { background: "linear-gradient(135deg, #4c1d95, #1e1b4b, #0f172a)" }
      : slide.layout === "closing"
        ? { background: "linear-gradient(135deg, #1e293b, #0f172a, #020617)" }
        : slide.layout === "quote"
          ? { background: "linear-gradient(135deg, #faf5ff, #f3e8ff)" }
          : { background: "#ffffff" };

  const textColor = isDark
    ? "text-white"
    : slide.layout === "quote"
      ? "text-purple-900"
      : "text-gray-800";
  const subColor = isDark
    ? "text-white/70"
    : slide.layout === "quote"
      ? "text-purple-700"
      : "text-gray-600";

  return (
    <div
      className="relative w-full mx-auto rounded-xl overflow-hidden shadow-2xl border border-white/10"
      style={{
        ...bgStyle,
        aspectRatio: "16/9",
        maxHeight: "calc(100vh - 200px)",
      }}
    >
      <div className="absolute inset-0 p-8 flex flex-col">
        {/* Title Layout */}
        {slide.layout === "title" && (
          <div className="flex-1 flex flex-col items-center justify-center text-center">
            {slide.imageUrl && (
              <div className="absolute inset-0 opacity-20">
                <PollinationsImage
                  src={slide.imageUrl}
                  alt=""
                  className="w-full h-full object-cover"
                  placeholderClassName="w-full h-full"
                />
              </div>
            )}
            <div className="relative z-10">
              <h1
                className={`text-3xl md:text-4xl font-bold ${textColor} mb-4`}
              >
                {slide.title}
              </h1>
              {slide.content && (
                <p className={`text-lg ${subColor} max-w-2xl`}>
                  {slide.content}
                </p>
              )}
            </div>
          </div>
        )}

        {/* Content Layout */}
        {slide.layout === "content" && (
          <div className="flex-1 flex flex-col">
            <h2 className={`text-2xl font-bold ${textColor} mb-4`}>
              {slide.title}
            </h2>
            {slide.content && (
              <p className={`text-sm ${subColor} mb-4 leading-relaxed`}>
                {slide.content}
              </p>
            )}
            {slide.bullets.length > 0 && (
              <ul className="space-y-2 flex-1">
                {slide.bullets.map((b, i) => (
                  <li
                    key={i}
                    className={`flex items-start gap-2 text-sm ${subColor}`}
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-purple-500 mt-1.5 shrink-0" />
                    {b}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {/* Two Column Layout */}
        {slide.layout === "two-column" && (
          <div className="flex-1 flex flex-col">
            <h2 className={`text-2xl font-bold ${textColor} mb-4`}>
              {slide.title}
            </h2>
            <div className="flex-1 grid grid-cols-2 gap-6">
              <div>
                {slide.content && (
                  <p className={`text-sm ${subColor} leading-relaxed`}>
                    {slide.content}
                  </p>
                )}
                {slide.bullets.length > 0 && (
                  <ul className="mt-3 space-y-2">
                    {slide.bullets.map((b, i) => (
                      <li
                        key={i}
                        className={`flex items-start gap-2 text-sm ${subColor}`}
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-purple-500 mt-1.5 shrink-0" />
                        {b}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div className="flex items-center justify-center">
                {slide.imageUrl ? (
                  <PollinationsImage
                    src={slide.imageUrl}
                    alt={slide.title}
                    className="w-full h-full object-cover rounded-lg"
                    placeholderClassName="w-full h-full rounded-lg bg-gray-100"
                  />
                ) : (
                  <div className="w-full h-full rounded-lg bg-gray-100 flex items-center justify-center">
                    <ImageIcon className="w-12 h-12 text-gray-300" />
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Image Focus Layout */}
        {slide.layout === "image-focus" && (
          <div className="flex-1 flex flex-col">
            <h2 className={`text-2xl font-bold ${textColor} mb-3`}>
              {slide.title}
            </h2>
            <div className="flex-1 rounded-lg overflow-hidden">
              {slide.imageUrl ? (
                <PollinationsImage
                  src={slide.imageUrl}
                  alt={slide.title}
                  className="w-full h-full object-cover"
                  placeholderClassName="w-full h-full bg-gray-100"
                />
              ) : (
                <div className="w-full h-full bg-gray-100 flex items-center justify-center">
                  <ImageIcon className="w-16 h-16 text-gray-300" />
                </div>
              )}
            </div>
            {slide.content && (
              <p className={`text-xs ${subColor} mt-2 text-center`}>
                {slide.content}
              </p>
            )}
          </div>
        )}

        {/* Quote Layout */}
        {slide.layout === "quote" && (
          <div className="flex-1 flex flex-col items-center justify-center text-center px-12">
            <div className="text-6xl text-purple-300 mb-4">&ldquo;</div>
            <blockquote
              className={`text-xl md:text-2xl font-medium ${textColor} italic leading-relaxed mb-4`}
            >
              {slide.content || slide.title}
            </blockquote>
            {slide.bullets[0] && (
              <cite className={`text-sm ${subColor} not-italic`}>
                — {slide.bullets[0]}
              </cite>
            )}
          </div>
        )}

        {/* Closing Layout */}
        {slide.layout === "closing" && (
          <div className="flex-1 flex flex-col items-center justify-center text-center">
            {slide.imageUrl && (
              <div className="absolute inset-0 opacity-15">
                <PollinationsImage
                  src={slide.imageUrl}
                  alt=""
                  className="w-full h-full object-cover"
                  placeholderClassName="w-full h-full"
                />
              </div>
            )}
            <div className="relative z-10">
              <h1
                className={`text-3xl md:text-4xl font-bold ${textColor} mb-4`}
              >
                {slide.title}
              </h1>
              {slide.content && (
                <p className={`text-lg ${subColor}`}>{slide.content}</p>
              )}
              {slide.bullets.length > 0 && (
                <div className="mt-6 space-y-1">
                  {slide.bullets.map((b, i) => (
                    <p key={i} className={`text-sm ${subColor}`}>
                      {b}
                    </p>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Slide Number */}
        <div
          className={`absolute bottom-3 right-4 text-xs ${isDark ? "text-white/30" : "text-gray-400"}`}
        >
          {slideNumber} / {totalSlides}
        </div>
      </div>
    </div>
  );
}
