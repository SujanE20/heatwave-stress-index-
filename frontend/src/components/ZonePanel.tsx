"use client";

import { Link } from "react-router-dom";
import { ArrowRight, Droplets, Snowflake, Users, X } from "lucide-react";
import type { HyperlocalZone } from "@/lib/types";
import { fmt, fmtInt, riskMeta } from "@/lib/utils";
import RiskBadge from "./RiskBadge";
import { Progress, Separator } from "./ui";

function Row({ label, value, unit, accent }: { label: string; value: string | number; unit?: string; accent?: string }) {
  return (
    <div className="flex items-center justify-between gap-2 py-1">
      <span className="text-xs text-slate-500">{label}</span>
      <span className="text-xs font-bold" style={{ color: accent }}>
        {value}
        {unit && <span className="ml-0.5 font-medium text-slate-400">{unit}</span>}
      </span>
    </div>
  );
}

export default function ZonePanel({ zone, onClose }: { zone: HyperlocalZone | null; onClose?: () => void }) {
  if (!zone) return null;

  const e = zone.exposure;
  const meta = riskMeta(zone.level);
  const contributors = Object.entries(e.contributions).sort((a, b) => b[1] - a[1]);

  return (
    <div className="flex max-h-[calc(100dvh-58px-44px-28px)] w-full flex-col overflow-hidden rounded-2xl border border-slate-200/90 bg-white/95 shadow-2xl shadow-slate-900/15 backdrop-blur-md">
      {/* header */}
      <div
        className="relative shrink-0 px-3.5 pb-2.5 pt-3 text-white"
        style={{ background: "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)" }}
      >
        <button
          type="button"
          aria-label="Close pocket details"
          onClick={onClose}
          className="absolute right-2.5 top-2.5 rounded-md p-1 text-slate-400 transition-colors hover:bg-white/10 hover:text-white"
        >
          <X className="h-3.5 w-3.5" />
        </button>
        <p className="text-[9px] font-bold uppercase tracking-widest text-slate-400">
          {zone.id} · Ward {zone.ward_code}
        </p>
        <div className="mt-0.5 flex items-center justify-between gap-2 pr-6">
          <div className="min-w-0">
            <h3 className="truncate text-sm font-extrabold leading-tight">{zone.name}</h3>
            <p className="truncate text-[10px] text-slate-300">{zone.kind}</p>
          </div>
          <RiskBadge level={zone.level} size="sm" />
        </div>
        {/* accent bar in the pocket's risk colour */}
        <div className="absolute inset-x-0 bottom-0 h-[3px]" style={{ backgroundColor: meta.color }} />
      </div>

      {/* body */}
      <div className="scroll-thin space-y-3 overflow-y-auto p-3.5">
        {/* quick stats */}
        <div className="grid grid-cols-3 gap-1.5 text-center">
          {[
            { label: "Zone risk", value: Math.round(zone.score), color: meta.text },
            { label: "Ward risk", value: Math.round(zone.ward_score), color: "#0f172a" },
            { label: "People", value: fmtInt(zone.population), color: "#0f172a" },
          ].map((s) => (
            <div key={s.label} className="rounded-xl bg-slate-50 px-1 py-1.5 ring-1 ring-slate-100">
              <p className="text-sm font-extrabold" style={{ color: s.color }}>{s.value}</p>
              <p className="text-[9px] font-semibold uppercase tracking-wide text-slate-400">{s.label}</p>
            </div>
          ))}
        </div>

        <p className="rounded-xl border border-slate-100 bg-slate-50 p-2.5 text-[11px] leading-relaxed text-slate-600">
          {zone.explanation}
        </p>

        <div>
          <p className="mb-1 text-[10px] font-bold uppercase tracking-wide text-slate-400">Heat vs exposure</p>
          <div className="grid grid-cols-2 gap-x-3 rounded-xl border border-slate-100 px-2.5 py-1">
            <Row label="City heat (HTSI)" value={fmt(zone.htsi)} unit="/100" />
            <Row label="Pocket exposure" value={fmt(e.score)} unit="/100" accent="#7c3aed" />
          </div>
          <Separator className="my-1.5" />
          <p className="mb-2 text-[10px] font-bold uppercase tracking-wide text-slate-400">
            Why this pocket stands out
          </p>
          <div className="space-y-2">
            {contributors.map(([k, val]) => (
              <div key={k}>
                <div className="flex justify-between text-[11px] text-slate-500">
                  <span className="flex items-center gap-1.5">
                    <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: val >= 10 ? meta.color : "#cbd5e1" }} />
                    {e.labels[k]}
                  </span>
                  <span className="font-semibold text-slate-700">+{fmt(val)}</span>
                </div>
                <Progress value={(val / (e.weights[k] * 100)) * 100} color={val >= 10 ? meta.color : "#94a3b8"} />
              </div>
            ))}
          </div>
          {zone.escalations.length > 0 && (
            <p className="mt-2.5 rounded-lg bg-amber-50 px-2 py-1.5 text-[10px] font-medium text-amber-800 ring-1 ring-amber-200">
              {zone.escalations.join(" · ")}
            </p>
          )}
        </div>

        <div>
          <p className="mb-1.5 text-[10px] font-bold uppercase tracking-wide text-slate-400">Nearest shelter resources</p>
          <div className="space-y-1.5 rounded-xl border border-slate-100 p-2 text-xs">
            <div className="flex items-center justify-between gap-2">
              <span className="flex min-w-0 items-center gap-1.5 text-slate-600">
                <Snowflake className="h-3.5 w-3.5 shrink-0 text-sky-600" />
                <span className="truncate">{e.nearest.cooling_centre.name}</span>
              </span>
              <span className="shrink-0 font-bold text-slate-700">{e.nearest.cooling_centre.distance_km} km</span>
            </div>
            <div className="flex items-center justify-between gap-2">
              <span className="flex min-w-0 items-center gap-1.5 text-slate-600">
                <Droplets className="h-3.5 w-3.5 shrink-0 text-cyan-600" />
                <span className="truncate">{e.nearest.water_point.name}</span>
              </span>
              <span className="shrink-0 font-bold text-slate-700">{e.nearest.water_point.distance_km} km</span>
            </div>
          </div>
        </div>

        <Link
          to={`/ward/${zone.ward_id}`}
          className="flex items-center justify-center gap-1.5 rounded-xl bg-slate-900 py-2 text-xs font-semibold text-white transition-colors hover:bg-slate-700"
        >
          Open ward {zone.ward_code} details <ArrowRight className="h-3.5 w-3.5" />
        </Link>
        <p className="flex items-start gap-1.5 text-[9px] leading-snug text-slate-400">
          <Users className="mt-0.5 h-3 w-3 shrink-0" />
          Air temperature is city-wide in Mysore — the colour difference between pockets is exposure, not temperature.
        </p>
      </div>
    </div>
  );
}
