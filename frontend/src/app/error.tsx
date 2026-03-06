"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  return (
    <div className="min-h-dvh flex flex-col items-center justify-center p-6 bg-surface text-primary">
      <h1 className="text-lg font-semibold text-red-400 mb-2">Bir hata oluştu</h1>
      <p className="text-sm text-slate-400 mb-4 max-w-md text-center">
        {error.message}
      </p>
      <button
        type="button"
        onClick={reset}
        className="px-4 py-2 rounded-lg bg-[var(--bg-raised)] border border-[var(--border)] text-primary text-sm hover:bg-[var(--bg-overlay)] transition-colors"
      >
        Tekrar dene
      </button>
    </div>
  );
}
