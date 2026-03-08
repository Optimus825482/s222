"use client";

import { useState, useEffect, useCallback } from "react";
import type { AgentRole } from "@/lib/types";
import { AGENT_ROLES, ROLE_ICON, ROLE_COLOR } from "@/lib/constants";
import { fetcher } from "@/lib/api";

/* ── local types ─────────────────────────────────────────────── */

interface EffectiveRole {
  agent_id: AgentRole;
  agent_name: string;
  original_role: AgentRole;
  effective_role: AgentRole;
  is_overridden: boolean;
  assignment_id?: string;
}

interface RoleAssignment {
  id: string;
  agent_id: AgentRole;
  agent_name: string;
  original_role: AgentRole;
  new_role: AgentRole;
  reason: string;
  task_context?: string;
  duration_minutes: number | null;
  status: "active" | "expired" | "reverted";
  created_at: string;
}

interface RoleHistoryEntry {
  id: string;
  agent_id: AgentRole;
  original_role?: AgentRole;
  new_role: AgentRole;
  reason?: string;
  task_context?: string;
  duration_minutes?: number | null;
  status?: string;
  assigned_at?: string;
  created_at?: string;
}

const DURATION_OPTIONS = [
  { value: "", label: "Kalıcı" },
  { value: "15", label: "15 dk" },
  { value: "30", label: "30 dk" },
  { value: "60", label: "1 saat" },
  { value: "120", label: "2 saat" },
];

const ROLE_LABELS: Record<AgentRole, string> = {
  orchestrator: "Orkestratör",
  thinker: "Düşünür",
  speed: "Hız",
  researcher: "Araştırmacı",
  reasoner: "Muhakemeci",
  critic: "Kritik",
};

const STATUS_STYLE: Record<
  string,
  { bg: string; text: string; label: string }
> = {
  active: { bg: "bg-blue-500/15", text: "text-blue-400", label: "Aktif" },
  expired: {
    bg: "bg-amber-500/15",
    text: "text-amber-400",
    label: "Süresi Doldu",
  },
  reverted: {
    bg: "bg-slate-500/15",
    text: "text-slate-400",
    label: "Geri Alındı",
  },
};

/* ── shared ui ───────────────────────────────────────────────── */

