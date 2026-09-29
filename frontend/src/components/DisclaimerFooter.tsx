"use client";

import { ShieldAlert } from "lucide-react";

const BASE = [
  "HeatShield is a decision-support prototype. Heat-stress and health-risk estimates must be calibrated and validated using local meteorological and public-health data before operational deployment.",
  "Estimated WBGT is not a replacement for a calibrated onsite WBGT instrument.",
  "UTCI Proxy is not official UTCI if a validated UTCI implementation is not used.",
  "No individual health data must be publicly displayed — only ward-level aggregated estimates.",
];

export default function DisclaimerFooter({ extra = [] }: { extra?: string[] }) {
  const items: string[] = [];
  for (const d of [...BASE, ...extra]) {
    if (!items.includes(d)) items.push(d);
  }
  return (
    <footer className="mt-10 rounded-xl border border-amber-200 bg-amber-50 p-4">
      <div className="flex items-start gap-3">
        <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-amber-700" />
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-amber-800">Important disclaimer</p>
          <ul className="mt-1.5 space-y-1 text-[11px] leading-relaxed text-amber-900">
            {items.map((d, i) => (
              <li key={i}>{d}</li>
            ))}
          </ul>
        </div>
      </div>
    </footer>
  );
}