"use client";

import { useState, useRef, useCallback } from "react";
import { Paperclip, X, FileText, Image, FileSpreadsheet } from "lucide-react";

const ALLOWED_TYPES = new Set([
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  "image/png",
  "image/jpeg",
  "image/gif",
  "image/webp",
]);
const ALLOWED_EXT = ".pdf,.docx,.xlsx,.pptx,.png,.jpg,.jpeg,.gif,.webp";
const MAX_SIZE = 20 * 1024 * 1024;

export interface AttachedFile {
  file: File;
  preview?: string; // data URL for images
}

interface Props {
  onSend: (message: string, attachments?: AttachedFile[]) => void;
  onStop: () => void;
  isProcessing: boolean;
  onSteering?: (message: string) => void;
}

function fileIcon(type: string) {
  if (type.startsWith("image/")) return <Image className="w-3.5 h-3.5" />;
  if (type.includes("spreadsheet"))
    return <FileSpreadsheet className="w-3.5 h-3.5" />;
  return <FileText className="w-3.5 h-3.5" />;
}

export function ChatInput({ onSend, onStop, isProcessing, onSteering }: Props) {
  const [value, setValue] = useState("");
  const [attachments, setAttachments] = useState<AttachedFile[]>([]);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleSubmit = useCallback(() => {
    const msg = value.trim();
    if (!msg && attachments.length === 0) return;
    // Faz 14.6: If processing and onSteering provided, send as steering message
    if (isProcessing && onSteering && msg) {
      onSteering(msg);
      setValue("");
      inputRef.current?.focus();
      return;
    }
    if (isProcessing) return;
    onSend(msg, attachments.length > 0 ? attachments : undefined);
    setValue("");
    setAttachments([]);
    inputRef.current?.focus();
  }, [value, isProcessing, onSend, onSteering, attachments]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (!files) return;
      const newAttachments: AttachedFile[] = [];
      for (const file of Array.from(files)) {
        if (!ALLOWED_TYPES.has(file.type)) continue;
        if (file.size > MAX_SIZE) continue;
        if (attachments.length + newAttachments.length >= 5) break;
        const af: AttachedFile = { file };
        if (file.type.startsWith("image/")) {
          af.preview = URL.createObjectURL(file);
        }
        newAttachments.push(af);
      }
      setAttachments((prev) => [...prev, ...newAttachments]);
      e.target.value = "";
    },
    [attachments.length],
  );

  const removeAttachment = useCallback((idx: number) => {
    setAttachments((prev) => {
      const removed = prev[idx];
      if (removed?.preview) URL.revokeObjectURL(removed.preview);
      return prev.filter((_, i) => i !== idx);
    });
  }, []);

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

      {/* Attachment previews */}
      {attachments.length > 0 && (
        <div className="flex gap-2 mb-2 flex-wrap">
          {attachments.map((att, idx) => (
            <div
              key={idx}
              className="flex items-center gap-1.5 bg-slate-800/60 border border-slate-700 rounded-lg px-2 py-1.5 text-xs text-slate-300 max-w-[200px]"
            >
              {att.preview ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={att.preview}
                  alt=""
                  className="w-6 h-6 rounded object-cover shrink-0"
                />
              ) : (
                <span className="text-slate-400 shrink-0">
                  {fileIcon(att.file.type)}
                </span>
              )}
              <span className="truncate">{att.file.name}</span>
              <button
                onClick={() => removeAttachment(idx)}
                className="text-slate-500 hover:text-red-400 transition-colors shrink-0 p-0.5"
                aria-label={`${att.file.name} dosyasını kaldır`}
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-2 items-end">
        {/* File attach button */}
        <button
          onClick={() => fileRef.current?.click()}
          disabled={isProcessing || attachments.length >= 5}
          className="p-2.5 rounded-xl border border-border text-slate-400 hover:text-slate-700 hover:border-slate-500 disabled:opacity-30 disabled:cursor-not-allowed transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center shrink-0"
          aria-label="Dosya ekle"
          title="Dosya ekle (PDF, DOCX, XLSX, PPTX, görsel)"
        >
          <Paperclip className="w-4 h-4" />
        </button>
        <input
          ref={fileRef}
          type="file"
          accept={ALLOWED_EXT}
          multiple
          onChange={handleFileSelect}
          className="hidden"
          aria-hidden="true"
        />

        <textarea
          ref={inputRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            isProcessing ? "Talimat gönder (steering)..." : "Görev gönder..."
          }
          rows={1}
          aria-label="Mesaj giriş alanı"
          className="flex-1 resize-none bg-surface border border-border rounded-xl px-3 md:px-4 py-2.5 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors min-h-[44px]"
        />
        <button
          onClick={handleSubmit}
          disabled={!value.trim() && attachments.length === 0}
          aria-label={isProcessing ? "Talimat gönder" : "Mesaj gönder"}
          className={`px-4 py-2.5 rounded-xl text-white text-sm font-medium disabled:opacity-30 disabled:cursor-not-allowed transition-colors shrink-0 min-h-[44px] min-w-[44px] ${
            isProcessing
              ? "bg-amber-600 hover:bg-amber-500"
              : "bg-blue-600 hover:bg-blue-500"
          }`}
        >
          <span className="hidden sm:inline">
            {isProcessing ? "Talimat" : "Gönder"}
          </span>
          <span className="sm:hidden">➤</span>
        </button>
      </div>
    </div>
  );
}
