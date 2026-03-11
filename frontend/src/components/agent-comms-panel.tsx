"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { api, fetcher } from "@/lib/api";
import { AGENT_CONFIG } from "@/lib/agents";
import { AgentIdentityEditor } from "./agent-identity-editor";
import type {
  AgentRole,
  AgentDirectMessage,
  AutonomousConversation,
  AutoChatConfig,
  PostTaskMeeting,
} from "@/lib/types";

type CommsTab = "behavior" | "sohbet" | "identity";
type MsgSubTab = "autonomous" | "manual" | "meetings";
interface BehaviorData {
  total_events: number;
  by_action: Record<string, number>;
  recent: { action: string; timestamp: string; details?: string }[];
}

const BAR_ACCENT_CLASSES = [
  "accent-amber-500",
  "accent-emerald-500",
  "accent-red-500",
  "accent-cyan-500",
  "accent-pink-500",
  "accent-lime-500",
  "accent-violet-400",
];
const allRoles = Object.keys(AGENT_CONFIG) as AgentRole[];
const crd = "bg-slate-800/50 border border-slate-700/50 rounded-lg p-4";
const sCls =
  "bg-slate-800/60 border border-slate-700/50 rounded px-2 py-1.5 text-[10px] text-slate-300 focus:outline-none focus:border-cyan-500/50";

const AGENT_TONE_CLASSES: Record<string, { text: string; softBg: string }> = {
  orchestrator: { text: "text-amber-400", softBg: "bg-amber-500/20" },
  thinker: { text: "text-emerald-400", softBg: "bg-emerald-500/20" },
  speed: { text: "text-red-400", softBg: "bg-red-500/20" },
  researcher: { text: "text-cyan-400", softBg: "bg-cyan-500/20" },
  reasoner: { text: "text-pink-400", softBg: "bg-pink-500/20" },
  critic: { text: "text-violet-400", softBg: "bg-violet-500/20" },
};

