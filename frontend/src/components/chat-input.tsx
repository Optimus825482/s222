"use client";

import { useState, useRef, useCallback } from "react";

interface Props {
  onSend: (message: string) => void;
  onStop: () => void;
  isProcessing: boolean;
}

export function ChatInput({ onSend, onStop, isProcessing }: Props) {
  const [value, setValue] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = useCallback(() => {
    const msg = value.trim();
    if (!msg || isProcessing) return;
    onSend(msg);
    setValue("");
    inputRef.current?.focus();
  }, [value, isProcessing, onSend]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="border-t border-border bg-surface-raised px-3 md:px-4 py-3 safe-bottom">
      {isProcessing && (
        <button
          onClick={onStop}
          className="w-full mb-2 py-2.5 rounded-lg bg-red-900/30 text-red-400 text-sm font-medium hover:bg-red-900/50 transition-colors border border-red-900/40 min-h-[44px]"
          aria-label="İşlemi durdur"
        >
          Durdur
        </button>
      )}
      <div className="flex gap-2 items-end">
        <textarea
          ref={inputRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isProcessing}
          placeholder="Görev gönder..."
          rows={1}
          aria-label="Mesaj giriş alanı"
          className="flex-1 resize-none bg-surface border border-border rounded-xl px-3 md:px-4 py-2.5 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 disabled:opacity-50 transition-colors min-h-[44px]"
        />
        <button
          onClick={handleSubmit}
          disabled={isProcessing || !value.trim()}
          aria-label="Mesaj gönder"
          className="px-4 py-2.5 rounded-xl bg-blue-600 text-white text-sm font-medium hover:bg-blue-500 disabled:opacity-30 disabled:cursor-not-allowed transition-colors shrink-0 min-h-[44px] min-w-[44px]"
        >
          <span className="hidden sm:inline">Gönder</span>
          <span className="sm:hidden">➤</span>
        </button>
      </div>
    </div>
  );
}
