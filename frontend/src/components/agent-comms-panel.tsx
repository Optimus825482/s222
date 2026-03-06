"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "@/lib/api";
import { AGENT_CONFIG } from "@/lib/agents";
import type { AgentRole, AgentDirectMessage } from "@/lib/types";

type CommsTab = "tools" | "behavior" | "messages";
interface ToolEntry {
  tool_name: string;
  count: number;
  success_rate: number;
  avg_latency_ms: number;
  total_tokens: number;
  agents: string[];
}
interface AgentToolEntry {
  agent_role: string;
  tool_calls: number;
  success_rate: number;
  avg_latency_ms: number;
  total_tokens: number;
  tools_used: string[];
}
interface ToolData {
  total_events: number;
  by_tool: ToolEntry[];
  by_agent: AgentToolEntry[];
  recent: unknown[];
}
interface BehaviorData {
  total_events: number;
  by_action: Record<string, number>;
  recent: { action: string; timestamp: string; details?: string }[];
}

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
const CL = [
  "#f59e0b",
  "#10b981",
  "#ef4444",
  "#06b6d4",
  "#ec4899",
  "#84cc16",
  "#a78bfa",
];
const allRoles = Object.keys(AGENT_CONFIG) as AgentRole[];
const crd = "bg-slate-800/50 border border-slate-700/50 rounded-lg p-4";
const sCls =
  "bg-slate-800/60 border border-slate-700/50 rounded px-2 py-1.5 text-[10px] text-slate-300 focus:outline-none focus:border-cyan-500/50";

function tk() {
  try {
    return (
      JSON.parse(localStorage.getItem("ops-center-auth") || "{}")?.state?.user
        ?.token || ""
    );
  } catch {
    return "";
  }
}
async function fApi<T>(p: string): Promise<T> {
  const t = tk();
  const r = await fetch(`${BASE}${p}`, {
    headers: {
      "Content-Type": "application/json",
      ...(t ? { Authorization: `Bearer ${t}` } : {}),
    },
  });
  if (!r.ok) throw new Error(`API ${r.status}`);
  return r.json();
}
function ai(r: string) {
  return (
    AGENT_CONFIG[r as AgentRole] ?? { icon: "⚙️", color: "#6b7280", name: r }
  );
}
function ago(ts: string) {
  const m = Math.floor((Date.now() - new Date(ts).getTime()) / 60000);
  return m < 1
    ? "az önce"
    : m < 60
      ? `${m}dk`
      : m < 1440
        ? `${Math.floor(m / 60)}sa`
        : `${Math.floor(m / 1440)}g`;
}

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

function Bar({ v, mx, c, l }: { v: number; mx: number; c: string; l: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-slate-400 w-20 truncate" title={l}>
        {l}
      </span>
      <div className="flex-1 bg-slate-700 rounded-full h-2 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${mx > 0 ? Math.min((v / mx) * 100, 100) : 0}%`,
            backgroundColor: c,
          }}
        />
      </div>
      <span className="text-[10px] text-slate-500 w-10 text-right tabular-nums">
        {v}
      </span>
    </div>
  );
}

function St({ l, v }: { l: string; v: string | number }) {
  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg px-3 py-2 flex-1">
      <div className="text-[10px] text-slate-500 uppercase tracking-wider">
        {l}
      </div>
      <div className="text-lg font-bold text-slate-200 tabular-nums">{v}</div>
    </div>
  );
}

function Opts({ exclude }: { exclude?: string }) {
  return (
    <>
      {allRoles
        .filter((r) => r !== exclude)
        .map((r) => (
          <option key={r} value={r}>
            {ai(r).icon} {ai(r).name}
          </option>
        ))}
    </>
  );
}

