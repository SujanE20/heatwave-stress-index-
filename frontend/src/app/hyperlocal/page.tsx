"use client";

import { useMemo, useState } from "react";
import { Info, Layers, MapPin, ShieldAlert, Snowflake, Users } from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import type { HyperlocalMap as HyperlocalMapData, RiskKey } from "@/lib/types";
import { RISK_META, RISK_ORDER, riskMeta } from "@/lib/utils";
import HyperlocalMap from "@/components/HyperlocalMap";
import ZonePanel from "@/components/ZonePanel";
import { Button, ErrorState, Select, Spinner } from "@/components/ui";

const POCKET_TIPS = [
  {
    icon: MapPin,
    title: "Pockets, not just wards",
    text: "Every ward is split into a core and six side blocks — 105 pockets across Mysore.",
  },
  {
    icon: Users,
    title: "Same heat, different people",
    text: "Air temperature is city-wide. Pocket colours show exposure: crowds, shade, housing, elderly presence, shelter distance.",
  },
  {
    icon: Snowflake,
    title: "Shelter-aware",
    text: "Each pocket knows its nearest cooling centre and water point, so action can be street-local.",
  },
];

const NAV_H = 58; // sticky top navigation height (desktop)
const BAR_H = 44; // disclaimer bar height

export default function HyperlocalPage() {
  const { data, loading, error, refresh } = useApi<HyperlocalMapData>(() => api.hyperlocal());
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [focusWard, setFocusWard] = useState<string>("all");

  const zoneCounts = useMemo(() => {
    const counts: Record<RiskKey, number> = { green: 0, yellow: 0, orange: 0, red: 0, maroon: 0 };
    for (const z of data?.zones ?? []) counts[z.level] += 1;
    return counts;
  }, [data]);

  if (loading) return <Spinner label="Computing hyperlocal pockets…" />;
  if (error || !data) return <ErrorState message={error || "No data"} onRetry={refresh} />;

  const selected = data.zones.find((z) => z.id === selectedId) ?? null;
  const center: [number, number] = [data.city.lat, data.city.lon];

  return (
    <main className="flex w-full flex-col bg-slate-100">
      {/* full-bleed map area */}
      <div className="relative w-full overflow-hidden" style={{ height: `calc(100dvh - ${NAV_H + BAR_H}px)` }}>
        <div className="absolute inset-0">
          <HyperlocalMap
            zones={data.zones}
            outlines={data.wards}
            selectedId={selectedId}
            onSelect={setSelectedId}
            focusWard={focusWard === "all" ? null : focusWard}
            center={center}
          />
        </div>

        {/* floating overlay UI */}
        <div className="pointer-events-none absolute inset-x-3 top-3 z-[1000] flex flex-wrap items-start justify-between gap-2 sm:inset-x-4 sm:top-4">
          {/* header + focus card */}
          <div className="pointer-events-auto w-[min(340px,calc(100vw-24px))] rounded-2xl border border-slate-200/80 bg-white/90 p-3 shadow-xl shadow-slate-900/10 backdrop-blur-md">
            <div className="flex items-center gap-2.5">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-orange-500 to-red-600 shadow-md">
                <MapPin className="h-5 w-5 text-white" />
              </span>
              <div className="leading-tight">
                <p className="text-[10px] font-bold uppercase tracking-widest text-orange-600">HeatShield India</p>
                <h1 className="text-sm font-extrabold text-slate-900">Hyperlocal Risk Map · {data.city.name}</h1>
              </div>
            </div>

            <p className="mt-2 text-[10px] leading-snug text-slate-500">
              {data.zones.length} sub-ward pockets across {data.wards.length} wards — zone polygons are demonstration
              subdivisions of the demo ward boundaries.
            </p>

            <div className="mt-2 flex flex-wrap items-center gap-1.5">
              {RISK_ORDER.filter((k) => zoneCounts[k] > 0).map((k) => (
                <span
                  key={k}
                  className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-bold"
                  style={{ backgroundColor: `${RISK_META[k].color}1a`, color: RISK_META[k].text }}
                >
                  <span className="h-2 w-2 rounded-full" style={{ backgroundColor: RISK_META[k].color }} />
                  {zoneCounts[k]} {RISK_META[k].label}
                </span>
              ))}
            </div>

            <div className="mt-2.5 flex items-center gap-2 border-t border-slate-100 pt-2.5">
              <span className="flex shrink-0 items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                <Layers className="h-3 w-3" /> Focus
              </span>
              <div className="min-w-0 flex-1">
                <Select
                  value={focusWard}
                  onChange={(v) => {
                    setFocusWard(v);
                    if (v === "all") setSelectedId(null);
                  }}
                  label="Focus ward"
                >
                  <option value="all">Whole city (all wards)</option>
                  {data.wards.map((w) => (
                    <option key={w.code} value={w.code}>
                      {w.code} · {w.name}
                    </option>
                  ))}
                </Select>
              </div>
              {focusWard !== "all" && (
                <Button
                  variant="outline"
                  size="sm"
                  className="shrink-0"
                  onClick={() => {
                    setFocusWard("all");
                    setSelectedId(null);
                  }}
                >
                  All
                </Button>
              )}
            </div>
          </div>

          {/* detail panel / hint */}
          <div className="pointer-events-auto w-[min(370px,calc(100vw-24px))]">
            {selected ? (
              <ZonePanel zone={selected} onClose={() => setSelectedId(null)} />
            ) : (
              <div className="rounded-2xl border border-slate-200/80 bg-white/90 p-3.5 shadow-xl shadow-slate-900/10 backdrop-blur-md">
                <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-widest text-slate-400">
                  <Info className="h-3 w-3 text-orange-500" /> How to read this map
                </div>
                <div className="mt-2 space-y-2">
                  {POCKET_TIPS.map((t) => (
                    <div key={t.title} className="flex items-start gap-2">
                      <t.icon className="mt-0.5 h-3.5 w-3.5 shrink-0 text-orange-500" />
                      <p className="text-[11px] leading-snug text-slate-600">
                        <b className="text-slate-800">{t.title}:</b> {t.text}
                      </p>
                    </div>
                  ))}
                </div>
                <p
                  className="mt-2.5 rounded-lg px-2 py-1.5 text-[10px] font-medium text-orange-800"
                  style={{ backgroundColor: "#f9731614" }}
                >
                  Click any pocket on the map to inspect its hyperlocal heat-health profile.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* slim disclaimer bar */}
      <footer className="flex items-center gap-2 overflow-hidden border-t border-amber-200/80 bg-amber-50/95 px-3 sm:px-4"
        style={{ height: BAR_H }}>
        <ShieldAlert className="h-3.5 w-3.5 shrink-0 text-amber-700" />
        <p className="truncate text-[10px] leading-tight text-amber-900">
          <b>Decision-support prototype</b> — heat-stress and health-risk estimates must be calibrated with local
          meteorological and public-health data before operational use. No individual health data is displayed.
        </p>
        <span className="ml-auto hidden shrink-0 items-center gap-1 rounded-full bg-white/80 px-2 py-0.5 text-[10px] font-semibold text-slate-500 ring-1 ring-amber-200 sm:flex">
          {riskMeta(selected?.level ?? "orange").label} selection · {data.city.name} · demo mode
        </span>
      </footer>
    </main>
  );
}