function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse bg-white/5 rounded ${className}`}
      aria-hidden="true"
    />
  );
}

function InlineError({ message }: { message: string }) {
  return (
    <p className="text-xs text-red-400 py-2" role="alert">
      ⚠️ {message}
    </p>
  );
}

/* ── Section 1: Mevcut Roller ────────────────────────────────── */

function CurrentRoles() {
  const [roles, setRoles] = useState<EffectiveRole[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reverting, setReverting] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const raw = await fetcher<{
        agents: Record<string, EffectiveRole>;
        timestamp: string;
      }>("/api/agents/effective-roles");
      // Backend returns {agents: {role: {...}}} — convert to array
      const agentsObj =
        (raw as { agents?: Record<string, Partial<EffectiveRole>> })?.agents ??
        raw;
      const arr: EffectiveRole[] = Object.entries(agentsObj).map(
        ([key, val]) => ({
          agent_id: key as AgentRole,
          agent_name: (val as Partial<EffectiveRole>).agent_name ?? key,
          original_role:
            (val as Partial<EffectiveRole>).original_role ?? (key as AgentRole),
          effective_role:
            (val as Partial<EffectiveRole>).effective_role ??
            (key as AgentRole),
          is_overridden: (val as Partial<EffectiveRole>).is_overridden ?? false,
          assignment_id:
            (val as Partial<EffectiveRole>).assignment_id ?? undefined,
        }),
      );
      setRoles(arr);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Roller yüklenemedi");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleRevert = async (assignmentId: string) => {
    try {
      setReverting(assignmentId);
      await fetcher(`/api/agents/role-revert/${assignmentId}`, {
        method: "POST",
      });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Geri alma başarısız");
    } finally {
      setReverting(null);
    }
  };

  if (loading) {
    return (
      <div className="space-y-1.5" aria-label="Roller yükleniyor">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-8" />
        ))}
      </div>
    );
  }

  if (error) return <InlineError message={error} />;

  return (
    <div className="overflow-x-auto">
      <table
        className="w-full text-[11px]"
        role="grid"
        aria-label="Mevcut etkin roller"
      >
        <thead>
          <tr className="text-[10px] text-slate-500">
            <th className="text-left pb-1.5 font-medium">Ajan</th>
            <th className="text-left pb-1.5 font-medium">Etkin Rol</th>
            <th className="text-right pb-1.5 font-medium">İşlem</th>
          </tr>
        </thead>
        <tbody>
          {roles.map((r) => (
            <tr key={r.agent_id} className="hover:bg-white/5 transition-colors">
              <td className="py-1.5 pr-2">
                <span className="flex items-center gap-1.5">
                  <span aria-hidden="true">{ROLE_ICON[r.agent_id]}</span>
                  <span
                    className="font-medium"
                    style={{ color: ROLE_COLOR[r.agent_id] }}
                  >
                    {r.agent_name}
                  </span>
                </span>
              </td>
              <td className="py-1.5">
                {r.is_overridden ? (
                  <span className="flex items-center gap-1">
                    <span className="text-slate-500">
                      {ROLE_ICON[r.original_role]}{" "}
                      {ROLE_LABELS[r.original_role]}
                    </span>
                    <span className="text-slate-600">→</span>
                    <span
                      className="font-medium"
                      style={{ color: ROLE_COLOR[r.effective_role] }}
                    >
                      {ROLE_ICON[r.effective_role]}{" "}
                      {ROLE_LABELS[r.effective_role]}
                    </span>
                  </span>
                ) : (
                  <span className="text-slate-400">
                    {ROLE_ICON[r.effective_role]}{" "}
                    {ROLE_LABELS[r.effective_role]}
                  </span>
                )}
              </td>
              <td className="py-1.5 text-right">
                {r.is_overridden && r.assignment_id ? (
                  <button
                    onClick={() => handleRevert(r.assignment_id!)}
                    disabled={reverting === r.assignment_id}
                    className="px-2 py-0.5 text-[10px] font-medium rounded border border-red-500/30 bg-red-500/10 text-red-400 hover:bg-red-500/20 disabled:opacity-40 transition-colors"
                    aria-label={`${r.agent_name} rolünü geri al`}
                  >
                    {reverting === r.assignment_id ? "..." : "Geri Al"}
                  </button>
                ) : (
                  <span className="text-[10px] text-slate-600">—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ── Section 2: Rol Atama ────────────────────────────────────── */

function RoleAssignmentForm({ onAssigned }: { onAssigned: () => void }) {
  const [agentId, setAgentId] = useState<AgentRole | "">("");
  const [newRole, setNewRole] = useState<AgentRole | "">("");
  const [reason, setReason] = useState("");
  const [taskContext, setTaskContext] = useState("");
  const [duration, setDuration] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const isSameRole = agentId !== "" && agentId === newRole;
  const canSubmit =
    agentId && newRole && reason.trim() && !isSameRole && !loading;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    try {
      setLoading(true);
      setError(null);
      setSuccess(false);
      await fetcher("/api/agents/role-assign", {
        method: "POST",
        body: JSON.stringify({
          agent_id: agentId,
          new_role: newRole,
          reason: reason.trim(),
          task_context: taskContext.trim() || undefined,
          duration_minutes: duration ? Number(duration) : null,
        }),
      });
      setSuccess(true);
      setAgentId("");
      setNewRole("");
      setReason("");
      setTaskContext("");
      setDuration("");
      onAssigned();
      setTimeout(() => setSuccess(false), 3000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Atama başarısız");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-2.5">
      {/* Agent + Role selectors */}
      <div className="flex gap-2">
        <select
          value={agentId}
          onChange={(e) => setAgentId(e.target.value as AgentRole | "")}
          className="flex-1 bg-white/5 border border-border rounded px-2 py-1.5 text-[11px] text-slate-300 focus:outline-none focus:border-slate-500 transition-colors"
          aria-label="Ajan seçin"
        >
          <option value="">Ajan seçin...</option>
          {AGENT_ROLES.map((role) => (
            <option key={role} value={role}>
              {ROLE_ICON[role]} {ROLE_LABELS[role]}
            </option>
          ))}
        </select>

        <span className="text-slate-600 self-center text-xs">→</span>

        <select
          value={newRole}
          onChange={(e) => setNewRole(e.target.value as AgentRole | "")}
          className="flex-1 bg-white/5 border border-border rounded px-2 py-1.5 text-[11px] text-slate-300 focus:outline-none focus:border-slate-500 transition-colors"
          aria-label="Yeni rol seçin"
        >
          <option value="">Yeni rol...</option>
          {AGENT_ROLES.map((role) => (
            <option key={role} value={role}>
              {ROLE_ICON[role]} {ROLE_LABELS[role]}
            </option>
          ))}
        </select>
      </div>

      {isSameRole && (
        <p className="text-[10px] text-amber-400">
          ⚠ Aynı rol atanamaz — farklı bir rol seçin.
        </p>
      )}

      {/* Reason */}
      <textarea
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        placeholder="Atama nedeni..."
        rows={2}
        className="w-full bg-white/5 border border-border rounded px-2 py-1.5 text-[11px] text-slate-300 placeholder-slate-600 resize-none focus:outline-none focus:border-slate-500 transition-colors"
        aria-label="Atama nedeni"
      />

      {/* Task context + Duration */}
      <div className="flex gap-2">
        <input
          type="text"
          value={taskContext}
          onChange={(e) => setTaskContext(e.target.value)}
          placeholder="Görev bağlamı (opsiyonel)"
          className="flex-1 bg-white/5 border border-border rounded px-2 py-1.5 text-[11px] text-slate-300 placeholder-slate-600 focus:outline-none focus:border-slate-500 transition-colors"
          aria-label="Görev bağlamı"
        />
        <select
          value={duration}
          onChange={(e) => setDuration(e.target.value)}
          className="bg-white/5 border border-border rounded px-2 py-1.5 text-[11px] text-slate-300 focus:outline-none focus:border-slate-500 transition-colors"
          aria-label="Süre"
        >
          {DURATION_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Submit */}
      <div className="flex items-center gap-3">
        <button
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="px-4 py-1.5 text-[11px] font-medium rounded border transition-all duration-200 bg-emerald-600/20 text-emerald-400 border-emerald-500/30 hover:bg-emerald-600/30 hover:border-emerald-500/50 disabled:opacity-40 disabled:cursor-not-allowed"
          aria-label="Rol ata"
        >
          {loading ? (
            <span className="inline-flex items-center gap-1.5">
              <span className="w-3 h-3 border-2 border-emerald-400/30 border-t-emerald-400 rounded-full animate-spin" />
              Atanıyor...
            </span>
          ) : (
            "Rol Ata"
          )}
        </button>

        {success && (
          <span className="text-[10px] text-emerald-400">
            ✓ Rol başarıyla atandı
          </span>
        )}
      </div>

      {error && <InlineError message={error} />}
    </div>
  );
}

/* ── Section 3: Atama Geçmişi ────────────────────────────────── */

function AssignmentHistory({ refreshKey }: { refreshKey: number }) {
  const [entries, setEntries] = useState<RoleAssignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const raw = await fetcher<{ history: RoleHistoryEntry[]; total: number }>(
        "/api/agents/role-history?limit=30",
      );
      // Backend returns {total, history, timestamp}
      const histArr =
        (raw as { history?: RoleHistoryEntry[] })?.history ??
        (Array.isArray(raw) ? raw : []);
      const mapped: RoleAssignment[] = histArr.map((h: RoleHistoryEntry) => ({
        id: h.id,
        agent_id: h.agent_id,
        agent_name: h.agent_id,
        original_role: h.original_role ?? h.agent_id,
        new_role: h.new_role,
        reason: h.reason ?? "",
        task_context: h.task_context,
        duration_minutes: h.duration_minutes ?? null,
        status: (h.status as RoleAssignment["status"]) ?? "active",
        created_at: h.assigned_at ?? h.created_at ?? new Date().toISOString(),
      }));
      setEntries(mapped);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Geçmiş yüklenemedi");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  if (loading) {
    return (
      <div className="space-y-1.5">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-14 rounded-lg" />
        ))}
      </div>
    );
  }

  if (error) return <InlineError message={error} />;

  if (entries.length === 0) {
    return (
      <div className="text-[11px] text-slate-600 text-center py-6">
        Henüz atama geçmişi yok
      </div>
    );
  }

  return (
    <div
      className="space-y-1.5 max-h-[300px] overflow-y-auto pr-1"
      role="list"
      aria-label="Rol atama geçmişi"
    >
      {entries.map((entry) => {
        const st = STATUS_STYLE[entry.status] ?? STATUS_STYLE.expired;
        const ts = new Date(entry.created_at);
        const timeStr = `${ts.toLocaleDateString("tr-TR")} ${ts.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" })}`;

        return (
          <article
            key={entry.id}
            className="flex items-start gap-2.5 px-3 py-2 rounded-lg bg-white/5 hover:bg-white/8 transition-colors"
            role="listitem"
            aria-label={`${entry.agent_name}: ${ROLE_LABELS[entry.original_role]} → ${ROLE_LABELS[entry.new_role]}`}
          >
            {/* Timeline dot */}
            <div className="flex flex-col items-center pt-1 shrink-0">
              <span
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: ROLE_COLOR[entry.agent_id] }}
              />
              <div className="w-px h-full bg-slate-700/50 mt-1" />
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0 space-y-1">
              <div className="flex items-center justify-between gap-2">
                <span className="flex items-center gap-1 text-[11px] font-medium">
                  <span aria-hidden="true">{ROLE_ICON[entry.agent_id]}</span>
                  <span style={{ color: ROLE_COLOR[entry.agent_id] }}>
                    {entry.agent_name}
                  </span>
                </span>
                <span
                  className={`px-1.5 py-0.5 rounded text-[9px] font-medium border ${st.bg} ${st.text} border-current/20`}
                >
                  {st.label}
                </span>
              </div>

              {/* Role transition */}
              <div className="flex items-center gap-1 text-[10px]">
                <span className="text-slate-500">
                  {ROLE_ICON[entry.original_role]}{" "}
                  {ROLE_LABELS[entry.original_role]}
                </span>
                <span className="text-slate-600">→</span>
                <span style={{ color: ROLE_COLOR[entry.new_role] }}>
                  {ROLE_ICON[entry.new_role]} {ROLE_LABELS[entry.new_role]}
                </span>
                {entry.duration_minutes && (
                  <span className="text-slate-600 ml-1">
                    (
                    {entry.duration_minutes >= 60
                      ? `${entry.duration_minutes / 60} saat`
                      : `${entry.duration_minutes} dk`}
                    )
                  </span>
                )}
              </div>

              {/* Reason */}
              <p className="text-[10px] text-slate-500 leading-snug truncate">
                {entry.reason}
              </p>

              {/* Timestamp */}
              <span className="text-[9px] text-slate-600 font-mono">
                {timeStr}
              </span>
            </div>
          </article>
        );
      })}
    </div>
  );
}

