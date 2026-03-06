"use client";

import { useEffect } from "react";

const PANELS = [
  {
    icon: "💬",
    title: "Sohbet",
    color: "text-blue-400",
    border: "border-blue-400/30",
    desc: "Ana chat arayüzü. Agent'larla konuşma, görev verme, sonuçları görme. Pipeline seçimi (auto/speed/deep/research) burada yapılır.",
  },
  {
    icon: "📊",
    title: "Görev Akışı",
    color: "text-sky-400",
    border: "border-sky-400/30",
    desc: "Aktif görevin aşama diyagramı, Gantt chart, agent sağlık dashboard'u, performans metrikleri ve canlı log stream.",
  },
  {
    icon: "⚙️",
    title: "Sistem",
    color: "text-emerald-400",
    border: "border-emerald-400/30",
    desc: "Sistem istatistikleri, agent sağlık kartları, anomali tespiti ve liderlik tablosu. Tüm altyapının kuş bakışı görünümü.",
  },
  {
    icon: "🧠",
    title: "Bellek",
    color: "text-purple-400",
    border: "border-purple-400/30",
    desc: "Bellek zaman çizelgesi ve korelasyon kümeleri. Agent'ların ne öğrendiğini, hangi bilgilerin birbiriyle ilişkili olduğunu gösterir.",
  },
  {
    icon: "📈",
    title: "Gelişim",
    color: "text-amber-400",
    border: "border-amber-400/30",
    desc: "Agent performans sıralaması, yetenek önerileri ve otomatik keşif. Her agent'ın zaman içindeki gelişimini takip eder.",
  },
  {
    icon: "🔗",
    title: "Koordinasyon",
    color: "text-pink-400",
    border: "border-pink-400/30",
    desc: "Yetkinlik matrisi (heatmap), görev atama simülasyonu ve rotasyon geçmişi. Agent'lar arası iş bölümünü optimize eder.",
  },
  {
    icon: "🌐",
    title: "Ekosistem",
    color: "text-cyan-400",
    border: "border-cyan-400/30",
    desc: "SVG tabanlı interaktif harita. Agent'lar arası etkileşim ağını, mesaj akışını ve bağımlılıkları görselleştirir.",
  },
  {
    icon: "🤖",
    title: "Özerk Evrim",
    color: "text-rose-400",
    border: "border-rose-400/30",
    desc: "İyileştirme planları ve hata öğrenme sistemi. Agent'lar kendi hatalarından ders çıkarır ve kendini geliştirir.",
  },
];

const AGENTS = [
  {
    icon: "🎭",
    title: "Orkestratör",
    color: "text-pink-400",
    border: "border-pink-400/30",
    tag: "Beyin",
    tagColor: "bg-pink-400/10 text-pink-400 border-pink-400/30",
    desc: "Görev analizi, agent seçimi, iş dağıtımı, sonuç sentezi. Tüm sistemi yönetir.",
  },
  {
    icon: "🧠",
    title: "Thinker",
    color: "text-cyan-300",
    border: "border-cyan-300/30",
    tag: "Analiz",
    tagColor: "bg-cyan-300/10 text-cyan-300 border-cyan-300/30",
    desc: "Derin analiz, karmaşık muhakeme, strateji geliştirme. Zor soruları çözer.",
  },
  {
    icon: "⚡",
    title: "Speed",
    color: "text-purple-400",
    border: "border-purple-400/30",
    tag: "Hız",
    tagColor: "bg-purple-400/10 text-purple-400 border-purple-400/30",
    desc: "Hızlı yanıt, basit görevler, anlık sorular. Düşük gecikme optimizasyonu.",
  },
  {
    icon: "🔬",
    title: "Researcher",
    color: "text-amber-400",
    border: "border-amber-400/30",
    tag: "Araştırma",
    tagColor: "bg-amber-400/10 text-amber-400 border-amber-400/30",
    desc: "Web araştırma, kaynak bulma, bilgi toplama, fact-checking. Dış dünya bağlantısı.",
  },
  {
    icon: "🔍",
    title: "Reasoner",
    color: "text-emerald-400",
    border: "border-emerald-400/30",
    tag: "Mantık",
    tagColor: "bg-emerald-400/10 text-emerald-400 border-emerald-400/30",
    desc: "Mantıksal çıkarım, doğrulama, tutarlılık kontrolü. Sonuçları denetler.",
  },
  {
    icon: "👁️",
    title: "Observer",
    color: "text-cyan-400",
    border: "border-cyan-400/30",
    tag: "Gözlemci",
    tagColor: "bg-cyan-400/10 text-cyan-400 border-cyan-400/30",
    desc: "Sistem izleme, anomali tespiti, kalite güvencesi. DeepSeek Chat modeli.",
  },
];

