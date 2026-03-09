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

type ThemeKey = "geist" | "apple" | "gradient" | "neon";

const THEME_OPTIONS: { value: ThemeKey; label: string; preview: string }[] = [
  { value: "geist", label: "Geist Dark", preview: "🌑" },
  { value: "apple", label: "Apple Keynote", preview: "🍎" },
  { value: "gradient", label: "Gradient Wave", preview: "🌊" },
  { value: "neon", label: "Neon Cyber", preview: "⚡" },
];

/* ─── Main Component ────────────────────────────────────────── */

export default function PresentationBuilderPanel() {
  // State
  const [slides, setSlides] = useState<Slide[]>([]);
  const [currentSlideIndex, setCurrentSlideIndex] = useState(0);
  const [prompt, setPrompt] = useState("");
  const [slideCount, setSlideCount] = useState(8);
  const [style, setStyle] = useState("professional");
  const [theme, setTheme] = useState<ThemeKey>("geist");
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

    const esc = (t: string) =>
      t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

    const renderSlide = (s: Slide, i: number): string => {
      const num = `<div class="sn">${i + 1} / ${slides.length}</div>`;
      const img = s.imageUrl
        ? `<img src="${s.imageUrl}" alt="${esc(s.title)}" loading="lazy"/>`
        : "";
      const bullets =
        s.bullets.filter(Boolean).length > 0
          ? `<ul>${s.bullets
              .filter(Boolean)
              .map((b) => `<li>${esc(b)}</li>`)
              .join("")}</ul>`
          : "";

      switch (s.layout) {
        case "title":
          return `<section class="slide slide-title">
  ${img ? `<div class="bg-img">${img}</div>` : ""}
  <div class="decor decor-tl"></div><div class="decor decor-br"></div>
  <div class="center-content">
    <h1>${esc(s.title)}</h1>
    ${s.content ? `<p class="subtitle">${esc(s.content)}</p>` : ""}
  </div>${num}</section>`;

        case "two-column":
          return `<section class="slide slide-twocol">
  <div class="decor decor-tl"></div><div class="decor decor-br"></div>
  <h2>${esc(s.title)}</h2>
  <div class="cols">
    <div class="col-text">
      ${s.content ? `<p>${esc(s.content)}</p>` : ""}
      ${bullets}
    </div>
    <div class="col-img">${img || `<div class="img-placeholder"></div>`}</div>
  </div>${num}</section>`;

        case "image-focus":
          return `<section class="slide slide-imgfocus">
  <div class="decor decor-tl"></div><div class="decor decor-br"></div>
  <h2>${esc(s.title)}</h2>
  <div class="hero-img">${img || `<div class="img-placeholder"></div>`}</div>
  ${s.content ? `<p class="caption">${esc(s.content)}</p>` : ""}
${num}</section>`;

        case "quote":
          return `<section class="slide slide-quote">
  <div class="decor decor-tl"></div><div class="decor decor-br"></div>
  <div class="quote-mark">\u201C</div>
  <blockquote>${esc(s.content || s.title)}</blockquote>
  ${s.bullets[0] ? `<cite>\u2014 ${esc(s.bullets[0])}</cite>` : ""}
${num}</section>`;

        case "closing":
          return `<section class="slide slide-closing">
  ${img ? `<div class="bg-img">${img}</div>` : ""}
  <div class="decor decor-tl"></div><div class="decor decor-br"></div>
  <div class="center-content">
    <h1>${esc(s.title)}</h1>
    ${s.content ? `<p class="subtitle">${esc(s.content)}</p>` : ""}
    ${
      s.bullets.filter(Boolean).length > 0
        ? `<div class="closing-points">${s.bullets
            .filter(Boolean)
            .map((b) => `<span>${esc(b)}</span>`)
            .join("")}</div>`
        : ""
    }
  </div>${num}</section>`;

        default: // "content"
          return `<section class="slide slide-content">
  <div class="decor decor-tl"></div><div class="decor decor-br"></div>
  <h2>${esc(s.title)}</h2>
  ${s.content ? `<p class="body-text">${esc(s.content)}</p>` : ""}
  ${bullets}
  ${img ? `<div class="side-img">${img}</div>` : ""}
${num}</section>`;
      }
    };

    const slidesHtml = slides.map(renderSlide).join("\n");

    /* ── Theme CSS generator ── */
    const themeCSS: Record<ThemeKey, string> = {
      geist: `
:root{--c-bg:#000;--c-surface:#111;--c-accent:#fff;--c-accent2:#888;--c-text:#ededed;--c-muted:#666;--font:'Inter',system-ui,sans-serif;--mono:'Geist Mono','SF Mono','Fira Code',monospace}
body{background:#000}
.slide{background:#000;color:#ededed}
.sn{color:#444}

/* Decorative elements */
.decor{position:absolute;pointer-events:none;z-index:0}
.decor-tl{top:0;left:0;width:120px;height:120px;border-left:1px solid #222;border-top:1px solid #222}
.decor-br{bottom:0;right:0;width:120px;height:120px;border-right:1px solid #222;border-bottom:1px solid #222}
.slide::before{content:"";position:absolute;inset:0;background:radial-gradient(ellipse at 20% 50%,rgba(255,255,255,.02) 0%,transparent 70%);pointer-events:none}

/* Title */
.slide-title{background:linear-gradient(180deg,#000 0%,#0a0a0a 100%);align-items:center;justify-content:center;text-align:center}
.slide-title::after{content:"";position:absolute;top:50%;left:50%;width:600px;height:600px;transform:translate(-50%,-50%);border-radius:50%;background:radial-gradient(circle,rgba(255,255,255,.03) 0%,transparent 70%);pointer-events:none}
.slide-title h1{font-size:clamp(2.5em,5.5vw,4.2em);font-weight:800;letter-spacing:-.04em;line-height:1.1;background:linear-gradient(180deg,#fff 30%,#666);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.slide-title .subtitle{font-size:clamp(1em,2vw,1.3em);color:#666;font-weight:300;font-family:var(--mono);margin-top:16px}

/* Content */
.slide-content{background:#000;gap:28px}
.slide-content::after{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:linear-gradient(180deg,#333 0%,transparent 100%)}
.slide-content h2{font-size:clamp(1.6em,3vw,2.4em);font-weight:700;letter-spacing:-.03em;color:#fff}
.slide-content h2::after{content:"";display:block;width:40px;height:2px;background:#444;margin-top:12px}
.slide-content .body-text{font-size:1.05em;color:#888;line-height:1.8;max-width:680px}
.slide-content ul{list-style:none;gap:16px}
.slide-content li{color:#ccc;padding-left:24px;font-size:1em;line-height:1.7;border-left:2px solid #222;padding:8px 0 8px 20px}
.slide-content li::before{display:none}

/* Two Column */
.slide-twocol{background:#000;gap:24px}
.slide-twocol h2{font-size:clamp(1.5em,3vw,2.2em);font-weight:700;color:#fff;letter-spacing:-.02em}
.slide-twocol .col-text p{color:#888;line-height:1.7}
.slide-twocol .col-text li{color:#aaa;border-left:2px solid #222;padding:6px 0 6px 16px}
.slide-twocol .col-text li::before{display:none}
.slide-twocol .col-img{border:1px solid #222;border-radius:12px}

/* Image Focus */
.slide-imgfocus{background:#000;gap:16px}
.slide-imgfocus h2{color:#fff;font-weight:600}
.slide-imgfocus .hero-img{border:1px solid #1a1a1a;border-radius:12px}
.slide-imgfocus .caption{color:#555;font-family:var(--mono);font-size:.85em}

/* Quote */
.slide-quote{background:#000;color:#ededed;align-items:center;justify-content:center;text-align:center}
.slide-quote::before{content:"";position:absolute;inset:40px;border:1px solid #1a1a1a;border-radius:24px;pointer-events:none}
.slide-quote .quote-mark{font-size:5em;color:#333;opacity:1}
.slide-quote blockquote{font-size:clamp(1.3em,3vw,2em);font-weight:400;color:#ccc;font-style:italic;max-width:650px}
.slide-quote cite{color:#555;font-family:var(--mono);font-size:.9em}

/* Closing */
.slide-closing{background:#000;align-items:center;justify-content:center;text-align:center}
.slide-closing::after{content:"";position:absolute;bottom:0;left:0;right:0;height:200px;background:linear-gradient(0deg,rgba(255,255,255,.02),transparent);pointer-events:none}
.slide-closing h1{font-size:clamp(2em,4.5vw,3.5em);font-weight:800;letter-spacing:-.04em;background:linear-gradient(180deg,#fff 30%,#555);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.slide-closing .subtitle{color:#666;font-weight:300}
.slide-closing .closing-points span{background:rgba(255,255,255,.05);border:1px solid #222;color:#aaa;font-family:var(--mono);font-size:.85em}
`,

      apple: `
:root{--c-bg:#000;--c-surface:#1d1d1f;--c-accent:#0071e3;--c-accent2:#2997ff;--c-text:#f5f5f7;--c-muted:#86868b;--font:'SF Pro Display','Inter',system-ui,sans-serif}
body{background:#000}
.slide{background:#000;color:#f5f5f7}
.sn{color:#48484a}

.decor{display:none}
.slide::before{display:none}

/* Title */
.slide-title{background:#000;align-items:center;justify-content:center;text-align:center}
.slide-title h1{font-size:clamp(3em,7vw,5.5em);font-weight:700;letter-spacing:-.04em;line-height:1.05;color:#f5f5f7}
.slide-title .subtitle{font-size:clamp(1.1em,2.2vw,1.6em);color:#86868b;font-weight:400;margin-top:20px}

/* Content — Apple uses massive white space */
.slide-content{background:#fff;color:#1d1d1f;gap:32px;padding:clamp(60px,8vw,120px)}
.slide-content h2{font-size:clamp(2em,4vw,3em);font-weight:700;letter-spacing:-.03em;color:#1d1d1f;border:none;padding-left:0}
.slide-content .body-text{font-size:1.15em;color:#6e6e73;line-height:1.8;max-width:640px}
.slide-content ul{gap:20px}
.slide-content li{font-size:1.1em;color:#1d1d1f;padding-left:0;line-height:1.6}
.slide-content li::before{width:6px;height:6px;background:#0071e3;top:12px}

/* Two Column */
.slide-twocol{background:#fff;color:#1d1d1f;gap:32px;padding:clamp(60px,8vw,120px)}
.slide-twocol h2{font-size:clamp(1.8em,3.5vw,2.8em);font-weight:700;color:#1d1d1f}
.slide-twocol .col-text p{color:#6e6e73;font-size:1.05em;line-height:1.7}
.slide-twocol .col-text li{color:#1d1d1f}
.slide-twocol .col-text li::before{background:#0071e3;border-radius:50%}
.slide-twocol .col-img{border-radius:20px;overflow:hidden}

/* Image Focus */
.slide-imgfocus{background:#000;gap:20px}
.slide-imgfocus h2{color:#f5f5f7;font-size:clamp(1.6em,3vw,2.4em);font-weight:600}
.slide-imgfocus .hero-img{border-radius:20px}
.slide-imgfocus .caption{color:#86868b}

/* Quote — dark with blue accent */
.slide-quote{background:#000;color:#f5f5f7;align-items:center;justify-content:center;text-align:center}
.slide-quote .quote-mark{font-size:6em;color:#0071e3;opacity:.4}
.slide-quote blockquote{font-size:clamp(1.5em,3.5vw,2.4em);font-weight:600;color:#f5f5f7;font-style:normal;max-width:700px;line-height:1.4}
.slide-quote cite{color:#0071e3;font-weight:500;font-size:1em}

/* Closing */
.slide-closing{background:#000;align-items:center;justify-content:center;text-align:center}
.slide-closing h1{font-size:clamp(2.5em,5.5vw,4.5em);font-weight:700;letter-spacing:-.04em;color:#f5f5f7}
.slide-closing .subtitle{color:#86868b;font-size:clamp(1em,2vw,1.4em)}
.slide-closing .closing-points span{background:rgba(0,113,227,.1);border:1px solid rgba(0,113,227,.3);color:#2997ff}
`,

      gradient: `
:root{--c-bg:#0f0720;--c-surface:#1a0d35;--c-accent:#f472b6;--c-accent2:#818cf8;--c-text:#faf5ff;--c-muted:#a78bfa;--font:'Inter',system-ui,sans-serif}
body{background:#0f0720}
.slide{color:#faf5ff}
.sn{color:rgba(255,255,255,.3)}

.decor{position:absolute;pointer-events:none;z-index:0;border-radius:50%;filter:blur(80px);opacity:.15}
.decor-tl{top:-100px;left:-100px;width:400px;height:400px;background:var(--c-accent)}
.decor-br{bottom:-100px;right:-100px;width:350px;height:350px;background:var(--c-accent2)}

/* Title */
.slide-title{background:linear-gradient(135deg,#1e0533 0%,#0f0720 40%,#0c1445 100%);align-items:center;justify-content:center;text-align:center}
.slide-title::before{content:"";position:absolute;top:50%;left:50%;width:800px;height:800px;transform:translate(-50%,-50%);border-radius:50%;background:radial-gradient(circle,rgba(244,114,182,.08) 0%,rgba(129,140,248,.05) 40%,transparent 70%);pointer-events:none}
.slide-title h1{font-size:clamp(2.5em,5.5vw,4em);font-weight:800;letter-spacing:-.03em;line-height:1.1;background:linear-gradient(135deg,#f472b6,#818cf8,#34d399);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.slide-title .subtitle{font-size:clamp(1em,2vw,1.3em);color:#c4b5fd;font-weight:300;margin-top:16px}

/* Content — gradient dark bg, NOT white */
.slide-content{background:linear-gradient(180deg,#130a28 0%,#0f0720 100%);gap:24px}
.slide-content::before{content:"";position:absolute;top:0;right:0;width:50%;height:100%;background:radial-gradient(ellipse at 80% 20%,rgba(244,114,182,.04) 0%,transparent 60%);pointer-events:none}
.slide-content h2{font-size:clamp(1.6em,3vw,2.4em);font-weight:700;letter-spacing:-.02em;color:#fff;border-left:3px solid;border-image:linear-gradient(180deg,#f472b6,#818cf8) 1;padding-left:16px}
.slide-content .body-text{font-size:1.05em;color:#c4b5fd;line-height:1.8;max-width:680px}
.slide-content ul{gap:14px}
.slide-content li{color:#e9d5ff;padding-left:28px;font-size:1em;line-height:1.7}
.slide-content li::before{width:8px;height:8px;border-radius:50%;background:linear-gradient(135deg,#f472b6,#818cf8);top:11px}

/* Two Column */
.slide-twocol{background:linear-gradient(135deg,#130a28 0%,#0c1445 100%);gap:24px}
.slide-twocol h2{font-size:clamp(1.5em,3vw,2.2em);font-weight:700;color:#fff}
.slide-twocol .col-text p{color:#c4b5fd;line-height:1.7}
.slide-twocol .col-text li{color:#e9d5ff}
.slide-twocol .col-text li::before{background:linear-gradient(135deg,#f472b6,#818cf8);border-radius:2px}
.slide-twocol .col-img{border-radius:16px;border:1px solid rgba(244,114,182,.2)}

/* Image Focus */
.slide-imgfocus{background:linear-gradient(180deg,#0f0720 0%,#0c1445 100%);gap:16px}
.slide-imgfocus h2{color:#fff;font-weight:600}
.slide-imgfocus .hero-img{border-radius:16px;border:1px solid rgba(129,140,248,.2)}
.slide-imgfocus .caption{color:#a78bfa}

/* Quote */
.slide-quote{background:linear-gradient(135deg,#1e0533,#0c1445);color:#faf5ff;align-items:center;justify-content:center;text-align:center}
.slide-quote::before{content:"";position:absolute;inset:0;background:radial-gradient(ellipse at 50% 50%,rgba(244,114,182,.06) 0%,transparent 60%);pointer-events:none}
.slide-quote .quote-mark{font-size:6em;background:linear-gradient(135deg,#f472b6,#818cf8);-webkit-background-clip:text;-webkit-text-fill-color:transparent;opacity:.6}
.slide-quote blockquote{font-size:clamp(1.3em,3vw,2em);font-weight:500;color:#e9d5ff;font-style:italic;max-width:650px}
.slide-quote cite{color:#f472b6;font-weight:600}

/* Closing */
.slide-closing{background:linear-gradient(135deg,#1e0533 0%,#0f0720 50%,#0c1445 100%);align-items:center;justify-content:center;text-align:center}
.slide-closing h1{font-size:clamp(2em,4.5vw,3.5em);font-weight:800;background:linear-gradient(135deg,#f472b6,#818cf8,#34d399);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.slide-closing .subtitle{color:#c4b5fd;font-weight:300}
.slide-closing .closing-points span{background:rgba(244,114,182,.1);border:1px solid rgba(244,114,182,.3);color:#f9a8d4}
`,

      neon: `
:root{--c-bg:#0a0a0f;--c-surface:#12121a;--c-accent:#00ff88;--c-accent2:#00d4ff;--c-text:#e0ffe0;--c-muted:#4a9;--font:'Inter',system-ui,sans-serif;--mono:'Fira Code','SF Mono',monospace}
body{background:#0a0a0f}
.slide{color:#e0ffe0}
.sn{color:#1a3a2a;font-family:var(--mono)}

.decor{position:absolute;pointer-events:none;z-index:0}
.decor-tl{top:0;left:0;width:1px;height:80px;background:linear-gradient(180deg,var(--c-accent),transparent);box-shadow:0 0 15px var(--c-accent)}
.decor-br{bottom:0;right:0;width:80px;height:1px;background:linear-gradient(90deg,transparent,var(--c-accent2));box-shadow:0 0 15px var(--c-accent2)}
.slide::before{content:"";position:absolute;inset:0;background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,255,136,.01) 2px,rgba(0,255,136,.01) 4px);pointer-events:none}

/* Title */
.slide-title{background:#0a0a0f;align-items:center;justify-content:center;text-align:center}
.slide-title::after{content:"";position:absolute;top:50%;left:50%;width:500px;height:500px;transform:translate(-50%,-50%);border-radius:50%;background:radial-gradient(circle,rgba(0,255,136,.06) 0%,rgba(0,212,255,.03) 40%,transparent 70%);pointer-events:none}
.slide-title h1{font-size:clamp(2.5em,5.5vw,4em);font-weight:800;letter-spacing:-.03em;line-height:1.1;color:#fff;text-shadow:0 0 40px rgba(0,255,136,.3),0 0 80px rgba(0,255,136,.1)}
.slide-title .subtitle{font-size:clamp(1em,2vw,1.3em);color:#00ff88;font-weight:300;font-family:var(--mono);text-shadow:0 0 20px rgba(0,255,136,.3)}

/* Content */
.slide-content{background:#0a0a0f;gap:24px}
.slide-content::after{content:"";position:absolute;left:0;top:0;width:2px;height:100%;background:linear-gradient(180deg,#00ff88,#00d4ff,transparent);box-shadow:0 0 10px rgba(0,255,136,.3)}
.slide-content h2{font-size:clamp(1.6em,3vw,2.4em);font-weight:700;color:#fff;letter-spacing:-.02em;border:none;padding-left:0}
.slide-content h2::after{content:"_";color:#00ff88;animation:blink 1.2s step-end infinite}
@keyframes blink{50%{opacity:0}}
.slide-content .body-text{font-size:1em;color:#8aaa8a;line-height:1.8;max-width:680px;font-family:var(--mono)}
.slide-content ul{gap:12px}
.slide-content li{color:#b0e0b0;padding-left:28px;font-size:.95em;line-height:1.7;font-family:var(--mono)}
.slide-content li::before{width:8px;height:8px;border-radius:0;background:#00ff88;box-shadow:0 0 8px #00ff88;top:10px}

/* Two Column */
.slide-twocol{background:#0a0a0f;gap:24px}
.slide-twocol h2{font-size:clamp(1.5em,3vw,2.2em);font-weight:700;color:#fff}
.slide-twocol .col-text p{color:#8aaa8a;font-family:var(--mono);line-height:1.7}
.slide-twocol .col-text li{color:#b0e0b0;font-family:var(--mono)}
.slide-twocol .col-text li::before{background:#00d4ff;box-shadow:0 0 6px #00d4ff;border-radius:0}
.slide-twocol .col-img{border-radius:8px;border:1px solid #00ff8833;box-shadow:0 0 20px rgba(0,255,136,.05)}

/* Image Focus */
.slide-imgfocus{background:#0a0a0f;gap:16px}
.slide-imgfocus h2{color:#fff;font-weight:600}
.slide-imgfocus .hero-img{border-radius:8px;border:1px solid #00d4ff33;box-shadow:0 0 30px rgba(0,212,255,.08)}
.slide-imgfocus .caption{color:#4a9;font-family:var(--mono);font-size:.85em}

/* Quote */
.slide-quote{background:#0a0a0f;color:#e0ffe0;align-items:center;justify-content:center;text-align:center}
.slide-quote::after{content:"";position:absolute;inset:30px;border:1px solid #00ff8822;border-radius:16px;box-shadow:inset 0 0 40px rgba(0,255,136,.02);pointer-events:none}
.slide-quote .quote-mark{font-size:5em;color:#00ff88;opacity:.4;text-shadow:0 0 30px rgba(0,255,136,.3)}
.slide-quote blockquote{font-size:clamp(1.3em,3vw,2em);font-weight:400;color:#c0ffc0;font-style:italic;max-width:650px}
.slide-quote cite{color:#00d4ff;font-family:var(--mono);font-size:.9em;text-shadow:0 0 10px rgba(0,212,255,.3)}

/* Closing */
.slide-closing{background:#0a0a0f;align-items:center;justify-content:center;text-align:center}
.slide-closing::after{content:"";position:absolute;bottom:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,#00ff88,#00d4ff,transparent);box-shadow:0 0 20px rgba(0,255,136,.3)}
.slide-closing h1{font-size:clamp(2em,4.5vw,3.5em);font-weight:800;color:#fff;text-shadow:0 0 40px rgba(0,255,136,.3)}
.slide-closing .subtitle{color:#4a9;font-family:var(--mono)}
.slide-closing .closing-points span{background:rgba(0,255,136,.08);border:1px solid rgba(0,255,136,.25);color:#00ff88;font-family:var(--mono);font-size:.85em;box-shadow:0 0 10px rgba(0,255,136,.1)}
`,
    };

    const selectedCSS = themeCSS[theme] || themeCSS.geist;

    const html = `<!DOCTYPE html>
<html lang="tr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(slides[0]?.title || "Sunum")}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
.slide{position:relative;width:100%;min-height:100vh;padding:clamp(40px,6vw,80px);display:flex;flex-direction:column;font-family:var(--font,Inter,system-ui,sans-serif);page-break-after:always;overflow:hidden}
.sn{position:absolute;bottom:24px;right:32px;font-size:13px;font-weight:500;opacity:.5}

/* Shared structural defaults */
.slide-title .bg-img,.slide-closing .bg-img{position:absolute;inset:0;opacity:.15}
.slide-title .bg-img img,.slide-closing .bg-img img{width:100%;height:100%;object-fit:cover}
.slide-title .center-content,.slide-closing .center-content{position:relative;z-index:1}
.slide-twocol .cols{display:grid;grid-template-columns:1fr 1fr;gap:40px;flex:1;align-items:center}
.slide-twocol .col-img{border-radius:16px;overflow:hidden;aspect-ratio:4/3}
.slide-twocol .col-img img,.slide-imgfocus .hero-img img,.slide-content .side-img img{width:100%;height:100%;object-fit:cover;display:block}
.slide-imgfocus .hero-img{flex:1;border-radius:16px;overflow:hidden;min-height:0}
.slide-content .side-img{margin-top:auto;border-radius:12px;overflow:hidden;max-height:35vh}
.slide-content ul{list-style:none;display:flex;flex-direction:column;gap:12px;flex:1}
.slide-twocol .col-text ul{list-style:none;display:flex;flex-direction:column;gap:10px}
.slide-closing .closing-points{margin-top:32px;display:flex;flex-wrap:wrap;gap:12px;justify-content:center}
.img-placeholder{width:100%;height:100%;background:linear-gradient(135deg,#e2e8f0,#cbd5e1);border-radius:12px;display:flex;align-items:center;justify-content:center}
.decor{position:absolute;pointer-events:none;opacity:.15}
.decor-tl{top:20px;left:20px;width:80px;height:80px;border-top:2px solid currentColor;border-left:2px solid currentColor}
.decor-br{bottom:20px;right:20px;width:80px;height:80px;border-bottom:2px solid currentColor;border-right:2px solid currentColor}

/* Theme overrides */
${selectedCSS}

@media print{.slide{page-break-after:always;min-height:100vh}}
</style>
</head><body>
${slidesHtml}
</body></html>`;

    const blob = new Blob([html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "presentation.html";
    a.click();
    URL.revokeObjectURL(url);
  }, [slides, theme]);

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

              <div>
                <label className="text-xs text-white/40 mb-2 block">Tema</label>
                <div className="grid grid-cols-2 gap-2">
                  {THEME_OPTIONS.map((t) => (
                    <button
                      key={t.value}
                      onClick={() => setTheme(t.value)}
                      disabled={isGenerating}
                      className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm transition-colors ${
                        theme === t.value
                          ? "bg-purple-500/20 border-purple-500/50 text-white/90"
                          : "bg-white/5 border-white/10 text-white/50 hover:bg-white/10"
                      }`}
                    >
                      <span>{t.preview}</span>
                      <span>{t.label}</span>
                    </button>
                  ))}
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
