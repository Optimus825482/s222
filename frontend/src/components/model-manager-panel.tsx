"use client";
import { useState, useEffect, useCallback, useRef } from "react";
import { fetcher } from "@/lib/api";
import { AGENT_CONFIG } from "@/lib/agents";
import type { AgentRole } from "@/lib/types";

/* ── Types ─────────────────────────────────────────────────────── */

interface ProviderInfo {
  name: string;
  status: "connected" | "disconnected";
  model_count: number;
  models?: string[];
}

interface ModelMapping {
  role: AgentRole;
  current_model: string;
  provider: string;
  alternatives: string[];
}

interface GatewayHealth {
  url: string;
  status: "healthy" | "degraded" | "down";
  uptime: string;
  total_requests: number;
  avg_latency_ms: number;
}

/* ── Constants ─────────────────────────────────────────────────── */

type MgrTab = "providers" | "mapping" | "gateway" | "validation";

const TABS: { key: MgrTab; label: string; icon: string }[] = [
  { key: "providers", label: "Sağlayıcılar", icon: "🔌" },
  { key: "mapping", label: "Model Eşleme", icon: "🔀" },
  { key: "gateway", label: "Gateway Durumu", icon: "📡" },
  { key: "validation", label: "Tool Doğrulama", icon: "🛡️" },
];

const PROVIDER_ICONS: Record<string, string> = {
  openai: "🟢",
  anthropic: "🟤",
  google: "🔵",
  groq: "⚡",
  mistral: "🌀",
  xai: "✖️",
  nvidia: "💚",
  deepseek: "🐋",
};

const ROLES: AgentRole[] = [
  "orchestrator",
  "thinker",
  "speed",
  "researcher",
  "reasoner",
  "critic",
];

const crd = "bg-slate-800/50 border border-slate-700/50 rounded-lg p-4";
const sCls =
  "bg-slate-800/60 border border-slate-700/50 rounded px-2 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-cyan-500/50";

const tabSt = (on: boolean): React.CSSProperties => ({
  padding: "6px 14px",
  fontSize: 11,
  fontFamily: "Tahoma, sans-serif",
  cursor: "pointer",
  border: "none",
  borderBottom: on ? "2px solid #22d3ee" : "2px solid transparent",
  color: on ? "#22d3ee" : "#94a3b8",
  background: "transparent",
  transition: "color .15s, border-color .15s",
});

/* ── Shared UI ─────────────────────────────────────────────────── */

function Sk({ n = 4 }: { n?: number }) {
  return (
    <div
      className="space-y-3 animate-pulse"
      role="status"
      aria-label="Yükleniyor"
    >
      {Array.from({ length: n }, (_, i) => (
        <div key={i} className="h-8 bg-slate-700/40 rounded" />
      ))}
    </div>
  );
}

function Er({ m, r }: { m: string; r: () => void }) {
  return (
    <div className="flex flex-col items-center gap-2 py-8">
      <span className="text-xs text-red-400">⚠️ {m}</span>
      <button
        onClick={r}
        className="px-3 py-1 text-xs bg-slate-700 hover:bg-slate-600 text-slate-300 rounded transition-colors"
      >
        Tekrar Dene
      </button>
    </div>
  );
}

function Mt({ icon, text }: { icon: string; text: string }) {
  return (
    <div className="text-center py-8">
      <div className="text-3xl mb-2">{icon}</div>
      <p className="text-xs text-slate-500">{text}</p>
    </div>
  );
}

/* ── Tab 1: Providers ──────────────────────────────────────────── */