/* ── Tool Usage ─────────────────────────────────────────────── */
function ToolUsageTab() {
  const [d, setD] = useState<ToolData | null>(null);
  const [e, setE] = useState("");
  const [ld, setLd] = useState(true);
  const load = useCallback(async () => {
    try {
      setE("");
      setLd(true);
      setD(await fApi<ToolData>("/api/analytics/tool-usage"));
    } catch (x) {
      setE(x instanceof Error ? x.message : "Veri yüklenemedi");
    } finally {
      setLd(false);
    }
  }, []);
  useEffect(() => {
    load();
  }, [load]);
  if (ld) return <Sk n={6} />;
  if (e) return <Er m={e} r={load} />;
  if (!d) return null;
  const mxT = Math.max(...d.by_tool.map((t) => t.count), 1),
    mxA = Math.max(...d.by_agent.map((a) => a.tool_calls), 1);
  return (
    <div className="space-y-4">
      <div className="flex gap-3">
        <St l="Toplam Event" v={d.total_events.toLocaleString()} />
        <St l="Araç Sayısı" v={d.by_tool.length} />
        <St l="Aktif Agent" v={d.by_agent.length} />
      </div>
      <div className={crd}>
        <h4 className="text-xs font-medium text-slate-200 mb-3">
          Araç Kullanımı
        </h4>
        <div className="space-y-2">
          {d.by_tool.length === 0 && (
            <p className="text-xs text-slate-600 text-center py-4">
              Henüz araç kullanımı yok
            </p>
          )}
          {d.by_tool.slice(0, 8).map((t, i) => (
            <div key={t.tool_name}>
              <Bar v={t.count} mx={mxT} c={CL[i % CL.length]} l={t.tool_name} />
              <div className="flex gap-3 ml-[88px] mt-0.5">
                <span className="text-[9px] text-slate-500">
                  Başarı:{" "}
                  <span className="text-emerald-400">
                    {(t.success_rate * 100).toFixed(0)}%
                  </span>
                </span>
                <span className="text-[9px] text-slate-500">
                  Latency:{" "}
                  <span className="text-cyan-400">
                    {t.avg_latency_ms.toFixed(0)}ms
                  </span>
                </span>
                <span className="text-[9px] text-slate-500">
                  Token:{" "}
                  <span className="text-amber-400">
                    {t.total_tokens.toLocaleString()}
                  </span>
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
      <div className={crd}>
        <h4 className="text-xs font-medium text-slate-200 mb-3">
          Agent Bazlı Kullanım
        </h4>
        <div className="space-y-2">
          {d.by_agent.map((a) => {
            const inf = ai(a.agent_role);
            return (
              <div key={a.agent_role}>
                <Bar
                  v={a.tool_calls}
                  mx={mxA}
                  c={inf.color}
                  l={`${inf.icon} ${inf.name}`}
                />
                <div className="flex gap-2 ml-[88px] mt-0.5 flex-wrap">
                  {a.tools_used.slice(0, 4).map((t) => (
                    <span
                      key={t}
                      className="text-[9px] px-1.5 py-0.5 bg-slate-700/60 text-slate-400 rounded"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

/* ── Behavior ───────────────────────────────────────────────── */
function BehaviorTab() {
  const [d, setD] = useState<BehaviorData | null>(null);
  const [e, setE] = useState("");
  const [ld, setLd] = useState(true);
  const load = useCallback(async () => {
    try {
      setE("");
      setLd(true);
      setD(await fApi<BehaviorData>("/api/analytics/user-behavior"));
    } catch (x) {
      setE(x instanceof Error ? x.message : "Veri yüklenemedi");
    } finally {
      setLd(false);
    }
  }, []);
  useEffect(() => {
    load();
  }, [load]);
  if (ld) return <Sk n={5} />;
  if (e) return <Er m={e} r={load} />;
  if (!d) return null;
  const acts = Object.entries(d.by_action).sort(([, a], [, b]) => b - a),
    mxA = Math.max(...acts.map(([, v]) => v), 1);
  return (
    <div className="space-y-4">
      <St l="Toplam Davranış Olayı" v={d.total_events.toLocaleString()} />
      <div className={crd}>
        <h4 className="text-xs font-medium text-slate-200 mb-3">
          Aksiyon Dağılımı
        </h4>
        <div className="space-y-2">
          {acts.length === 0 && (
            <p className="text-xs text-slate-600 text-center py-4">
              Henüz davranış verisi yok
            </p>
          )}
          {acts.slice(0, 10).map(([a, c], i) => (
            <Bar key={a} v={c} mx={mxA} c={CL[i % CL.length]} l={a} />
          ))}
        </div>
      </div>
      <div className={crd}>
        <h4 className="text-xs font-medium text-slate-200 mb-3">
          Son Aktiviteler
        </h4>
        <div className="space-y-1.5 max-h-60 overflow-y-auto">
          {d.recent.length === 0 && (
            <p className="text-xs text-slate-600 text-center py-4">
              Henüz aktivite yok
            </p>
          )}
          {d.recent.slice(0, 20).map((ev, i) => (
            <div
              key={i}
              className="flex items-start gap-2 py-1 border-b border-slate-700/30 last:border-0"
            >
              <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 mt-1.5 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <span className="text-[11px] text-slate-300">{ev.action}</span>
                {ev.details && (
                  <span className="text-[10px] text-slate-500 ml-1.5">
                    — {ev.details}
                  </span>
                )}
              </div>
              <span className="text-[9px] text-slate-600 flex-shrink-0">
                {ago(ev.timestamp)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── Messages ───────────────────────────────────────────────── */
function MessagesTab() {
  const [msgs, setMsgs] = useState<AgentDirectMessage[]>([]);
  const [ld, setLd] = useState(true);
  const [e, setE] = useState("");
  const [fS, setFS] = useState("");
  const [fR, setFR] = useState("");
  const [snd, setSnd] = useState("orchestrator");
  const [rcv, setRcv] = useState("thinker");
  const [txt, setTxt] = useState("");
  const [busy, setBusy] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const load = useCallback(async () => {
    try {
      setE("");
      const r = await api.getAgentMessages(
        50,
        fS || undefined,
        fR || undefined,
      );
      setMsgs(r.messages);
    } catch (x) {
      setE(x instanceof Error ? x.message : "Mesajlar yüklenemedi");
    } finally {
      setLd(false);
    }
  }, [fS, fR]);
  useEffect(() => {
    setLd(true);
    load();
    const iv = setInterval(load, 10000);
    return () => clearInterval(iv);
  }, [load]);
  const send = async () => {
    if (!txt.trim() || busy || snd === rcv) return;
    try {
      setBusy(true);
      await api.sendAgentMessage(snd, rcv, txt.trim());
      setTxt("");
      await load();
      ref.current?.scrollTo({ top: 0, behavior: "smooth" });
    } catch {
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="flex flex-col gap-3">
      <div className="flex gap-2 items-center">
        <select
          value={fS}
          onChange={(x) => setFS(x.target.value)}
          className={sCls}
          aria-label="Gönderen filtresi"
        >
          <option value="">Tüm Göndericiler</option>
          <Opts />
        </select>
        <span className="text-[10px] text-slate-600">→</span>
        <select
          value={fR}
          onChange={(x) => setFR(x.target.value)}
          className={sCls}
          aria-label="Alıcı filtresi"
        >
          <option value="">Tüm Alıcılar</option>
          <Opts />
        </select>
      </div>
      {ld ? (
        <Sk n={5} />
      ) : e ? (
        <Er m={e} r={load} />
      ) : (
        <div
          ref={ref}
          className="space-y-1 max-h-72 overflow-y-auto pr-1"
          role="log"
          aria-label="Agent mesajları"
        >
          {msgs.length === 0 && (
            <p className="text-xs text-slate-600 text-center py-8">
              Henüz mesaj yok
            </p>
          )}
          {msgs.map((m) => {
            const s = ai(m.sender),
              r = ai(m.receiver);
            return (
              <div
                key={m.id}
                className="bg-slate-800/40 border border-slate-700/30 rounded-lg px-3 py-2 hover:border-slate-600/50 transition-colors"
              >
                <div className="flex items-center gap-1.5 mb-1">
                  <span
                    className="text-[10px] font-semibold"
                    style={{ color: s.color }}
                  >
                    {s.icon} {s.name}
                  </span>
                  <span className="text-[9px] text-slate-600">→</span>
                  <span
                    className="text-[10px] font-semibold"
                    style={{ color: r.color }}
                  >
                    {r.icon} {r.name}
                  </span>
                  <span className="ml-auto text-[9px] text-slate-600">
                    {ago(m.timestamp)}
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed break-words">
                  {m.content}
                </p>
              </div>
            );
          })}
        </div>
      )}
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-3 space-y-2">
        <div className="flex gap-2 items-center">
          <select
            value={snd}
            onChange={(x) => setSnd(x.target.value)}
            className={`flex-1 ${sCls}`}
            aria-label="Gönderen ajan"
          >
            <Opts />
          </select>
          <span className="text-[10px] text-slate-600">→</span>
          <select
            value={rcv}
            onChange={(x) => setRcv(x.target.value)}
            className={`flex-1 ${sCls}`}
            aria-label="Alıcı ajan"
          >
            <Opts exclude={snd} />
          </select>
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={txt}
            onChange={(x) => setTxt(x.target.value)}
            onKeyDown={(x) => {
              if (x.key === "Enter") send();
            }}
            placeholder="Mesaj yaz..."
            className="flex-1 bg-slate-900/60 border border-slate-700/50 rounded px-2.5 py-1.5 text-[11px] text-slate-300 placeholder-slate-600 focus:outline-none focus:border-cyan-500/50"
            aria-label="Mesaj içeriği"
          />
          <button
            onClick={send}
            disabled={busy || !txt.trim() || snd === rcv}
            className="px-3 py-1.5 bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-400 text-[10px] font-medium rounded border border-cyan-500/20 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {busy ? "..." : "Gönder"}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── Main ───────────────────────────────────────────────────── */
const TABS: { key: CommsTab; label: string; icon: string }[] = [
  { key: "tools", label: "Araç Kullanımı", icon: "🔧" },
  { key: "behavior", label: "Kullanıcı Davranışı", icon: "📊" },
  { key: "messages", label: "Agent Mesajları", icon: "💬" },
];

export function AgentCommsPanel() {
  const [tab, setTab] = useState<CommsTab>("tools");
  return (
    <div className="flex flex-col h-full">
      <div
        className="flex border-b border-slate-700/50"
        role="tablist"
        aria-label="İletişim ekosistemi sekmeleri"
      >
        {TABS.map((t) => (
          <button
            key={t.key}
            role="tab"
            aria-selected={tab === t.key}
            aria-controls={`panel-${t.key}`}
            onClick={() => setTab(t.key)}
            className={`text-xs font-medium px-3 py-2 border-b-2 transition-colors ${tab === t.key ? "border-cyan-400 text-cyan-400" : "border-transparent text-slate-500 hover:text-slate-300"}`}
          >
            <span className="mr-1">{t.icon}</span>
            {t.label}
          </button>
        ))}
      </div>
      <div
        className="flex-1 overflow-y-auto p-3"
        id={`panel-${tab}`}
        role="tabpanel"
      >
        {tab === "tools" && <ToolUsageTab />}
        {tab === "behavior" && <BehaviorTab />}
        {tab === "messages" && <MessagesTab />}
      </div>
    </div>
  );
}
