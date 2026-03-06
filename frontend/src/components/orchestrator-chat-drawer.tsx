"use client";

import { useRef, useEffect } from "react";
import { X, Send, MessageCircle } from "lucide-react";

export interface OrchestratorChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
  messages: OrchestratorChatMessage[];
  onSend: (message: string) => void;
  threadId?: string | null;
  isProcessing?: boolean;
}

export function OrchestratorChatDrawer({
  isOpen,
  onClose,
  messages,
  onSend,
  isProcessing,
}: Props) {
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen) inputRef.current?.focus();
  }, [isOpen]);

  useEffect(() => {
    listRef.current?.scrollTo(0, listRef.current.scrollHeight);
  }, [messages.length]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const raw = inputRef.current?.value?.trim();
    if (!raw) return;
    onSend(raw);
    inputRef.current!.value = "";
  };

  if (!isOpen) return null;

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm lg:bg-transparent"
        onClick={onClose}
        onKeyDown={(e) => e.key === "Escape" && onClose()}
        role="presentation"
        aria-hidden
      />
      <div
        className="fixed top-0 right-0 bottom-0 z-50 w-full max-w-md flex flex-col bg-[#1a1f2e] border-l border-border shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-label="Orkestratörle sohbet"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
          <div className="flex items-center gap-2">
            <MessageCircle className="w-4 h-4 text-blue-400" aria-hidden />
            <span className="text-sm font-semibold text-slate-200">
              Orkestratörle sohbet
            </span>
            {isProcessing && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-950/50 text-blue-400 border border-blue-800/50">
                Görev çalışıyor
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Kapat"
            className="min-w-[36px] min-h-[36px] flex items-center justify-center text-slate-500 hover:text-slate-300 rounded hover:bg-white/5 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <p className="px-4 py-2 text-[11px] text-slate-500 border-b border-border/50 shrink-0">
          Görev devam ederken durum sorabilir veya ek talimat yazabilirsiniz.
        </p>

        {/* Messages */}
        <div
          ref={listRef}
          className="flex-1 min-h-0 overflow-y-auto px-4 py-3 space-y-3"
        >
          {messages.length === 0 && (
            <div className="text-center text-xs text-slate-500 py-6">
              Mesaj yazıp gönderin — örn. &quot;Durum?&quot; veya &quot;Şu ana kadar ne yaptınız?&quot;
            </div>
          )}
          {messages.map((m, i) => (
            <div
              key={i}
              className={`rounded-lg px-3 py-2 text-[12px] ${
                m.role === "user"
                  ? "ml-6 bg-blue-950/40 border border-blue-800/40 text-slate-200"
                  : "mr-6 bg-surface border border-border text-slate-300"
              }`}
            >
              <span className="text-[10px] font-medium text-slate-500 block mb-0.5">
                {m.role === "user" ? "Siz" : "Orkestratör"}
              </span>
              <div className="whitespace-pre-wrap break-words">{m.content}</div>
            </div>
          ))}
        </div>

        {/* Input */}
        <form
          onSubmit={handleSubmit}
          className="p-4 border-t border-border shrink-0"
        >
          <div className="flex gap-2">
            <textarea
              ref={inputRef}
              rows={2}
              placeholder="Durum sor veya ek talimat yaz..."
              className="flex-1 min-h-[44px] max-h-32 px-3 py-2 rounded-lg bg-surface border border-border text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-600/50 resize-none"
              aria-label="Orkestratör mesajı"
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
            />
            <button
              type="submit"
              aria-label="Gönder"
              className="shrink-0 min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg bg-blue-600 hover:bg-blue-500 text-white transition-colors"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
