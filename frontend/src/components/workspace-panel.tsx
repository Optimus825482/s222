"use client";

import { useState, useEffect, useCallback } from "react";
import { workspaceApi } from "@/lib/api";

type Tab = "overview" | "skills" | "events" | "create";

interface WorkspaceStats {
  agents: Record<string, { skill_count: number; last_active: string | null }>;
  total_skills: number;
}

interface SkillInfo {
  name: string;
  description: string;
  scripts: string[];
  path: string;
}

interface EventInfo {
  id: string;
  event_type: string;
  target_agent: string;
  message: string;
  schedule: string | null;
  trigger_at: string | null;
  created_by: string | null;
  created_at: string;
}

const AGENT_ROLES = [
  "orchestrator",
  "researcher",
  "reasoner",
  "critic",
  "synthesizer",
  "speed",
];

const tabStyle = (active: boolean) => ({
  padding: "6px 14px",
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

export function WorkspacePanel() {
  const [tab, setTab] = useState<Tab>("overview");

  return (
    <div
      className="flex flex-col h-full overflow-hidden"
      style={{ fontFamily: "Tahoma, sans-serif", fontSize: 12 }}
    >
      <div
        style={{
          display: "flex",
          borderBottom: "1px solid #d6d2c2",
          background: "#ECE9D8",
          padding: "0 4px",
        }}
      >
        {[
          { id: "overview" as const, label: "Genel Bakış" },
          { id: "skills" as const, label: "Yetenekler" },
          { id: "events" as const, label: "Olaylar" },
          { id: "create" as const, label: "Yeni Skill" },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={tabStyle(tab === t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-auto p-3">
        {tab === "overview" && <OverviewTab />}
        {tab === "skills" && <SkillsTab />}
        {tab === "events" && <EventsTab />}
        {tab === "create" && <CreateSkillTab />}
      </div>
    </div>
  );
}

export default WorkspacePanel;

// ── Overview Tab ──────────────────────────────────────────────────

function OverviewTab() {
  const [stats, setStats] = useState<WorkspaceStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    workspaceApi
      .getStats()
      .then(setStats)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p style={{ color: "#666" }}>Yükleniyor...</p>;
  if (error) return <p style={{ color: "#c00" }}>{error}</p>;
  if (!stats) return <p style={{ color: "#666" }}>Veri yok</p>;

  const agents = Object.entries(stats.agents);

  return (
    <div>
      <div
        style={{
          background: "#f0f0e8",
          border: "1px solid #d6d2c2",
          borderRadius: 4,
          padding: "10px 14px",
          marginBottom: 12,
        }}
      >
        <span style={{ fontWeight: 600 }}>Toplam Skill: </span>
        <span style={{ color: "#6366f1", fontWeight: 700, fontSize: 16 }}>
          {stats.total_skills}
        </span>
        <span style={{ marginLeft: 16, fontWeight: 600 }}>Aktif Agent: </span>
        <span style={{ color: "#10b981", fontWeight: 700, fontSize: 16 }}>
          {agents.length}
        </span>
      </div>

      {agents.length === 0 ? (
        <p style={{ color: "#888" }}>
          Henüz workspace oluşturulmamış. Agent&apos;lar skill oluşturdukça
          burada görünecek.
        </p>
      ) : (
        <table
          style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}
        >
          <thead>
            <tr
              style={{
                background: "#ECE9D8",
                borderBottom: "1px solid #d6d2c2",
              }}
            >
              <th style={{ textAlign: "left", padding: "6px 8px" }}>Agent</th>
              <th style={{ textAlign: "center", padding: "6px 8px" }}>
                Skill Sayısı
              </th>
              <th style={{ textAlign: "right", padding: "6px 8px" }}>
                Son Aktivite
              </th>
            </tr>
          </thead>
          <tbody>
            {agents.map(([role, info]) => (
              <tr key={role} style={{ borderBottom: "1px solid #eee" }}>
                <td style={{ padding: "6px 8px", fontWeight: 600 }}>{role}</td>
                <td style={{ padding: "6px 8px", textAlign: "center" }}>
                  {info.skill_count}
                </td>
                <td
                  style={{
                    padding: "6px 8px",
                    textAlign: "right",
                    color: "#888",
                    fontSize: 10,
                  }}
                >
                  {info.last_active
                    ? new Date(info.last_active).toLocaleString("tr-TR")
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

// ── Skills Tab ───────────────────────────────────────────────────

function SkillsTab() {
  const [allSkills, setAllSkills] = useState<Record<string, SkillInfo[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [runResult, setRunResult] = useState<{
    success: boolean;
    stdout: string;
    stderr: string;
  } | null>(null);
  const [running, setRunning] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    workspaceApi
      .getAllSkills()
      .then((data) => setAllSkills(data as Record<string, SkillInfo[]>))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleRun = async (
    agentRole: string,
    skillName: string,
    scriptName: string,
  ) => {
    setRunning(`${agentRole}/${skillName}/${scriptName}`);
    setRunResult(null);
    try {
      const res = await workspaceApi.runScript({
        agent_role: agentRole,
        skill_name: skillName,
        script_name: scriptName,
      });
      setRunResult(res);
    } catch (e: unknown) {
      setRunResult({
        success: false,
        stdout: "",
        stderr: (e as Error).message,
      });
    } finally {
      setRunning("");
    }
  };

  if (loading) return <p style={{ color: "#666" }}>Yükleniyor...</p>;
  if (error) return <p style={{ color: "#c00" }}>{error}</p>;

  const entries = Object.entries(allSkills).filter(
    ([, skills]) => skills.length > 0,
  );

  if (entries.length === 0) {
    return (
      <p style={{ color: "#888" }}>
        Henüz skill oluşturulmamış. &quot;Yeni Skill&quot; sekmesinden
        oluşturabilirsiniz.
      </p>
    );
  }

  return (
    <div>
      {entries.map(([agent, skills]) => (
        <div key={agent} style={{ marginBottom: 16 }}>
          <div
            style={{
              fontWeight: 700,
              fontSize: 12,
              color: "#6366f1",
              marginBottom: 6,
              textTransform: "capitalize",
            }}
          >
            {agent === "_shared" ? "Paylaşılan" : agent}
          </div>
          {skills.map((skill) => (
            <div
              key={skill.name}
              style={{
                background: "#fafaf5",
                border: "1px solid #e5e2d6",
                borderRadius: 4,
                padding: "8px 10px",
                marginBottom: 6,
              }}
            >
              <div style={{ fontWeight: 600, marginBottom: 2 }}>
                {skill.name}
              </div>
              {skill.description && (
                <div style={{ color: "#666", fontSize: 10, marginBottom: 4 }}>
                  {skill.description}
                </div>
              )}
              {skill.scripts.length > 0 && (
                <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                  {skill.scripts.map((s) => (
                    <button
                      key={s}
                      onClick={() => handleRun(agent, skill.name, s)}
                      disabled={running !== ""}
                      style={{
                        fontSize: 10,
                        padding: "2px 8px",
                        background: "#ECE9D8",
                        border: "1px solid #d6d2c2",
                        borderRadius: 3,
                        cursor: "pointer",
                      }}
                    >
                      ▶ {s}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      ))}

      {runResult && (
        <div
          style={{
            marginTop: 12,
            padding: 10,
            borderRadius: 4,
            background: runResult.success ? "#f0fdf4" : "#fef2f2",
            border: `1px solid ${runResult.success ? "#86efac" : "#fca5a5"}`,
          }}
        >
          <div style={{ fontWeight: 600, fontSize: 11, marginBottom: 4 }}>
            {runResult.success ? "✓ Başarılı" : "✗ Hata"}
          </div>
          {runResult.stdout && (
            <pre
              style={{
                fontSize: 10,
                whiteSpace: "pre-wrap",
                margin: 0,
                maxHeight: 150,
                overflow: "auto",
              }}
            >
              {runResult.stdout}
            </pre>
          )}
          {runResult.stderr && (
            <pre
              style={{
                fontSize: 10,
                whiteSpace: "pre-wrap",
                margin: 0,
                color: "#c00",
                maxHeight: 100,
                overflow: "auto",
              }}
            >
              {runResult.stderr}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}

// ── Events Tab ───────────────────────────────────────────────────

function EventsTab() {
  const [events, setEvents] = useState<EventInfo[]>([]);
  const [stats, setStats] = useState<{
    total_active: number;
    immediate_queued: number;
    by_agent: Record<string, number>;
    by_type: Record<string, number>;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("");

  // Create event form
  const [showCreate, setShowCreate] = useState(false);
  const [evtType, setEvtType] = useState("immediate");
  const [evtAgent, setEvtAgent] = useState("orchestrator");
  const [evtMsg, setEvtMsg] = useState("");
  const [evtSchedule, setEvtSchedule] = useState("");
  const [creating, setCreating] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([
      workspaceApi.listEvents(filter || undefined),
      workspaceApi.getEventStats(),
    ])
      .then(([evts, st]) => {
        setEvents(evts);
        setStats(st);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [filter]);

  useEffect(() => {
    load();
  }, [load]);

  const handleDelete = async (id: string) => {
    try {
      await workspaceApi.deleteEvent(id);
      load();
    } catch (e: unknown) {
      setError((e as Error).message);
    }
  };

  const handleCreate = async () => {
    if (!evtMsg.trim()) return;
    setCreating(true);
    try {
      await workspaceApi.createEvent({
        event_type: evtType,
        target_agent: evtAgent,
        message: evtMsg,
        schedule: evtType === "periodic" ? evtSchedule : undefined,
      });
      setEvtMsg("");
      setShowCreate(false);
      load();
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setCreating(false);
    }
  };

  if (loading) return <p style={{ color: "#666" }}>Yükleniyor...</p>;
  if (error) return <p style={{ color: "#c00" }}>{error}</p>;

  return (
    <div>
      {stats && (
        <div
          style={{
            display: "flex",
            gap: 16,
            marginBottom: 12,
            background: "#f0f0e8",
            border: "1px solid #d6d2c2",
            borderRadius: 4,
            padding: "8px 12px",
          }}
        >
          <span>
            <b>Aktif:</b> {stats.total_active}
          </span>
          <span>
            <b>Kuyrukta:</b> {stats.immediate_queued}
          </span>
        </div>
      )}

      <div
        style={{
          display: "flex",
          gap: 8,
          marginBottom: 10,
          alignItems: "center",
        }}
      >
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          style={{
            fontSize: 11,
            padding: "3px 6px",
            border: "1px solid #d6d2c2",
            borderRadius: 3,
          }}
        >
          <option value="">Tüm Agent&apos;lar</option>
          {AGENT_ROLES.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
        <button
          onClick={() => setShowCreate(!showCreate)}
          style={{
            fontSize: 11,
            padding: "3px 10px",
            background: "#6366f1",
            color: "#fff",
            border: "none",
            borderRadius: 3,
            cursor: "pointer",
          }}
        >
          + Yeni Olay
        </button>
      </div>

      {showCreate && (
        <div
          style={{
            background: "#fafaf5",
            border: "1px solid #e5e2d6",
            borderRadius: 4,
            padding: 10,
            marginBottom: 12,
          }}
        >
          <div style={{ display: "flex", gap: 8, marginBottom: 6 }}>
            <select
              value={evtType}
              onChange={(e) => setEvtType(e.target.value)}
              style={{ fontSize: 11, padding: "2px 4px" }}
            >
              <option value="immediate">Anlık</option>
              <option value="one-shot">Tek Seferlik</option>
              <option value="periodic">Periyodik</option>
            </select>
            <select
              value={evtAgent}
              onChange={(e) => setEvtAgent(e.target.value)}
              style={{ fontSize: 11, padding: "2px 4px" }}
            >
              {AGENT_ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </div>
          <textarea
            value={evtMsg}
            onChange={(e) => setEvtMsg(e.target.value)}
            placeholder="Olay mesajı..."
            rows={2}
            style={{
              width: "100%",
              fontSize: 11,
              padding: 6,
              border: "1px solid #d6d2c2",
              borderRadius: 3,
              resize: "vertical",
            }}
          />
          {evtType === "periodic" && (
            <input
              value={evtSchedule}
              onChange={(e) => setEvtSchedule(e.target.value)}
              placeholder="Cron ifadesi (ör: */5 * * * *)"
              style={{
                width: "100%",
                fontSize: 11,
                padding: 4,
                marginTop: 4,
                border: "1px solid #d6d2c2",
                borderRadius: 3,
              }}
            />
          )}
          <button
            onClick={handleCreate}
            disabled={creating || !evtMsg.trim()}
            style={{
              marginTop: 6,
              fontSize: 11,
              padding: "4px 14px",
              background: "#10b981",
              color: "#fff",
              border: "none",
              borderRadius: 3,
              cursor: "pointer",
            }}
          >
            {creating ? "Oluşturuluyor..." : "Oluştur"}
          </button>
        </div>
      )}

      {events.length === 0 ? (
        <p style={{ color: "#888" }}>Aktif olay yok.</p>
      ) : (
        events.map((evt) => (
          <div
            key={evt.id}
            style={{
              background: "#fafaf5",
              border: "1px solid #e5e2d6",
              borderRadius: 4,
              padding: "8px 10px",
              marginBottom: 6,
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div>
                <span
                  style={{
                    fontSize: 9,
                    padding: "1px 6px",
                    borderRadius: 3,
                    marginRight: 6,
                    background:
                      evt.event_type === "immediate"
                        ? "#dbeafe"
                        : evt.event_type === "periodic"
                          ? "#fef3c7"
                          : "#e0e7ff",
                    color:
                      evt.event_type === "immediate"
                        ? "#1d4ed8"
                        : evt.event_type === "periodic"
                          ? "#92400e"
                          : "#4338ca",
                  }}
                >
                  {evt.event_type}
                </span>
                <span style={{ fontWeight: 600, fontSize: 11 }}>
                  {evt.target_agent}
                </span>
              </div>
              <button
                onClick={() => handleDelete(evt.id)}
                style={{
                  fontSize: 10,
                  color: "#c00",
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                }}
              >
                ✕
              </button>
            </div>
            <div style={{ fontSize: 11, color: "#444", marginTop: 4 }}>
              {evt.message}
            </div>
            {evt.schedule && (
              <div style={{ fontSize: 9, color: "#888", marginTop: 2 }}>
                Cron: {evt.schedule}
              </div>
            )}
            <div style={{ fontSize: 9, color: "#aaa", marginTop: 2 }}>
              {new Date(evt.created_at).toLocaleString("tr-TR")}
            </div>
          </div>
        ))
      )}
    </div>
  );
}

// ── Create Skill Tab ─────────────────────────────────────────────

function CreateSkillTab() {
  const [agent, setAgent] = useState("orchestrator");
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [usage, setUsage] = useState("");
  const [scriptName, setScriptName] = useState("main.py");
  const [scriptCode, setScriptCode] = useState("");
  const [creating, setCreating] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(
    null,
  );

  const handleCreate = async () => {
    if (!name.trim() || !desc.trim()) return;
    setCreating(true);
    setResult(null);
    try {
      const scripts: Record<string, string> = {};
      if (scriptName.trim() && scriptCode.trim()) {
        scripts[scriptName.trim()] = scriptCode;
      }
      await workspaceApi.createSkill({
        agent_role: agent,
        skill_name: name,
        description: desc,
        usage_instructions: usage,
        scripts,
      });
      setResult({
        ok: true,
        msg: `"${name}" skill'i ${agent} workspace'ine oluşturuldu.`,
      });
      setName("");
      setDesc("");
      setUsage("");
      setScriptCode("");
    } catch (e: unknown) {
      setResult({ ok: false, msg: (e as Error).message });
    } finally {
      setCreating(false);
    }
  };

  const inputStyle = {
    width: "100%",
    fontSize: 11,
    padding: "4px 6px",
    border: "1px solid #d6d2c2",
    borderRadius: 3,
  };

  return (
    <div>
      <div style={{ marginBottom: 8 }}>
        <label
          style={{
            fontSize: 10,
            color: "#666",
            display: "block",
            marginBottom: 2,
          }}
        >
          Agent
        </label>
        <select
          value={agent}
          onChange={(e) => setAgent(e.target.value)}
          style={{ ...inputStyle }}
        >
          {AGENT_ROLES.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
      </div>
      <div style={{ marginBottom: 8 }}>
        <label
          style={{
            fontSize: 10,
            color: "#666",
            display: "block",
            marginBottom: 2,
          }}
        >
          Skill Adı
        </label>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="data-analyzer"
          style={inputStyle}
        />
      </div>
      <div style={{ marginBottom: 8 }}>
        <label
          style={{
            fontSize: 10,
            color: "#666",
            display: "block",
            marginBottom: 2,
          }}
        >
          Açıklama
        </label>
        <input
          value={desc}
          onChange={(e) => setDesc(e.target.value)}
          placeholder="Veri analizi yapan skill"
          style={inputStyle}
        />
      </div>
      <div style={{ marginBottom: 8 }}>
        <label
          style={{
            fontSize: 10,
            color: "#666",
            display: "block",
            marginBottom: 2,
          }}
        >
          Kullanım Talimatları (opsiyonel)
        </label>
        <textarea
          value={usage}
          onChange={(e) => setUsage(e.target.value)}
          rows={2}
          placeholder="Bu skill şu şekilde kullanılır..."
          style={{ ...inputStyle, resize: "vertical" }}
        />
      </div>
      <div style={{ marginBottom: 8 }}>
        <label
          style={{
            fontSize: 10,
            color: "#666",
            display: "block",
            marginBottom: 2,
          }}
        >
          Script Dosya Adı
        </label>
        <input
          value={scriptName}
          onChange={(e) => setScriptName(e.target.value)}
          style={inputStyle}
        />
      </div>
      <div style={{ marginBottom: 8 }}>
        <label
          style={{
            fontSize: 10,
            color: "#666",
            display: "block",
            marginBottom: 2,
          }}
        >
          Script Kodu (opsiyonel)
        </label>
        <textarea
          value={scriptCode}
          onChange={(e) => setScriptCode(e.target.value)}
          rows={6}
          placeholder="#!/usr/bin/env python3&#10;print('Hello from skill')"
          style={{
            ...inputStyle,
            fontFamily: "Consolas, monospace",
            resize: "vertical",
          }}
        />
      </div>
      <button
        onClick={handleCreate}
        disabled={creating || !name.trim() || !desc.trim()}
        style={{
          fontSize: 11,
          padding: "6px 18px",
          background: "#6366f1",
          color: "#fff",
          border: "none",
          borderRadius: 3,
          cursor: "pointer",
          opacity: creating ? 0.6 : 1,
        }}
      >
        {creating ? "Oluşturuluyor..." : "Skill Oluştur"}
      </button>

      {result && (
        <div
          style={{
            marginTop: 10,
            padding: 8,
            borderRadius: 4,
            fontSize: 11,
            background: result.ok ? "#f0fdf4" : "#fef2f2",
            border: `1px solid ${result.ok ? "#86efac" : "#fca5a5"}`,
            color: result.ok ? "#166534" : "#991b1b",
          }}
        >
          {result.msg}
        </div>
      )}
    </div>
  );
}
