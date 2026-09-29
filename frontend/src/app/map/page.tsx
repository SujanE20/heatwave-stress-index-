"use client";

import { useState } from "react";
import { Layers } from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import type { WardLite } from "@/lib/types";
import RiskMap, { LAYERS, type LayerKey, type PointItem } from "@/components/RiskMap";
import WardPanel from "@/components/WardPanel";
import DisclaimerFooter from "@/components/DisclaimerFooter";
import { ErrorState, Spinner, Switch } from "@/components/ui";

export default function MapPage() {
  const { data: wards, loading, error, refresh } = useApi<WardLite[]>(() => api.wards(true));
  const { data: trends } = useApi(() => api.trends());
  const { data: summary } = useApi(() => api.dashboard());
  const { data: hospitals } = useApi<PointItem[]>(async () => {
    const hs = await api.hospitals();
    return hs.map((h) => ({ id: h.id, name: h.name, lat: h.lat, lon: h.lon }));
  });
  const { data: cooling } = useApi<PointItem[]>(async () => {
    const cs = await api.coolingCentres();
    return cs.map((c) => ({ id: c.id, name: c.name, lat: c.lat, lon: c.lon }));
  });
  const { data: water } = useApi<PointItem[]>(async () => {
    const ws = await api.waterPoints();
    return ws.map((p) => ({ id: p.id, name: p.name, lat: p.lat, lon: p.lon }));
  });

  const [active, setActive] = useState<Set<LayerKey>>(new Set<LayerKey>(["combined"]));
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const toggle = (key: LayerKey) => {
    setActive((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  if (loading) return <Spinner label="Loading ward geometries…" />;
  if (error || !wards) return <ErrorState message={error || "No data"} onRetry={refresh} />;

  const compareById = new Map((trends?.ward_comparison ?? []).map((c) => [c.id, c]));
  const mapWards = wards.map((w) => {
    const c = compareById.get(w.id);
    return {
      id: w.id, code: w.code, name: w.name,
      level: w.risk?.level ?? c?.risk_level ?? "green",
      label: w.risk?.label ?? c?.risk_label ?? "Low",
      score: w.risk?.score ?? c?.risk_score ?? 0,
      htsi: c?.htsi ?? 0, vulnerability: c?.vulnerability ?? 0,
      population: w.population,
      centroid_lat: w.centroid_lat, centroid_lon: w.centroid_lon,
      geojson: w.geojson,
    };
  });

  // centre the map on the configured demo city (from the API, not hardcoded)
  const center: [number, number] = summary
    ? [summary.city.lat, summary.city.lon]
    : [12.2958, 76.6394];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-bold text-slate-900">Interactive GIS Risk Map — {summary?.city.name ?? "Mysore"}</h1>
        <span className="text-xs text-slate-500">
          15 demonstration wards · boundaries are demo polygons, replaceable with official municipal GIS data
        </span>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_400px]">
        <div className="relative h-[70vh] overflow-hidden rounded-xl border border-slate-200">
          <div className="absolute left-3 top-3 z-[500] rounded-lg border border-slate-200 bg-white/95 p-2.5 shadow-md">
            <p className="mb-1.5 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wide text-slate-500">
              <Layers className="h-3 w-3" /> Layers
            </p>
            <div className="space-y-1.5">
              {LAYERS.map((l) => (
                <Switch
                  key={l.key}
                  checked={active.has(l.key)}
                  onChange={() => toggle(l.key)}
                  label={l.label}
                />
              ))}
            </div>
          </div>
          <RiskMap
            wards={mapWards}
            hospitals={hospitals || []}
            cooling={cooling || []}
            water={water || []}
            activeLayers={Array.from(active)}
            selectedId={selectedId}
            onSelect={setSelectedId}
            center={center}
          />
        </div>

        <div>
          <WardPanel wardId={selectedId} />
        </div>
      </div>

      <p className="text-[11px] text-slate-400">
        Colour never carries the message alone — every ward shows a labelled risk badge and opens a
        full explanation of why that risk level was assigned.
      </p>
      <DisclaimerFooter />
    </div>
  );
}