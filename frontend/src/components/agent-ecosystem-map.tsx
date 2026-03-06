"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { EcosystemData, EcosystemNode, EcosystemEdge } from "@/lib/types";

function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse bg-white/5 rounded ${className}`}
      aria-hidden
    />
  );
}

function InlineError({ message }: { message: string }) {
  return (
    <p className="text-xs text-red-400 py-2" role="alert">
      {message}
    </p>
  );
}

// Node positions in a pentagon layout
const NODE_POSITIONS: Record<string, { x: number; y: number }> = {
  orchestrator: { x: 250, y: 60 },
  thinker: { x: 430, y: 180 },
  speed: { x: 370, y: 360 },
  researcher: { x: 130, y: 360 },
  reasoner: { x: 70, y: 180 },
};

const NODE_RADIUS = 32;

interface TooltipInfo {
  node: EcosystemNode;
  x: number;
  y: number;
}

export function AgentEcosystemMap() {
  const [data, setData] = useState<EcosystemData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<TooltipInfo | null>(null);
  const [pulsePhase, setPulsePhase] = useState(0);
  const svgRef = useRef<SVGSVGElement>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.getAgentEcosystem();
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Yüklenemedi");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Pulse animation
  useEffect(() => {
    const interval = setInterval(() => {
      setPulsePhase((p) => (p + 1) % 360);
    }, 50);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <Skeleton className="h-[420px]" />;
  if (error) return <InlineError message={error} />;
  if (!data) return null;

  const maxWeight = Math.max(1, ...data.edges.map((e) => e.weight));

  const handleNodeHover = (node: EcosystemNode | null) => {
    if (node) {
      const pos = NODE_POSITIONS[node.role] ?? { x: 250, y: 200 };
      setHoveredNode(node.id);
      setTooltip({ node, x: pos.x, y: pos.y });
    } else {
      setHoveredNode(null);
      setTooltip(null);
    }
  };

  return (
    <div
      className="space-y-2"
      role="region"
      aria-label="Ajan Ekosistem Haritası"
    >
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold text-slate-300">
          🌐 Ajan Ekosistemi
        </h3>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-slate-500">
            {data.total_interactions} etkileşim
          </span>
          <button
            onClick={load}
            className="text-[10px] text-slate-500 hover:text-slate-300 transition-colors"
          >
            ↻
          </button>
        </div>
      </div>

      <div className="relative bg-white/[0.02] rounded-lg border border-border/50 overflow-hidden">
        <svg
          ref={svgRef}
          viewBox="0 0 500 420"
          className="w-full h-auto"
          role="img"
          aria-label="Ajan ilişki grafiği"
        >
          <defs>
            {/* Glow filter */}
            <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
            {/* Animated gradient for edges */}
            <linearGradient id="edgeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.3" />
              <stop offset="50%" stopColor="#8b5cf6" stopOpacity="0.6" />
              <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.3" />
            </linearGradient>
          </defs>

          {/* Background grid */}
          <pattern
            id="grid"
            width="20"
            height="20"
            patternUnits="userSpaceOnUse"
          >
            <path
              d="M 20 0 L 0 0 0 20"
              fill="none"
              stroke="#ffffff"
              strokeOpacity="0.02"
              strokeWidth="0.5"
            />
          </pattern>
          <rect width="500" height="420" fill="url(#grid)" />

          {/* Edges */}
          {data.edges.map((edge: EcosystemEdge) => {
            const src = NODE_POSITIONS[edge.source];
            const tgt = NODE_POSITIONS[edge.target];
            if (!src || !tgt) return null;

            const thickness = Math.max(1, (edge.weight / maxWeight) * 4);
            const isHighlighted =
              hoveredNode === edge.source || hoveredNode === edge.target;
            const opacity = hoveredNode ? (isHighlighted ? 0.8 : 0.15) : 0.4;

            // Midpoint for label
            const mx = (src.x + tgt.x) / 2;
            const my = (src.y + tgt.y) / 2;

            return (
              <g key={`${edge.source}-${edge.target}`}>
                <line
                  x1={src.x}
                  y1={src.y}
                  x2={tgt.x}
                  y2={tgt.y}
                  stroke={isHighlighted ? "#8b5cf6" : "#475569"}
                  strokeWidth={thickness}
                  strokeOpacity={opacity}
                  strokeLinecap="round"
                  className="transition-all duration-300"
                />
                {/* Animated particle on edge */}
                {isHighlighted && (
                  <circle r="3" fill="#8b5cf6" opacity="0.8">
                    <animateMotion
                      dur="2s"
                      repeatCount="indefinite"
                      path={`M${src.x},${src.y} L${tgt.x},${tgt.y}`}
                    />
                  </circle>
                )}
                {/* Weight label */}
                {edge.weight > 0 && (
                  <text
                    x={mx}
                    y={my - 6}
                    textAnchor="middle"
                    className="text-[9px] fill-slate-500"
                    opacity={hoveredNode ? (isHighlighted ? 1 : 0.2) : 0.6}
                  >
                    {edge.weight}
                  </text>
                )}
              </g>
            );
          })}

          {/* Nodes */}
          {data.nodes.map((node: EcosystemNode) => {
            const pos = NODE_POSITIONS[node.role];
            if (!pos) return null;

            const isHovered = hoveredNode === node.id;
            const isConnected =
              hoveredNode &&
              data.edges.some(
                (e) =>
                  (e.source === hoveredNode && e.target === node.id) ||
                  (e.target === hoveredNode && e.source === node.id),
              );
            const dimmed = hoveredNode && !isHovered && !isConnected;
            const scale = isHovered ? 1.15 : 1;
            const pulseR =
              node.status === "active"
                ? NODE_RADIUS + 4 + Math.sin((pulsePhase * Math.PI) / 180) * 3
                : 0;

            return (
              <g
                key={node.id}
                transform={`translate(${pos.x}, ${pos.y}) scale(${scale})`}
                className="transition-transform duration-200 cursor-pointer"
                onMouseEnter={() => handleNodeHover(node)}
                onMouseLeave={() => handleNodeHover(null)}
                onFocus={() => handleNodeHover(node)}
                onBlur={() => handleNodeHover(null)}
                tabIndex={0}
                role="button"
                aria-label={`${node.name}: ${node.total_tasks} görev, %${Math.round(node.success_rate)} başarı`}
              >
                {/* Pulse ring for active */}
                {node.status === "active" && (
                  <circle
                    r={pulseR}
                    fill="none"
                    stroke={node.color}
                    strokeWidth="1"
                    strokeOpacity="0.2"
                  />
                )}

                {/* Outer ring */}
                <circle
                  r={NODE_RADIUS + 2}
                  fill="none"
                  stroke={node.color}
                  strokeWidth={isHovered ? 2.5 : 1.5}
                  strokeOpacity={dimmed ? 0.2 : 0.6}
                  filter={isHovered ? "url(#glow)" : undefined}
                />

                {/* Node body */}
                <circle
                  r={NODE_RADIUS}
                  fill={`${node.color}15`}
                  stroke={node.color}
                  strokeWidth="0"
                  opacity={dimmed ? 0.3 : 1}
                />

                {/* Icon */}
                <text
                  textAnchor="middle"
                  dominantBaseline="central"
                  className="text-lg select-none pointer-events-none"
                  opacity={dimmed ? 0.3 : 1}
                >
                  {node.icon}
                </text>

                {/* Name label */}
                <text
                  y={NODE_RADIUS + 14}
                  textAnchor="middle"
                  className="text-[10px] font-medium select-none pointer-events-none"
                  fill={node.color}
                  opacity={dimmed ? 0.3 : 1}
                >
                  {node.name}
                </text>

                {/* Task count badge */}
                <g
                  transform={`translate(${NODE_RADIUS - 4}, ${-NODE_RADIUS + 4})`}
                >
                  <circle
                    r="9"
                    fill="#1e293b"
                    stroke={node.color}
                    strokeWidth="1"
                    opacity={dimmed ? 0.3 : 1}
                  />
                  <text
                    textAnchor="middle"
                    dominantBaseline="central"
                    className="text-[8px] font-bold select-none pointer-events-none"
                    fill={node.color}
                    opacity={dimmed ? 0.3 : 1}
                  >
                    {node.total_tasks}
                  </text>
                </g>

                {/* Status indicator */}
                <circle
                  cx={-NODE_RADIUS + 4}
                  cy={-NODE_RADIUS + 4}
                  r="4"
                  fill={node.status === "active" ? "#10b981" : "#6b7280"}
                  stroke="#0f172a"
                  strokeWidth="1.5"
                  opacity={dimmed ? 0.3 : 1}
                />
              </g>
            );
          })}
        </svg>

        {/* Tooltip */}
        {tooltip && (
          <div
            className="absolute z-10 bg-surface border border-border rounded-lg shadow-xl px-3 py-2 pointer-events-none"
            style={{
              left: `${(tooltip.x / 500) * 100}%`,
              top: `${(tooltip.y / 420) * 100 - 18}%`,
              transform: "translate(-50%, -100%)",
            }}
          >
            <div className="flex items-center gap-1.5 mb-1">
              <span>{tooltip.node.icon}</span>
              <span
                className="text-[11px] font-semibold"
                style={{ color: tooltip.node.color }}
              >
                {tooltip.node.name}
              </span>
            </div>
            <div className="text-[10px] text-slate-400 space-y-0.5">
              <div>Görev: {tooltip.node.total_tasks}</div>
              <div>Başarı: %{Math.round(tooltip.node.success_rate)}</div>
              <div>
                Durum:{" "}
                <span
                  className={
                    tooltip.node.status === "active"
                      ? "text-emerald-400"
                      : "text-slate-500"
                  }
                >
                  {tooltip.node.status === "active" ? "Aktif" : "Beklemede"}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-3 px-1">
        {data.nodes.map((node: EcosystemNode) => (
          <div key={node.id} className="flex items-center gap-1 text-[10px]">
            <span
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: node.color }}
            />
            <span className="text-slate-400">{node.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
