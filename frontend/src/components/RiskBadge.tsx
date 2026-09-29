"use client";

import { ShieldCheck, ShieldAlert, Shield, TriangleAlert, Skull } from "lucide-react";
import type { RiskKey } from "@/lib/types";
import { RISK_META, riskMeta, cn } from "@/lib/utils";

const ICONS: Record<RiskKey, any> = {
  green: ShieldCheck,
  yellow: Shield,
  orange: ShieldAlert,
  red: TriangleAlert,
  maroon: Skull,
};

export default function RiskBadge({
  level,
  label,
  size = "md",
  showLabel = true,
}: {
  level: RiskKey | string;
  label?: string;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
}) {
  const meta = riskMeta(level);
  const Icon = ICONS[(level as RiskKey) in ICONS ? (level as RiskKey) : "green"];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full font-semibold",
        size === "sm" && "px-2 py-0.5 text-[10px]",
        size === "md" && "px-2.5 py-1 text-xs",
        size === "lg" && "px-3.5 py-1.5 text-sm"
      )}
      style={{ backgroundColor: meta.bg, color: meta.text, border: `1px solid ${meta.color}66` }}
    >
      <Icon className={size === "sm" ? "h-3 w-3" : "h-4 w-4"} />
      {showLabel && (label ?? meta.label)}
      <span className="sr-only">Risk level {meta.label}</span>
    </span>
  );
}

export function RiskDot({ level, size = 10 }: { level: RiskKey | string; size?: number }) {
  return (
    <span
      aria-hidden
      className="inline-block rounded-full"
      style={{ width: size, height: size, backgroundColor: riskMeta(level).color }}
    />
  );
}

export function RiskPill({ score, level }: { score: number; level: RiskKey }) {
  const meta = RISK_META[level];
  return (
    <span className="inline-flex items-center gap-1.5">
      <RiskDot level={level} />
      <span className="text-xs font-semibold" style={{ color: meta.text }}>
        {meta.label} · {Math.round(score)}/100
      </span>
    </span>
  );
}