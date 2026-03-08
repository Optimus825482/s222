"use client";
import { TIME_FILTERS } from "./shared";

export function TimeFilterBar({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex items-center gap-1">
      {TIME_FILTERS.map((f) => (
        <button
          key={f.value}
          onClick={() => onChange(f.value)}
          className={`px-2 py-0.5 rounded text-[10px] transition-colors ${
            value === f.value
              ? "bg-cyan-600 text-white"
              : "bg-slate-700/50 text-slate-400 hover:text-slate-200"
          }`}
        >
          {f.label}
        </button>
      ))}
    </div>
  );
}
