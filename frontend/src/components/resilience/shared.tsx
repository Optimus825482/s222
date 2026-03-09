/* Resilience panel shared UI primitives — XP theme */
import type { CSSProperties } from "react";
export { REFRESH_MS } from "./types";

export const xpBtn = (active?: boolean): CSSProperties => ({
  padding: "5px 14px",
  fontSize: 11,
  fontFamily: "Tahoma, sans-serif",
  fontWeight: active ? 600 : 400,
  background: active ? "#fff" : "transparent",
  border: active ? "1px solid #d6d2c2" : "1px solid transparent",
  borderBottom: active ? "1px solid #fff" : "1px solid #d6d2c2",
  borderRadius: "3px 3px 0 0",
  marginBottom: -1,
  cursor: "pointer",
  color: active ? "#000" : "#555",
});

export const card: CSSProperties = {
  background: "#fff",
  border: "1px solid #d6d2c2",
  borderRadius: 4,
  padding: 10,
  marginBottom: 8,
  fontSize: 12,
  fontFamily: "Tahoma, sans-serif",
};

export const badge = (color: string): CSSProperties => ({
  display: "inline-block",
  padding: "2px 8px",
  borderRadius: 3,
  fontSize: 10,
  fontWeight: 600,
  color: "#fff",
  background: color,
});

export function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span
      style={{
        display: "inline-block",
        width: 8,
        height: 8,
        borderRadius: "50%",
        background: ok ? "#22c55e" : "#ef4444",
        marginRight: 6,
      }}
    />
  );
}

/* Loading skeleton */
export function Sk({ n = 3 }: { n?: number }) {
  return (
    <div
      style={{
        padding: 20,
        textAlign: "center",
        color: "#888",
        fontSize: 12,
        fontFamily: "Tahoma",
      }}
    >
      Yükleniyor...
    </div>
  );
}

/* Error with retry */
export function Er({ m, r }: { m: string; r: () => void }) {
  return (
    <div style={{ padding: 20, textAlign: "center" }}>
      <div style={{ color: "#ef4444", fontSize: 12, marginBottom: 8 }}>
        ⚠️ {m}
      </div>
      <button
        onClick={r}
        style={{ ...card, cursor: "pointer", padding: "4px 12px" }}
      >
        Tekrar Dene
      </button>
    </div>
  );
}
