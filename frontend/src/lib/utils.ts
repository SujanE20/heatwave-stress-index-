import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { RiskKey } from "./types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const RISK_META: Record<RiskKey, { label: string; color: string; bg: string; border: string; text: string }> = {
  green: { label: "Low", color: "#16a34a", bg: "#dcfce7", border: "#16a34a", text: "#166534" },
  yellow: { label: "Moderate", color: "#eab308", bg: "#fef9c3", border: "#ca8a04", text: "#854d0e" },
  orange: { label: "High", color: "#f97316", bg: "#ffedd5", border: "#ea580c", text: "#9a3412" },
  red: { label: "Very High", color: "#dc2626", bg: "#fee2e2", border: "#dc2626", text: "#991b1b" },
  maroon: { label: "Extreme", color: "#7f1d1d", bg: "#fecaca", border: "#7f1d1d", text: "#450a0a" },
};

export const RISK_ORDER: RiskKey[] = ["green", "yellow", "orange", "red", "maroon"];

export function riskMeta(key: RiskKey | string): typeof RISK_META.green {
  return RISK_META[(key as RiskKey) in RISK_META ? (key as RiskKey) : "green"];
}

export function fmt(n: number | undefined | null, digits = 1): string {
  if (n === undefined || n === null || Number.isNaN(n)) return "—";
  return n.toFixed(digits);
}

export function fmtInt(n: number | undefined | null): string {
  if (n === undefined || n === null) return "—";
  return n.toLocaleString("en-IN");
}

export function fmtTime(iso: string | undefined | null): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
  } catch {
    return iso;
  }
}

export function fmtDate(iso: string | undefined | null): string {
  if (!iso) return "—";
  const d = new Date(iso + (iso.length === 10 ? "T00:00:00" : ""));
  return d.toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" });
}