interface Props {
  open: boolean;
  onClose: () => void;
}

export function SystemGuideDialog({ open, onClose }: Props) {
  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Sistem Rehberi"
    >
      <div
        className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-[94vw] max-w-3xl max-h-[85vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🧠</span>
            <div>
              <h2 className="text-base font-bold text-slate-100">
                Multi-Agent Ops Center
              </h2>
              <p className="text-[11px] text-slate-500">
                Sistem Rehberi — Paneller &amp; Agent&apos;lar
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-500 hover:text-slate-200 transition-colors text-xl leading-none p-2 min-w-[36px] min-h-[36px] flex items-center justify-center rounded-lg hover:bg-white/5"
            aria-label="Kapat"
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 min-h-0 overflow-y-auto px-5 py-4 space-y-6">
          {/* Tags */}
          <div className="flex flex-wrap gap-2">
            <span className="px-3 py-1 rounded-full text-[11px] font-semibold bg-blue-400/10 text-blue-400 border border-blue-400/30">
              8 Panel
            </span>
            <span className="px-3 py-1 rounded-full text-[11px] font-semibold bg-purple-400/10 text-purple-400 border border-purple-400/30">
              5 Agent
            </span>
            <span className="px-3 py-1 rounded-full text-[11px] font-semibold bg-pink-400/10 text-pink-400 border border-pink-400/30">
              Gerçek Zamanlı
            </span>
            <span className="px-3 py-1 rounded-full text-[11px] font-semibold bg-emerald-400/10 text-emerald-400 border border-emerald-400/30">
              PostgreSQL + pgvector
            </span>
          </div>

          {/* Panels section */}
          <div>
            <h3 className="text-sm font-semibold text-slate-300 mb-3">
              📋 Paneller
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {PANELS.map((p) => (
                <div
                  key={p.title}
                  className={`bg-slate-800/50 border ${p.border} rounded-lg p-3`}
                >
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="text-lg">{p.icon}</span>
                    <span className={`text-sm font-bold ${p.color}`}>
                      {p.title}
                    </span>
                  </div>
                  <p className="text-[12px] text-slate-400 leading-relaxed">
                    {p.desc}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Agents section */}
          <div>
            <h3 className="text-sm font-semibold text-slate-300 mb-3">
              🤖 Agent Ekosistemi
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {AGENTS.map((a) => (
                <div
                  key={a.title}
                  className={`bg-slate-800/50 border ${a.border} rounded-lg p-3 text-center`}
                >
                  <div className="text-3xl mb-2">{a.icon}</div>
                  <div className={`text-sm font-bold ${a.color} mb-1`}>
                    {a.title}
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed mb-2">
                    {a.desc}
                  </p>
                  <span
                    className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold border ${a.tagColor}`}
                  >
                    {a.tag}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Data flow */}
          <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-4 text-center">
            <p className="text-[11px] text-slate-500 mb-2">Veri Akışı</p>
            <p className="text-sm tracking-wide">
              <span className="text-blue-400">Kullanıcı</span>
              <span className="text-slate-600"> → </span>
              <span className="text-pink-400">Orkestratör</span>
              <span className="text-slate-600"> → </span>
              <span className="text-purple-400">Agent(lar)</span>
              <span className="text-slate-600"> → </span>
              <span className="text-pink-400">Orkestratör</span>
              <span className="text-slate-600"> → </span>
              <span className="text-emerald-400">Sentez</span>
              <span className="text-slate-600"> → </span>
              <span className="text-blue-400">Kullanıcı</span>
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-slate-800 text-center text-[10px] text-slate-600">
          © 2026 Multi-Agent Ops Center · Erkan Erdem &amp; Yiğit Avcı
        </div>
      </div>
    </div>
  );
}