/* ── Main Export ──────────────────────────────────────────────── */

export function DynamicRolePanel() {
  const [refreshKey, setRefreshKey] = useState(0);

  const triggerRefresh = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  return (
    <section className="space-y-4" role="region" aria-label="Dinamik Rol Atama">
      {/* Section 1 */}
      <div>
        <h3 className="text-xs font-semibold text-slate-200 mb-3 flex items-center gap-1.5">
          <span aria-hidden="true">🎭</span>
          Mevcut Roller
        </h3>
        <CurrentRoles key={refreshKey} />
      </div>

      <div className="border-t border-border/50" />

      {/* Section 2 */}
      <div>
        <h3 className="text-xs font-semibold text-slate-200 mb-3 flex items-center gap-1.5">
          <span aria-hidden="true">🔄</span>
          Rol Atama
        </h3>
        <RoleAssignmentForm onAssigned={triggerRefresh} />
      </div>

      <div className="border-t border-border/50" />

      {/* Section 3 */}
      <div>
        <h3 className="text-xs font-semibold text-slate-200 mb-3 flex items-center gap-1.5">
          <span aria-hidden="true">📜</span>
          Atama Geçmişi
        </h3>
        <AssignmentHistory refreshKey={refreshKey} />
      </div>
    </section>
  );
}