function ProvidersTab() {
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [ld, setLd] = useState(true);
  const [err, setErr] = useState("");

  const load = useCallback(async () => {
    try {
      setErr("");
      setLd(true);
      const data = await fetcher<
        ProviderInfo[] | { providers: ProviderInfo[] }
      >("/api/gateway/providers");
      const list = Array.isArray(data)
        ? data
        : Array.isArray(data?.providers)
          ? data.providers
          : [];
      setProviders(list);
    } catch (x) {
      setErr(x instanceof Error ? x.message : "Sağlayıcılar yüklenemedi");
    } finally {
      setLd(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (ld) return <Sk n={4} />;
  if (err) return <Er m={err} r={load} />;
  if (providers.length === 0)
    return <Mt icon="🔌" text="Yapılandırılmış sağlayıcı yok" />;

  const connected = providers.filter((p) => p.status === "connected").length;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between px-1">
        <span className="text-[10px] text-slate-500 uppercase tracking-wider">
          {connected}/{providers.length} bağlı
        </span>
        <button
          onClick={load}
          className="text-[10px] text-cyan-400 hover:text-cyan-300 transition-colors"
          aria-label="Yenile"
        >
          ↻ Yenile
        </button>
      </div>

      <div className="grid grid-cols-2 gap-2">
        {providers.map((p) => {
          const icon = PROVIDER_ICONS[p.name.toLowerCase()] ?? "⚙️";
          const ok = p.status === "connected";
          return (
            <div
              key={p.name}
              className={`${crd} flex flex-col gap-2 hover:border-slate-600/60 transition-colors`}
            >
              <div className="flex items-center gap-2">
                <span className="text-lg">{icon}</span>
                <span className="text-xs font-medium text-slate-200 flex-1 truncate">
                  {p.name}
                </span>
                <span
                  className={`w-2 h-2 rounded-full flex-shrink-0 ${ok ? "bg-emerald-400" : "bg-red-400"}`}
                  title={ok ? "Bağlı" : "Bağlantı Yok"}
                />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-slate-500">
                  {p.model_count} model
                </span>
                <span
                  className={`text-[9px] px-1.5 py-0.5 rounded border ${
                    ok
                      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                      : "bg-red-500/10 text-red-400 border-red-500/20"
                  }`}
                >
                  {ok ? "Bağlı" : "Bağlantı Yok"}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ── Tab 2: Model Mapping ──────────────────────────────────────── */

function MappingTab() {
  const [mappings, setMappings] = useState<ModelMapping[]>([]);
  const [draft, setDraft] = useState<Record<AgentRole, string>>(
    {} as Record<AgentRole, string>,
  );
  const [ld, setLd] = useState(true);
  const [err, setErr] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const load = useCallback(async () => {
    try {
      setErr("");
      setLd(true);
      const raw = await fetcher<Record<string, any> | ModelMapping[]>(
        "/api/gateway/model-mapping",
      );
      const data = Array.isArray(raw)
        ? raw
        : Object.entries(raw).map(
            ([role, v]) => ({ role, ...v }) as ModelMapping,
          );
      setMappings(data);
      const initial: Record<string, string> = {};
      data.forEach((m) => {
        initial[m.role] = m.current_model;
      });
      setDraft(initial as Record<AgentRole, string>);
    } catch (x) {
      setErr(x instanceof Error ? x.message : "Eşleme verisi yüklenemedi");
    } finally {
      setLd(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const hasChanges = mappings.some((m) => draft[m.role] !== m.current_model);

  const apply = useCallback(async () => {
    try {
      setSaving(true);
      setSaved(false);
      await fetcher<unknown>("/api/gateway/model-mapping", {
        method: "POST",
        body: JSON.stringify({ mappings: draft }),
      });
      setSaved(true);
      await load();
      setTimeout(() => setSaved(false), 2000);
    } catch (x) {
      setErr(x instanceof Error ? x.message : "Kaydetme başarısız");
    } finally {
      setSaving(false);
    }
  }, [draft, load]);

  const reset = useCallback(() => {
    const original: Record<string, string> = {};
    mappings.forEach((m) => {
      original[m.role] = m.current_model;
    });
    setDraft(original as Record<AgentRole, string>);
  }, [mappings]);

  if (ld) return <Sk n={6} />;
  if (err) return <Er m={err} r={load} />;
  if (mappings.length === 0)
    return <Mt icon="🔀" text="Model eşleme verisi bulunamadı" />;

  return (
    <div className="space-y-3">
      <div className="space-y-1.5 max-h-[360px] overflow-y-auto pr-1">
        {ROLES.map((role) => {
          const m = mappings.find((x) => x.role === role);
          if (!m) return null;
          const cfg = AGENT_CONFIG[role];
          const changed = draft[role] !== m.current_model;
          return (
            <div
              key={role}
              className={`${crd} flex items-center gap-3 py-3 ${changed ? "border-cyan-500/30" : ""}`}
            >
              <span className="text-lg flex-shrink-0" title={cfg.name}>
                {cfg.icon}
              </span>
              <div className="flex-1 min-w-0">
                <div className="text-[11px] font-medium text-slate-200 capitalize">
                  {role}
                </div>
                <div className="text-[9px] text-slate-500 truncate">
                  {m.provider}
                </div>
              </div>
              <select
                value={draft[role] ?? m.current_model}
                onChange={(e) =>
                  setDraft((prev) => ({ ...prev, [role]: e.target.value }))
                }
                className={`${sCls} max-w-[180px] truncate`}
                aria-label={`${role} model seçimi`}
              >
                <option value={m.current_model}>{m.current_model}</option>
                {m.alternatives
                  .filter((a) => a !== m.current_model)
                  .map((alt) => (
                    <option key={alt} value={alt}>
                      {alt}
                    </option>
                  ))}
              </select>
              {changed && (
                <span
                  className="w-1.5 h-1.5 rounded-full bg-cyan-400 flex-shrink-0"
                  title="Değiştirildi"
                />
              )}
            </div>
          );
        })}
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={apply}
          disabled={saving || !hasChanges}
          className="flex-1 px-3 py-2 text-xs font-medium rounded border transition-colors disabled:opacity-40 bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-400 border-cyan-500/20"
          style={{ fontFamily: "Tahoma, sans-serif" }}
        >
          {saving ? "Kaydediliyor…" : saved ? "✓ Kaydedildi" : "Uygula"}
        </button>
        <button
          onClick={reset}
          disabled={saving || !hasChanges}
          className="px-3 py-2 text-xs rounded border transition-colors disabled:opacity-40 bg-slate-700/30 hover:bg-slate-700/50 text-slate-400 border-slate-600/30"
          style={{ fontFamily: "Tahoma, sans-serif" }}
        >
          Varsayılana Dön
        </button>
      </div>
    </div>
  );
}

/* ── Tab 3: Gateway Status ─────────────────────────────────────── */

function GatewayTab() {
  const [health, setHealth] = useState<GatewayHealth | null>(null);
  const [fallbackCfg, setFallbackCfg] = useState<{
    enabled: boolean;
    max_retries: number;
    chains: Record<
      string,
      { primary: string; fallbacks: string[]; total_providers: number }
    >;
  } | null>(null);
  const [ld, setLd] = useState(true);
  const [err, setErr] = useState("");
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    try {
      setErr("");
      if (!health) setLd(true);
      const [hData, fbData] = await Promise.all([
        fetcher<GatewayHealth>("/api/gateway/health"),
        fetcher<any>("/api/gateway/fallback-config").catch(() => null),
      ]);
      setHealth(hData);
      if (fbData) setFallbackCfg(fbData);
    } catch (x) {
      setErr(x instanceof Error ? x.message : "Gateway durumu alınamadı");
    } finally {
      setLd(false);
    }
  }, [health]);

  useEffect(() => {
    load();
    intervalRef.current = setInterval(load, 10_000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (ld) return <Sk n={5} />;
  if (err) return <Er m={err} r={load} />;
  if (!health) return null;

  const ok = health.status === "healthy";
  const degraded = health.status === "degraded";

  const statusColor = ok
    ? "text-emerald-400"
    : degraded
      ? "text-amber-400"
      : "text-red-400";
  const statusBg = ok
    ? "bg-emerald-500/10 border-emerald-500/20"
    : degraded
      ? "bg-amber-500/10 border-amber-500/20"
      : "bg-red-500/10 border-red-500/20";
  const statusLabel = ok ? "Sağlıklı" : degraded ? "Kısmi Sorun" : "Çevrimdışı";
  const statusDot = ok
    ? "bg-emerald-400"
    : degraded
      ? "bg-amber-400"
      : "bg-red-400";

  const rows: { label: string; value: string; accent?: string }[] = [
    { label: "Gateway URL", value: health.url },
    { label: "Çalışma Süresi", value: health.uptime, accent: "text-slate-200" },
    {
      label: "Toplam İstek",
      value: health.total_requests.toLocaleString("tr-TR"),
      accent: "text-cyan-400",
    },
    {
      label: "Ort. Gecikme",
      value: `${health.avg_latency_ms.toFixed(1)} ms`,
      accent:
        health.avg_latency_ms > 500 ? "text-amber-400" : "text-emerald-400",
    },
  ];

  return (
    <div className="space-y-3">
      {/* Status banner */}
      <div className={`${crd} flex items-center gap-3 ${statusBg}`}>
        <span className={`w-3 h-3 rounded-full ${statusDot} animate-pulse`} />
        <div className="flex-1">
          <div className={`text-sm font-medium ${statusColor}`}>
            {statusLabel}
          </div>
          <div className="text-[10px] text-slate-500">
            Her 10 saniyede otomatik yenilenir
          </div>
        </div>
        <button
          onClick={load}
          className="text-[10px] text-cyan-400 hover:text-cyan-300 transition-colors"
          aria-label="Şimdi yenile"
        >
          ↻
        </button>
      </div>

      {/* Stats */}
      <div className={crd + " space-y-2"}>
        {rows.map((r) => (
          <div key={r.label} className="flex items-center justify-between">
            <span className="text-[10px] text-slate-500">{r.label}</span>
            <span
              className={`text-xs tabular-nums ${r.accent ?? "text-slate-300"} truncate max-w-[200px]`}
              title={r.value}
            >
              {r.value}
            </span>
          </div>
        ))}
      </div>

      {/* Fallback Config */}
      {fallbackCfg && (
        <div className={crd + " space-y-2"}>
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-slate-300">
              🔄 Provider Fallback
            </span>
            <span
              className={`text-[10px] px-2 py-0.5 rounded-full border ${
                fallbackCfg.enabled
                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                  : "bg-slate-600/20 text-slate-500 border-slate-600/30"
              }`}
            >
              {fallbackCfg.enabled ? "Aktif" : "Kapalı"}
            </span>
          </div>
          {fallbackCfg.enabled && fallbackCfg.chains && (
            <div className="space-y-1.5 mt-1">
              {Object.entries(fallbackCfg.chains).map(([role, chain]) => {
                const icon = AGENT_CONFIG[role as AgentRole]?.icon ?? "🤖";
                return (
                  <div
                    key={role}
                    className="flex items-start gap-2 text-[10px]"
                  >
                    <span className="shrink-0 mt-0.5">{icon}</span>
                    <div className="min-w-0">
                      <span className="text-slate-400 capitalize">{role}</span>
                      <span className="text-slate-600 mx-1">→</span>
                      <span
                        className="text-cyan-400 truncate"
                        title={chain.primary}
                      >
                        {chain.primary.split("/").pop()}
                      </span>
                      {chain.fallbacks.length > 0 && (
                        <span className="text-slate-600">
                          {" "}
                          (+{chain.fallbacks.length} yedek)
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Tab 4: Tool Validation (Faz 14.3) ─────────────────────────── */

interface ToolSchemaSummary {
  name: string;
  description: string;
  param_count: number;
  required_count: number;
  required_params: string[];
}

interface ValStats {
  total: number;
  passed: number;
  failed: number;
  by_tool: Record<string, { passed: number; failed: number }>;
  last_sync: string | null;
  gateway_registered: number;
}

function ValidationTab() {
  const [schemas, setSchemas] = useState<ToolSchemaSummary[]>([]);
  const [stats, setStats] = useState<{ local: ValStats; gateway: any } | null>(
    null,
  );
  const [ld, setLd] = useState(true);
  const [err, setErr] = useState("");
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState("");

  // Test validation state
  const [testTool, setTestTool] = useState("");
  const [testArgs, setTestArgs] = useState("{}");
  const [testResult, setTestResult] = useState<any>(null);

  const load = useCallback(async () => {
    try {
      setErr("");
      setLd(true);
      const [schData, stData] = await Promise.all([
        fetcher<{ schemas: ToolSchemaSummary[] }>("/api/gateway/tool-schemas"),
        fetcher<{ local: ValStats; gateway: any }>(
          "/api/gateway/tool-validation-stats",
        ),
      ]);
      setSchemas(schData.schemas ?? []);
      setStats(stData);
    } catch (x) {
      setErr(x instanceof Error ? x.message : "Doğrulama verisi yüklenemedi");
    } finally {
      setLd(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const syncSchemas = useCallback(async () => {
    try {
      setSyncing(true);
      setSyncMsg("");
      const res = await fetcher<{ registered?: number; status?: string }>(
        "/api/gateway/tool-schemas/sync",
        { method: "POST" },
      );
      setSyncMsg(
        res.registered
          ? `✓ ${res.registered} şema senkronize edildi`
          : (res.status ?? "Tamamlandı"),
      );
      await load();
      setTimeout(() => setSyncMsg(""), 3000);
    } catch (x) {
      setSyncMsg(x instanceof Error ? x.message : "Senkronizasyon başarısız");
    } finally {
      setSyncing(false);
    }
  }, [load]);

  const runTest = useCallback(async () => {
    if (!testTool) return;
    try {
      let parsed: Record<string, unknown> = {};
      try {
        parsed = JSON.parse(testArgs);
      } catch {
        setTestResult({ error: "Geçersiz JSON" });
        return;
      }
      const res = await fetcher<any>("/api/gateway/tool-validate", {
        method: "POST",
        body: JSON.stringify({ tool_name: testTool, arguments: parsed }),
      });
      setTestResult(res);
    } catch (x) {
      setTestResult({
        error: x instanceof Error ? x.message : "Test başarısız",
      });
    }
  }, [testTool, testArgs]);

  if (ld) return <Sk n={4} />;
  if (err) return <Er m={err} r={load} />;

  const local = stats?.local;
  const failRate =
    local && local.total > 0
      ? ((local.failed / local.total) * 100).toFixed(1)
      : "0";

  return (
    <div className="space-y-3">
      {/* Stats summary */}
      <div className={crd + " space-y-2"}>
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-medium text-slate-300">
            📊 Doğrulama İstatistikleri
          </span>
          <button
            onClick={load}
            className="text-[10px] text-cyan-400 hover:text-cyan-300 transition-colors"
            aria-label="Yenile"
          >
            ↻
          </button>
        </div>
        <div className="grid grid-cols-4 gap-2">
          {[
            {
              label: "Toplam",
              value: local?.total ?? 0,
              accent: "text-slate-200",
            },
            {
              label: "Başarılı",
              value: local?.passed ?? 0,
              accent: "text-emerald-400",
            },
            {
              label: "Başarısız",
              value: local?.failed ?? 0,
              accent: "text-red-400",
            },
            {
              label: "Hata %",
              value: `${failRate}%`,
              accent:
                Number(failRate) > 10 ? "text-red-400" : "text-emerald-400",
            },
          ].map((s) => (
            <div key={s.label} className="text-center">
              <div className={`text-sm font-medium tabular-nums ${s.accent}`}>
                {s.value}
              </div>
              <div className="text-[9px] text-slate-500">{s.label}</div>
            </div>
          ))}
        </div>
        {local?.last_sync && (
          <div className="text-[9px] text-slate-600 text-right">
            Son senkronizasyon: {local.last_sync}
          </div>
        )}
      </div>

      {/* Registered schemas */}
      <div className={crd + " space-y-2"}>
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-medium text-slate-300">
            📋 Kayıtlı Şemalar ({schemas.length})
          </span>
          <button
            onClick={syncSchemas}
            disabled={syncing}
            className="text-[10px] px-2 py-1 rounded border transition-colors disabled:opacity-40 bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-400 border-cyan-500/20"
          >
            {syncing ? "Senkronize ediliyor…" : "🔄 Gateway'e Senkronize Et"}
          </button>
        </div>
        {syncMsg && <div className="text-[10px] text-cyan-400">{syncMsg}</div>}
        <div className="max-h-[180px] overflow-y-auto space-y-1">
          {schemas.length === 0 ? (
            <div className="text-[10px] text-slate-500 text-center py-3">
              Henüz kayıtlı şema yok
            </div>
          ) : (
            schemas.map((s) => (
              <div
                key={s.name}
                className="flex items-center justify-between py-1.5 px-2 rounded bg-slate-700/20 hover:bg-slate-700/40 transition-colors"
              >
                <div className="min-w-0 flex-1">
                  <span className="text-[11px] text-slate-200 font-mono">
                    {s.name}
                  </span>
                  {s.description && (
                    <span className="text-[9px] text-slate-500 ml-2 truncate">
                      {s.description}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-[9px] text-slate-500">
                    {s.param_count} param
                  </span>
                  <span className="text-[9px] text-amber-400">
                    {s.required_count} zorunlu
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Manual test */}
      <div className={crd + " space-y-2"}>
        <span className="text-[11px] font-medium text-slate-300">
          🧪 Manuel Test
        </span>
        <div className="flex gap-2">
          <select
            value={testTool}
            onChange={(e) => setTestTool(e.target.value)}
            className={`${sCls} flex-1`}
            aria-label="Test edilecek araç"
          >
            <option value="">Araç seçin…</option>
            {schemas.map((s) => (
              <option key={s.name} value={s.name}>
                {s.name}
              </option>
            ))}
          </select>
          <button
            onClick={runTest}
            disabled={!testTool}
            className="px-3 py-1.5 text-[10px] rounded border transition-colors disabled:opacity-40 bg-violet-600/20 hover:bg-violet-600/30 text-violet-400 border-violet-500/20"
          >
            Test Et
          </button>
        </div>
        <textarea
          value={testArgs}
          onChange={(e) => setTestArgs(e.target.value)}
          className={`${sCls} w-full h-16 font-mono resize-none`}
          placeholder='{"param": "value"}'
          aria-label="Test argümanları (JSON)"
        />
        {testResult && (
          <div
            className={`text-[10px] p-2 rounded border ${
              testResult.valid
                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                : testResult.error
                  ? "bg-red-500/10 text-red-400 border-red-500/20"
                  : "bg-red-500/10 text-red-400 border-red-500/20"
            }`}
          >
            {testResult.valid
              ? "✓ Geçerli"
              : testResult.error
                ? `✗ ${testResult.error}`
                : `✗ ${testResult.errors?.map((e: any) => `${e.path}: ${e.message}`).join(", ")}`}
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Main Panel ────────────────────────────────────────────────── */

export default function ModelManagerPanel() {
  const [tab, setTab] = useState<MgrTab>("providers");

  return (
    <div className="flex flex-col h-full">
      {/* Tab bar */}
      <div
        className="flex border-b border-slate-700/50 px-2 gap-1 flex-shrink-0"
        role="tablist"
        aria-label="Model Yönetimi sekmeleri"
      >
        {TABS.map((t) => (
          <button
            key={t.key}
            role="tab"
            aria-selected={tab === t.key}
            aria-controls={`panel-${t.key}`}
            style={tabSt(tab === t.key)}
            onClick={() => setTab(t.key)}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div
        className="flex-1 overflow-y-auto p-3"
        id={`panel-${tab}`}
        role="tabpanel"
      >
        {tab === "providers" && <ProvidersTab />}
        {tab === "mapping" && <MappingTab />}
        {tab === "gateway" && <GatewayTab />}
        {tab === "validation" && <ValidationTab />}
      </div>
    </div>
  );
}