function ai(r: string) {
  return (
    AGENT_CONFIG[r as AgentRole] ?? { icon: "⚙️", color: "#6b7280", name: r }
  );
}
function toneFor(role: string) {
  return AGENT_TONE_CLASSES[role] ?? {
    text: "text-slate-400",
    softBg: "bg-slate-500/20",
  };
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
      <progress
        className={`flex-1 h-2 overflow-hidden rounded-full bg-slate-700 ${c}`}
        max={mx}
        value={v}
        aria-label={`${l}: ${v}`}
      />
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

/* ── Behavior ───────────────────────────────────────────────── */
function BehaviorTab() {
  const [d, setD] = useState<BehaviorData | null>(null);
  const [e, setE] = useState("");
  const [ld, setLd] = useState(true);
  const load = useCallback(async () => {
    try {
      setE("");
      setLd(true);
      setD(await fetcher<BehaviorData>("/api/analytics/user-behavior"));
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
            <Bar
              key={a}
              v={c}
              mx={mxA}
              c={BAR_ACCENT_CLASSES[i % BAR_ACCENT_CLASSES.length]}
              l={a}
            />
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
  const [sub, setSub] = useState<MsgSubTab>("autonomous");
  return (
    <div className="flex flex-col gap-3">
      <div className="flex gap-1 bg-slate-800/40 rounded-lg p-0.5">
        <button
          onClick={() => setSub("autonomous")}
          className={`flex-1 text-[10px] font-medium py-1.5 rounded-md transition-colors ${sub === "autonomous" ? "bg-cyan-600/20 text-cyan-400 border border-cyan-500/30" : "text-slate-500 hover:text-slate-300"}`}
        >
          🤖 Otonom Sohbet
        </button>
        <button
          onClick={() => setSub("manual")}
          className={`flex-1 text-[10px] font-medium py-1.5 rounded-md transition-colors ${sub === "manual" ? "bg-cyan-600/20 text-cyan-400 border border-cyan-500/30" : "text-slate-500 hover:text-slate-300"}`}
        >
          ✉️ Manuel Mesaj
        </button>
        <button
          onClick={() => setSub("meetings")}
          className={`flex-1 text-[10px] font-medium py-1.5 rounded-md transition-colors ${sub === "meetings" ? "bg-cyan-600/20 text-cyan-400 border border-cyan-500/30" : "text-slate-500 hover:text-slate-300"}`}
        >
          🏛️ Toplantılar
        </button>
      </div>
      {sub === "autonomous" && <AutonomousChatTab />}
      {sub === "manual" && <ManualMessagesTab />}
      {sub === "meetings" && <MeetingsTab />}
    </div>
  );
}

/* ── Autonomous Chat (ClaudBot-style) ───────────────────────── */
function AutonomousChatTab() {
  const [convs, setConvs] = useState<AutonomousConversation[]>([]);
  const [cfg, setCfg] = useState<AutoChatConfig | null>(null);
  const [ld, setLd] = useState(true);
  const [e, setE] = useState("");
  const [triggering, setTriggering] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [filterAgent, setFilterAgent] = useState("");
  const [showCfg, setShowCfg] = useState(false);

  const loadConvs = useCallback(async () => {
    try {
      setE("");
      const r = await api.getAutonomousConversations(
        20,
        filterAgent || undefined,
      );
      setConvs(r.conversations);
    } catch (x) {
      setE(x instanceof Error ? x.message : "Yüklenemedi");
    } finally {
      setLd(false);
    }
  }, [filterAgent]);

  const loadCfg = useCallback(async () => {
    try {
      const r = await api.getAutoChatConfig();
      setCfg(r.config);
    } catch {}
  }, []);

  useEffect(() => {
    setLd(true);
    loadConvs();
    loadCfg();
    const iv = setInterval(loadConvs, 12000);
    return () => clearInterval(iv);
  }, [loadConvs, loadCfg]);

  const trigger = async () => {
    if (triggering) return;
    try {
      setTriggering(true);
      await api.triggerAutonomousChat();
      await loadConvs();
    } catch {
    } finally {
      setTriggering(false);
    }
  };

  const toggleEnabled = async () => {
    if (!cfg) return;
    try {
      const r = await api.updateAutoChatConfig({ enabled: !cfg.enabled });
      setCfg(r.config);
    } catch {}
  };

  const toggleAutoStart = async () => {
    if (!cfg) return;
    try {
      const r = await api.updateAutoChatConfig({ auto_start: !cfg.auto_start });
      setCfg(r.config);
    } catch {}
  };

  return (
    <div className="flex flex-col gap-3">
      {/* Scheduler status banner */}
      {cfg?.scheduler_running && (
        <div className="flex items-center gap-2 px-2.5 py-1.5 bg-emerald-900/20 border border-emerald-500/15 rounded text-[10px] text-emerald-400">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          Otonom zamanlayıcı çalışıyor — her {cfg.interval_minutes}dk&apos;da
          bir sohbet
        </div>
      )}

      {/* Controls */}
      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={trigger}
          disabled={triggering || (cfg !== null && !cfg.enabled)}
          className="px-3 py-1.5 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 text-[10px] font-medium rounded border border-emerald-500/20 transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1"
        >
          {triggering ? (
            <span className="inline-block w-3 h-3 border border-emerald-400 border-t-transparent rounded-full animate-spin" />
          ) : (
            "⚡"
          )}
          {triggering ? "Başlatılıyor..." : "Sohbet Başlat"}
        </button>
        <button
          onClick={toggleEnabled}
          className={`px-2.5 py-1.5 text-[10px] font-medium rounded border transition-colors ${cfg?.enabled ? "bg-green-600/15 text-green-400 border-green-500/20 hover:bg-green-600/25" : "bg-red-600/15 text-red-400 border-red-500/20 hover:bg-red-600/25"}`}
        >
          {cfg?.enabled ? "● Aktif" : "○ Pasif"}
        </button>
        <button
          onClick={toggleAutoStart}
          disabled={!cfg?.enabled}
          className={`px-2.5 py-1.5 text-[10px] font-medium rounded border transition-colors disabled:opacity-40 ${cfg?.auto_start ? "bg-cyan-600/15 text-cyan-400 border-cyan-500/20 hover:bg-cyan-600/25" : "bg-slate-600/15 text-slate-400 border-slate-500/20 hover:bg-slate-600/25"}`}
          title={
            cfg?.auto_start
              ? "Otomatik başlatma açık"
              : "Otomatik başlatma kapalı"
          }
        >
          {cfg?.auto_start ? "🔄 Oto" : "⏸ Manuel"}
        </button>
        <button
          onClick={() => setShowCfg(!showCfg)}
          className="px-2 py-1.5 text-[10px] text-slate-500 hover:text-slate-300 transition-colors"
        >
          ⚙️
        </button>
        <label id="agent-filter-label" htmlFor="agent-filter" className="sr-only">
          Agent filtresi
        </label>
        <select
          id="agent-filter"
          name="agent-filter"
          value={filterAgent}
          onChange={(x) => setFilterAgent(x.target.value)}
          className={`ml-auto ${sCls}`}
          aria-labelledby="agent-filter-label"
          aria-label="Agent filtresi"
          title="Agent filtresi"
        >
          <option value="">Tüm Ajanlar</option>
          <Opts />
        </select>
      </div>

      {/* Config Panel */}
      {showCfg && cfg && <CfgPanel cfg={cfg} onUpdate={setCfg} />}

      {/* Conversations */}
      {ld ? (
        <Sk n={4} />
      ) : e ? (
        <Er m={e} r={loadConvs} />
      ) : convs.length === 0 ? (
        <div className="text-center py-10">
          <div className="text-3xl mb-2">🤖</div>
          <p className="text-xs text-slate-500">Henüz otonom sohbet yok</p>
          <p className="text-[10px] text-slate-600 mt-1">
            {cfg?.auto_start
              ? "Otomatik sohbet aktif — ajanlar kısa süre içinde konuşmaya başlayacak"
              : '"Sohbet Başlat" ile ajanların kendi aralarında konuşmasını başlatın'}
          </p>
        </div>
      ) : (
        <div
          className="space-y-2 max-h-[420px] overflow-y-auto pr-1"
          role="log"
          aria-label="Otonom sohbetler"
        >
          {convs.map((c) => {
            const ini = ai(c.initiator);
            const iniTone = toneFor(c.initiator);
            const res = ai(c.responder);
            const resTone = toneFor(c.responder);
            const isOpen = expanded === c.id;
            return (
              <div
                key={c.id}
                className="bg-slate-800/40 border border-slate-700/30 rounded-lg overflow-hidden hover:border-slate-600/40 transition-colors"
              >
                <button
                  onClick={() => setExpanded(isOpen ? null : c.id)}
                  className="w-full flex items-center gap-2 px-3 py-2 text-left"
                  {...(isOpen
                    ? { "aria-expanded": "true" }
                    : { "aria-expanded": "false" })}
                >
                  <span className={`text-sm ${iniTone.text}`}>
                    {ini.icon}
                  </span>
                  <span className="text-[10px] text-slate-500">⇄</span>
                  <span className={`text-sm ${resTone.text}`}>
                    {res.icon}
                  </span>
                  <span className="text-[10px] text-slate-400 flex-1 truncate">
                    {c.topic}
                  </span>
                  <span className="text-[9px] text-slate-600 tabular-nums">
                    {c.message_count} mesaj
                  </span>
                  <span className="text-[9px] text-slate-600">
                    {ago(c.started_at)}
                  </span>
                  <span
                    className={`text-[10px] transition-transform ${isOpen ? "rotate-180" : ""}`}
                  >
                    ▾
                  </span>
                </button>
                {isOpen && (
                  <div className="border-t border-slate-700/30 px-3 py-2 space-y-1.5">
                    {c.messages.map((m) => {
                      const s = ai(m.sender);
                      const sTone = toneFor(m.sender);
                      const isLeft = m.sender === c.initiator;
                      return (
                        <div
                          key={m.id}
                          className={`flex gap-2 ${isLeft ? "" : "flex-row-reverse"}`}
                        >
                          <div
                            className={`flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-[10px] ${sTone.softBg}`}
                          >
                            {s.icon}
                          </div>
                          <div
                            className={`max-w-[80%] rounded-lg px-2.5 py-1.5 ${isLeft ? "bg-slate-700/40 rounded-tl-none" : "bg-cyan-900/20 rounded-tr-none"}`}
                          >
                            <div className="flex items-center gap-1.5 mb-0.5">
                              <span className={`text-[9px] font-semibold ${sTone.text}`}>
                                {s.name}
                              </span>
                              <span className="text-[8px] text-slate-600">
                                {ago(m.timestamp)}
                              </span>
                            </div>
                            {"personality" in m &&
                              (m as { personality?: string }).personality && (
                                <p
                                  className="text-[8px] text-slate-500 italic mb-1 line-clamp-2"
                                  title={
                                    (m as { personality?: string }).personality
                                  }
                                >
                                  {(m as { personality?: string }).personality}
                                </p>
                              )}
                            <p className="text-[11px] text-slate-300 leading-relaxed break-words">
                              {m.content}
                            </p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ── Config Panel ───────────────────────────────────────────── */
function CfgPanel({
  cfg,
  onUpdate,
}: {
  cfg: AutoChatConfig;
  onUpdate: (c: AutoChatConfig) => void;
}) {
  const [maxEx, setMaxEx] = useState(cfg.max_exchanges);
  const [agents, setAgents] = useState<string[]>(cfg.enabled_agents);
  const [autoStart, setAutoStart] = useState(cfg.auto_start ?? true);
  const [interval, setInterval_] = useState(cfg.interval_minutes ?? 5);

  const save = async () => {
    try {
      const r = await api.updateAutoChatConfig({
        max_exchanges: maxEx,
        enabled_agents: agents,
        auto_start: autoStart,
        interval_minutes: interval,
      });
      onUpdate(r.config);
    } catch {}
  };

  const toggleAgent = (role: string) => {
    setAgents((prev) =>
      prev.includes(role) ? prev.filter((a) => a !== role) : [...prev, role],
    );
  };

  return (
    <div className="bg-slate-800/60 border border-slate-700/40 rounded-lg p-3 space-y-2">
      <div className="text-[10px] text-slate-400 font-medium">Ayarlar</div>
      <div className="flex items-center gap-3">
        <button
          onClick={() => setAutoStart(!autoStart)}
          className={`text-[9px] px-2 py-1 rounded border transition-colors ${autoStart ? "border-emerald-500/30 bg-emerald-600/15 text-emerald-400" : "border-slate-700/40 text-slate-600 hover:text-slate-400"}`}
        >
          {autoStart
            ? "🔄 Otomatik Başlatma: Açık"
            : "⏸ Otomatik Başlatma: Kapalı"}
        </button>
        <span className="text-[10px] text-slate-500">Aralık:</span>
        <input
          id="auto-chat-interval"
          type="range"
          min={1}
          max={30}
          value={interval}
          onChange={(x) => setInterval_(Number(x.target.value))}
          className="w-20 h-1 accent-cyan-500"
          aria-label="Sohbet aralığı dakika"
          title="Sohbet aralığı dakika"
        />
        <span className="text-[10px] text-cyan-400 tabular-nums">
          {interval} dk
        </span>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-[10px] text-slate-500">Maks. mesaj:</span>
        <input
          id="auto-chat-max-messages"
          type="range"
          min={2}
          max={6}
          value={maxEx}
          onChange={(x) => setMaxEx(Number(x.target.value))}
          className="flex-1 h-1 accent-cyan-500"
          aria-label="Maksimum mesaj sayısı"
          title="Maksimum mesaj sayısı"
        />
        <span className="text-[10px] text-cyan-400 tabular-nums w-4 text-center">
          {maxEx}
        </span>
      </div>
      <div className="flex flex-wrap gap-1">
        {allRoles.map((r) => {
          const a = ai(r);
          const on = agents.includes(r);
          return (
            <button
              key={r}
              onClick={() => toggleAgent(r)}
              className={`text-[9px] px-2 py-1 rounded border transition-colors ${on ? "border-cyan-500/30 bg-cyan-600/15 text-cyan-400" : "border-slate-700/40 text-slate-600 hover:text-slate-400"}`}
            >
              {a.icon} {a.name}
            </button>
          );
        })}
      </div>
      <button
        onClick={save}
        disabled={agents.length < 2}
        className="w-full py-1.5 text-[10px] font-medium bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-400 rounded border border-cyan-500/20 transition-colors disabled:opacity-40"
      >
        Kaydet
      </button>
    </div>
  );
}

/* ── Manual Messages (existing) ─────────────────────────────── */
function ManualMessagesTab() {
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
        <label id="sender-filter-label" htmlFor="sender-filter" className="sr-only">
          Gönderen filtresi
        </label>
        <select
          id="sender-filter"
          name="sender-filter"
          value={fS}
          onChange={(x) => setFS(x.target.value)}
          className={sCls}
          aria-labelledby="sender-filter-label"
          aria-label="Gönderen filtresi"
          title="Gönderen filtresi"
        >
          <option value="">Tüm Göndericiler</option>
          <Opts />
        </select>
        <span className="text-[10px] text-slate-600">→</span>
        <label id="receiver-filter-label" htmlFor="receiver-filter" className="sr-only">
          Alıcı filtresi
        </label>
        <select
          id="receiver-filter"
          name="receiver-filter"
          value={fR}
          onChange={(x) => setFR(x.target.value)}
          className={sCls}
          aria-labelledby="receiver-filter-label"
          aria-label="Alıcı filtresi"
          title="Alıcı filtresi"
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
              sTone = toneFor(m.sender),
              r = ai(m.receiver),
              rTone = toneFor(m.receiver);
            return (
              <div
                key={m.id}
                className="bg-slate-800/40 border border-slate-700/30 rounded-lg px-3 py-2 hover:border-slate-600/50 transition-colors"
              >
                <div className="flex items-center gap-1.5 mb-1">
                  <span className={`text-[10px] font-semibold ${sTone.text}`}>
                    {s.icon} {s.name}
                  </span>
                  <span className="text-[9px] text-slate-600">→</span>
                  <span className={`text-[10px] font-semibold ${rTone.text}`}>
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
          <label id="message-sender-label" htmlFor="message-sender" className="sr-only">
            Gönderen ajan
          </label>
          <select
            id="message-sender"
            name="message-sender"
            value={snd}
            onChange={(x) => setSnd(x.target.value)}
            className={`flex-1 ${sCls}`}
            aria-labelledby="message-sender-label"
            aria-label="Gönderen ajan"
            title="Gönderen ajan"
          >
            <Opts />
          </select>
          <span className="text-[10px] text-slate-600">→</span>
          <label id="message-receiver-label" htmlFor="message-receiver" className="sr-only">
            Alıcı ajan
          </label>
          <select
            id="message-receiver"
            name="message-receiver"
            value={rcv}
            onChange={(x) => setRcv(x.target.value)}
            className={`flex-1 ${sCls}`}
            aria-labelledby="message-receiver-label"
            aria-label="Alıcı ajan"
            title="Alıcı ajan"
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

/* ── Post-Task Meetings ─────────────────────────────────────── */
function MeetingsTab() {
  const [meetings, setMeetings] = useState<PostTaskMeeting[]>([]);
  const [ld, setLd] = useState(true);
  const [e, setE] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [triggering, setTriggering] = useState(false);

  const load = useCallback(async () => {
    try {
      setE("");
      const r = await api.getMeetings(20);
      setMeetings(r.meetings);
    } catch (x) {
      setE(x instanceof Error ? x.message : "Yüklenemedi");
    } finally {
      setLd(false);
    }
  }, []);

  useEffect(() => {
    setLd(true);
    load();
    const iv = setInterval(load, 15000);
    return () => clearInterval(iv);
  }, [load]);

  const triggerManual = async () => {
    if (triggering) return;
    try {
      setTriggering(true);
      await api.triggerMeeting();
      await load();
    } catch {
    } finally {
      setTriggering(false);
    }
  };

  const msgTypeStyle = (t: string) => {
    if (t === "opening") return "border-l-2 border-l-pink-500/50";
    if (t === "closing") return "border-l-2 border-l-emerald-500/50";
    return "border-l-2 border-l-slate-600/50";
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <button
          onClick={triggerManual}
          disabled={triggering}
          className="px-3 py-1.5 bg-pink-600/20 hover:bg-pink-600/30 text-pink-400 text-[10px] font-medium rounded border border-pink-500/20 transition-colors disabled:opacity-40 flex items-center gap-1"
        >
          {triggering ? (
            <span className="inline-block w-3 h-3 border border-pink-400 border-t-transparent rounded-full animate-spin" />
          ) : (
            "🏛️"
          )}
          {triggering ? "Toplanıyor..." : "Toplantı Başlat"}
        </button>
        <span className="text-[9px] text-slate-600 ml-auto">
          Görev sonrası otomatik tetiklenir
        </span>
      </div>

      {ld ? (
        <Sk n={4} />
      ) : e ? (
        <Er m={e} r={load} />
      ) : meetings.length === 0 ? (
        <div className="text-center py-10">
          <div className="text-3xl mb-2">🏛️</div>
          <p className="text-xs text-slate-500">Henüz toplantı yok</p>
          <p className="text-[10px] text-slate-600 mt-1">
            Görev tamamlandığında Orchestrator otomatik toplantı düzenler
          </p>
        </div>
      ) : (
        <div
          className="space-y-2 max-h-[420px] overflow-y-auto pr-1"
          role="log"
          aria-label="Toplantılar"
        >
          {meetings.map((m) => {
            const isOpen = expanded === m.id;
            const statusColor =
              m.task_status === "completed"
                ? "text-emerald-400"
                : "text-red-400";
            const statusIcon = m.task_status === "completed" ? "✅" : "❌";
            return (
              <div
                key={m.id}
                className="bg-slate-800/40 border border-slate-700/30 rounded-lg overflow-hidden hover:border-slate-600/40 transition-colors"
              >
                <button
                  onClick={() => setExpanded(isOpen ? null : m.id)}
                  className="w-full flex items-center gap-2 px-3 py-2.5 text-left"
                >
                  <span className="text-sm">🏛️</span>
                  <div className="flex-1 min-w-0">
                    <div className="text-[10px] text-slate-300 truncate">
                      {m.task_summary}
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className={`text-[9px] ${statusColor}`}>
                        {statusIcon}
                      </span>
                      <span className="text-[9px] text-slate-600">
                        {m.participants.length} katılımcı
                      </span>
                      <span className="text-[9px] text-slate-600">
                        {m.message_count} mesaj
                      </span>
                    </div>
                  </div>
                  <span className="text-[9px] text-slate-600">
                    {ago(m.started_at)}
                  </span>
                  <span
                    className={`text-[10px] transition-transform ${isOpen ? "rotate-180" : ""}`}
                  >
                    ▾
                  </span>
                </button>
                {isOpen && (
                  <div className="border-t border-slate-700/30 px-3 py-2 space-y-2">
                    {/* Meeting stats */}
                    <div className="flex gap-3 text-[9px] text-slate-500 pb-1 border-b border-slate-700/20">
                      <span>
                        ⏱{" "}
                        {m.duration_ms > 0
                          ? `${(m.duration_ms / 1000).toFixed(1)}s`
                          : "—"}
                      </span>
                      <span>🪙 {m.total_tokens.toLocaleString()} token</span>
                      <span>
                        👥 {m.participants.map((p) => ai(p).icon).join(" ")}
                      </span>
                    </div>
                    {/* Messages */}
                    {m.messages.map((msg) => {
                      const speaker = ai(msg.speaker);
                      return (
                        <div
                          key={msg.id}
                          className={`pl-3 py-1.5 ${msgTypeStyle(msg.msg_type)}`}
                        >
                          <div className="flex items-center gap-1.5 mb-0.5">
                            <span
                              className={`text-[10px] ${toneFor(msg.speaker).text}`}
                            >
                              {speaker.icon} {speaker.name}
                            </span>
                            {msg.msg_type === "opening" && (
                              <span className="text-[8px] bg-pink-500/15 text-pink-400 px-1 rounded">
                                açılış
                              </span>
                            )}
                            {msg.msg_type === "closing" && (
                              <span className="text-[8px] bg-emerald-500/15 text-emerald-400 px-1 rounded">
                                kapanış
                              </span>
                            )}
                            <span className="text-[8px] text-slate-600 ml-auto">
                              {ago(msg.timestamp)}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-400 leading-relaxed break-words">
                            {msg.content}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ── Collective policy type ──────────────────────────────────── */
type CollectivePolicy = {
  quorum_min_votes: number;
  majority_ratio: number;
  tie_breaker: string;
  allow_human_escalation: boolean;
  escalation_threshold_ratio?: number;
};

type SocialProposal = {
  id: string;
  proposer: string;
  title: string;
  description: string;
  votes: Record<string, string>;
  status: string;
  resolution_reason?: string | null;
  created_at: string;
};

/* ── Social summary (learnings + proposals + policy + resolve) ── */
function SocialSummaryBlock() {
  const [learnings, setLearnings] = useState<
    { id: string; teacher: string; pattern: string; adopted_by: string[] }[]
  >([]);
  const [proposals, setProposals] = useState<SocialProposal[]>([]);
  const [policy, setPolicy] = useState<CollectivePolicy | null>(null);
  const [loading, setLoading] = useState(true);
  const [policySaving, setPolicySaving] = useState(false);
  const [resolveProposalId, setResolveProposalId] = useState<string | null>(
    null,
  );
  const [resolveReason, setResolveReason] = useState("");
  const [resolving, setResolving] = useState(false);

  const load = useCallback(async () => {
    try {
      const [lr, pr, pol] = await Promise.all([
        api.getSocialLearnings(undefined, 8),
        api.getSocialProposals(undefined, 15),
        api.getCollectivePolicy().catch(() => ({ policy: null })),
      ]);
      setLearnings(lr.learnings ?? []);
      setProposals(pr.proposals ?? []);
      setPolicy(pol.policy ?? null);
    } catch {
      setLearnings([]);
      setProposals([]);
      setPolicy(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onSavePolicy = async () => {
    if (!policy) return;
    setPolicySaving(true);
    try {
      await api.updateCollectivePolicy({
        quorum_min_votes: policy.quorum_min_votes,
        majority_ratio: policy.majority_ratio,
        tie_breaker: policy.tie_breaker,
        allow_human_escalation: policy.allow_human_escalation,
        escalation_threshold_ratio: policy.escalation_threshold_ratio,
      });
      await load();
    } finally {
      setPolicySaving(false);
    }
  };

  const onResolve = async (resolution: "passed" | "rejected") => {
    if (!resolveProposalId) return;
    setResolving(true);
    try {
      await api.resolveSocialProposal(
        resolveProposalId,
        resolution,
        resolveReason || undefined,
      );
      setResolveProposalId(null);
      setResolveReason("");
      await load();
    } finally {
      setResolving(false);
    }
  };

  if (loading) return <Sk n={2} />;
  return (
    <div className="space-y-4 text-[10px]">
      {/* Kolektif karar policy (Faz 12.2) */}
      {policy && (
        <details className="bg-slate-800/40 border border-slate-700/40 rounded-lg overflow-hidden">
          <summary className="px-3 py-2 cursor-pointer text-slate-300 font-medium">
            Kolektif karar policy (quorum, çoğunluk, tie-breaker)
          </summary>
          <div className="px-3 pb-3 pt-1 space-y-2 border-t border-slate-700/40">
            <div className="grid grid-cols-2 gap-2">
              <label className="flex flex-col gap-0.5">
                <span className="text-slate-500">Quorum (min oy)</span>
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={policy.quorum_min_votes}
                  onChange={(e) =>
                    setPolicy((p) =>
                      p
                        ? {
                            ...p,
                            quorum_min_votes: Number(e.target.value) || 1,
                          }
                        : null,
                    )
                  }
                  className={sCls}
                />
              </label>
              <label className="flex flex-col gap-0.5">
                <span className="text-slate-500">Çoğunluk oranı (0–1)</span>
                <input
                  type="number"
                  min={0.1}
                  max={1}
                  step={0.05}
                  value={policy.majority_ratio}
                  onChange={(e) =>
                    setPolicy((p) =>
                      p
                        ? {
                            ...p,
                            majority_ratio: Number(e.target.value) || 0.6,
                          }
                        : null,
                    )
                  }
                  className={sCls}
                />
              </label>
            </div>
            <div className="flex flex-col gap-0.5">
              <label htmlFor="tie-breaker-strategy" className="text-slate-500">
                Tie-breaker
              </label>
              <select
                id="tie-breaker-strategy"
                name="tie-breaker-strategy"
                value={policy.tie_breaker}
                onChange={(e) =>
                  setPolicy((p) =>
                    p ? { ...p, tie_breaker: e.target.value } : null,
                  )
                }
                className={sCls}
                aria-label="Tie-breaker stratejisi"
                title="Tie-breaker stratejisi"
              >
                <option value="proposer_wins">Proposer kazanır</option>
                <option value="reject">Varsayılan red</option>
                <option value="random">Rastgele (insan çözer)</option>
                <option value="human">İnsan kararı</option>
              </select>
            </div>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={policy.allow_human_escalation}
                onChange={(e) =>
                  setPolicy((p) =>
                    p
                      ? { ...p, allow_human_escalation: e.target.checked }
                      : null,
                  )
                }
                className="accent-cyan-500"
              />
              <span className="text-slate-400">
                İnsan escalation (needs_human)
              </span>
            </label>
            <button
              type="button"
              onClick={onSavePolicy}
              disabled={policySaving}
              className="px-2 py-1.5 bg-cyan-600/20 text-cyan-400 rounded border border-cyan-500/30 text-[10px] disabled:opacity-50"
            >
              {policySaving ? "…" : "Kaydet"}
            </button>
          </div>
        </details>
      )}

      <p className="text-slate-500">
        Öğrenmeler: {learnings.length} · Oylamalar: {proposals.length}
      </p>
      {learnings.length === 0 && proposals.length === 0 && (
        <p className="text-slate-600">
          Henüz peer öğrenme veya oylama yok. API: POST /api/social/learnings,
          /api/social/proposals
        </p>
      )}
      {learnings.slice(0, 4).map((l) => (
        <div key={l.id} className="truncate text-slate-400">
          {ai(l.teacher).icon} {l.teacher}: {l.pattern.slice(0, 60)}… ·{" "}
          {l.adopted_by?.length ?? 0} benimsedi
        </div>
      ))}

      {/* Proposals list with resolve for needs_human */}
      <div className="space-y-2">
        {proposals.slice(0, 10).map((p) => (
          <div
            key={p.id}
            className="rounded border border-slate-700/50 bg-slate-800/30 p-2 space-y-1"
          >
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <span className="font-medium text-slate-300">{p.title}</span>
              <span
                className={`text-[9px] px-1.5 py-0.5 rounded ${
                  p.status === "passed"
                    ? "bg-green-500/20 text-green-400"
                    : p.status === "rejected"
                      ? "bg-red-500/20 text-red-400"
                      : p.status === "needs_human"
                        ? "bg-amber-500/20 text-amber-400"
                        : "bg-slate-600/40 text-slate-400"
                }`}
              >
                {p.status}
              </span>
            </div>
            <div className="text-slate-500 text-[9px]">
              {ai(p.proposer).icon} {p.proposer} · {Object.keys(p.votes).length}{" "}
              oy
              {p.resolution_reason && ` · ${p.resolution_reason}`}
            </div>
            {p.status === "needs_human" && (
              <div className="pt-1 border-t border-slate-700/40">
                {resolveProposalId === p.id ? (
                  <div className="space-y-1.5">
                    <input
                      type="text"
                      placeholder="Gerekçe (opsiyonel)"
                      value={resolveReason}
                      onChange={(e) => setResolveReason(e.target.value)}
                      className={`${sCls} w-full text-[10px]`}
                      aria-label="Karar gerekçesi"
                      title="Karar gerekçesi"
                    />
                    <div className="flex gap-1.5">
                      <button
                        onClick={() => onResolve("passed")}
                        disabled={resolving}
                        className="px-2 py-1 bg-green-600/20 text-green-400 rounded text-[10px] disabled:opacity-50"
                      >
                        Kabul
                      </button>
                      <button
                        onClick={() => onResolve("rejected")}
                        disabled={resolving}
                        className="px-2 py-1 bg-red-600/20 text-red-400 rounded text-[10px] disabled:opacity-50"
                      >
                        Red
                      </button>
                      <button
                        onClick={() => {
                          setResolveProposalId(null);
                          setResolveReason("");
                        }}
                        className="px-2 py-1 text-slate-500 rounded text-[10px]"
                      >
                        İptal
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    onClick={() => setResolveProposalId(p.id)}
                    className="px-2 py-1 bg-amber-600/20 text-amber-400 rounded border border-amber-500/30 text-[10px]"
                  >
                    Çöz (insan kararı)
                  </button>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Post-Task Meetings ──────────────────────────────────────── */
function MeetingsSection() {
  const [meetings, setMeetings] = useState<PostTaskMeeting[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [summary, setSummary] = useState("");

  const load = useCallback(async () => {
    try {
      const r = await api.getMeetings(15);
      setMeetings(r.meetings);
    } catch {
      setMeetings([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onTrigger = async () => {
    if (triggering) return;
    try {
      setTriggering(true);
      await api.triggerMeeting(summary || "Manuel toplantı");
      setSummary("");
      await load();
    } finally {
      setTriggering(false);
    }
  };

  if (loading) return <Sk n={3} />;
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 flex-wrap">
        <input
          type="text"
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          placeholder="Görev özeti (opsiyonel)"
          className={`${sCls} flex-1 min-w-[120px]`}
          maxLength={120}
          aria-label="Görev özeti"
          title="Görev özeti"
        />
        <button
          onClick={onTrigger}
          disabled={triggering}
          className="px-3 py-1.5 bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-400 text-[10px] font-medium rounded border border-cyan-500/20 disabled:opacity-50"
        >
          {triggering ? "…" : "Toplantı Başlat"}
        </button>
      </div>
      <p className="text-[10px] text-slate-500">
        Görev bittiğinde otomatik retrospektif toplantı da oluşturulur.
      </p>
      <div className="space-y-2 max-h-48 overflow-y-auto">
        {meetings.length === 0 ? (
          <p className="text-[10px] text-slate-600">Henüz toplantı yok</p>
        ) : (
          meetings.map((meet) => (
            <div
              key={meet.id}
              className="bg-slate-800/40 border border-slate-700/30 rounded-lg px-3 py-2"
            >
              <div className="text-[10px] text-slate-400 truncate">
                {meet.task_summary}
              </div>
              <div className="text-[9px] text-slate-600 mt-0.5">
                {meet.participants?.length ?? 0} katılımcı ·{" "}
                {meet.message_count} mesaj · {ago(meet.started_at)}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

/* ── Main ───────────────────────────────────────────────────── */
const TABS: { key: CommsTab; label: string; icon: string }[] = [
  { key: "behavior", label: "Kullanıcı Davranışı", icon: "📊" },
  { key: "sohbet", label: "Sohbet & Toplantılar", icon: "💬" },
  { key: "identity", label: "Kimlik", icon: "🧬" },
];

export function AgentCommsPanel() {
  const [tab, setTab] = useState<CommsTab>("behavior");
  return (
    <div className="flex flex-col h-full">
      <div
        className="flex border-b border-slate-700/50"
        role="tablist"
        aria-label="İletişim ekosistemi sekmeleri"
      >
        {TABS.map((t) => (
          (() => {
            const isSelected = tab === t.key;
            return (
              <button
                key={t.key}
                id={`tab-${t.key}`}
                role="tab"
                {...(isSelected
                  ? { "aria-selected": "true" }
                  : { "aria-selected": "false" })}
                aria-controls={`panel-${t.key}`}
                onClick={() => setTab(t.key)}
                className={`text-xs font-medium px-3 py-2 border-b-2 transition-colors ${isSelected ? "border-cyan-400 text-cyan-400" : "border-transparent text-slate-500 hover:text-slate-300"}`}
              >
                <span className="mr-1">{t.icon}</span>
                {t.label}
              </button>
            );
          })()
        ))}
      </div>
      <div
        className="flex-1 overflow-y-auto p-3"
        id={`panel-${tab}`}
        role="tabpanel"
        aria-labelledby={`tab-${tab}`}
      >
        {tab === "behavior" && <BehaviorTab />}
        {tab === "sohbet" && (
          <div className="space-y-4">
            <MessagesTab />
            <div className={crd}>
              <h4 className="text-xs font-medium text-slate-200 mb-2">
                Post-task toplantılar
              </h4>
              <MeetingsSection />
            </div>
            <div className={crd}>
              <h4 className="text-xs font-medium text-slate-200 mb-2">
                Kolektif (öğrenmeler & oylamalar)
              </h4>
              <SocialSummaryBlock />
            </div>
          </div>
        )}
        {tab === "identity" && <AgentIdentityEditor />}
      </div>
    </div>
  );
}
