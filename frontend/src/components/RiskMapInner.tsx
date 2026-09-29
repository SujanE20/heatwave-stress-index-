"use client";

// Leaflet map wrapped in next/dynamic (ssr:false) by the parent so it only
// loads in the browser — required because Leaflet touches `window`.
// Official Leaflet styles are mandatory: they position panes, tiles and
// controls. Without them the map renders as a broken pile of tiles.
import "leaflet/dist/leaflet.css";

import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import {
  CircleMarker, GeoJSON, LayerGroup, MapContainer, Popup, TileLayer, Tooltip as LTooltip, useMap,
} from "react-leaflet";
import { Hospital, MapPin, Snowflake, Droplets } from "lucide-react";
import type { RiskKey } from "@/lib/types";
import { RISK_META, riskMeta } from "@/lib/utils";
import RiskBadge from "./RiskBadge";

export interface MapWard {
  id: number;
  code: string;
  name: string;
  level: RiskKey;
  label: string;
  score: number;
  htsi: number;
  vulnerability: number;
  population: number;
  centroid_lat: number;
  centroid_lon: number;
  geojson?: any;
}

export type LayerKey =
  | "combined" | "thermal" | "vulnerability" | "hospitals" | "cooling" | "water" | "green";

export interface PointItem {
  id: number;
  name: string;
  lat: number;
  lon: number;
  extra?: string;
}

/**
 * Lat/Lng bounds covering every ward polygon. Lets us frame the whole city
 * regardless of screen size instead of trusting a fixed zoom level.
 */
function cityBounds(wards: MapWard[]): L.LatLngBounds | null {
  let minLat = Infinity,
    maxLat = -Infinity,
    minLon = Infinity,
    maxLon = -Infinity;
  for (const w of wards) {
    const ring = w.geojson?.geometry?.coordinates?.[0];
    if (!Array.isArray(ring)) continue;
    for (const c of ring) {
      const lon = c?.[0];
      const lat = c?.[1];
      if (typeof lon === "number" && typeof lat === "number") {
        minLat = Math.min(minLat, lat);
        maxLat = Math.max(maxLat, lat);
        minLon = Math.min(minLon, lon);
        maxLon = Math.max(maxLon, lon);
      }
    }
  }
  if (minLat === Infinity) return null;
  // `latLngBounds` expects (southWest, northEast) as [lat, lng] pairs.
  return L.latLngBounds([minLat, minLon], [maxLat, maxLon]);
}

/** Fits the viewport to the full set of wards so the whole city is visible. */
function AutoFit({ wards, center }: { wards: MapWard[]; center: [number, number] }) {
  const map = useMap();
  const fitted = useRef<string | null>(null);
  useEffect(() => {
    const bounds = cityBounds(wards);
    if (!bounds) {
      map.setView(center, 12);
      return;
    }
    // fit once per data snapshot (avoids re-fitting on every re-render)
    const key = wards.map((w) => w.id).join(",");
    if (fitted.current === key) return;
    fitted.current = key;
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
  }, [wards, center, map]);
  return null;
}

export default function RiskMapInner({
  wards,
  hospitals = [],
  cooling = [],
  water = [],
  activeLayers,
  selectedId,
  onSelect,
  center,
}: {
  wards: MapWard[];
  hospitals?: PointItem[];
  cooling?: PointItem[];
  water?: PointItem[];
  activeLayers: LayerKey[];
  selectedId: number | null;
  onSelect: (id: number | null) => void;
  center: [number, number];
}) {
  const [tilesFailed, setTilesFailed] = useState(false);

  const colorFor = (w: MapWard, layer: LayerKey): string => {
    if (layer === "thermal") return riskMeta(levelFromScore(w.htsi, "orange")).color;
    if (layer === "vulnerability") return riskMeta(levelFromScore(w.vulnerability, "orange")).color;
    if (layer === "green") return greenColor(w.vulnerability);
    return riskMeta(w.level).color;
  };

  const styleFor = (layer: LayerKey) => (feature: any) => {
    const w = wards.find((x) => x.code === feature?.properties?.code || x.id === feature?.properties?.id);
    const meta = w ? riskMeta(w.level) : RISK_META.green;
    const base = {
      weight: 1.5,
      opacity: 1,
      fillOpacity: 0.55,
    };
    if (layer === "hospitals" || layer === "cooling" || layer === "water") {
      return { ...base, color: "#94a3b8", fillColor: "#e2e8f0", fillOpacity: 0.08, weight: 1 };
    }
    return {
      ...base,
      color: meta.border,
      fillColor: colorFor(w ?? wards[0], layer),
    };
  };

  // highlight selected ward with a stronger outline
  const selectedStyle = {
    weight: 3,
    color: "#0f172a",
    fillOpacity: 0.75,
  };

  return (
    <MapContainer
      center={center}
      zoom={12}
      style={{ height: "100%", width: "100%" }}
      scrollWheelZoom={false}
      className="rounded-xl"
    >
      <AutoFit wards={wards} center={center} />
      <TileLayer
        attribution='&copy; OpenStreetMap contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        eventHandlers={{ tileerror: () => setTilesFailed(true) }}
      />
      {tilesFailed && (
        <div className="absolute left-2 top-2 z-[500] rounded-md bg-slate-900/85 px-2 py-1 text-[10px] text-white shadow">
          Map tiles unavailable (offline) — ward polygons still render
        </div>
      )}

      {(activeLayers.includes("combined") || activeLayers.includes("thermal") ||
        activeLayers.includes("vulnerability") || activeLayers.includes("green")) && (
        <LayerGroup>
          {wards.map((w) => {
            const layer = activeLayers.includes("thermal")
              ? "thermal"
              : activeLayers.includes("vulnerability")
                ? "vulnerability"
                : activeLayers.includes("green")
                  ? "green"
                  : "combined";
            return (
              <GeoJSON
                key={w.id}
                data={w.geojson ?? {
                  type: "Feature",
                  properties: { code: w.code },
                  geometry: {
                    type: "Polygon",
                    coordinates: [[
                      [w.centroid_lon - 0.006, w.centroid_lat - 0.005],
                      [w.centroid_lon + 0.006, w.centroid_lat - 0.005],
                      [w.centroid_lon + 0.006, w.centroid_lat + 0.005],
                      [w.centroid_lon - 0.006, w.centroid_lat + 0.005],
                      [w.centroid_lon - 0.006, w.centroid_lat - 0.005],
                    ]],
                  },
                }}
                style={selectedId === w.id ? selectedStyle : styleFor(layer)}
                eventHandlers={{ click: () => onSelect(w.id) }}
              >
                <LTooltip sticky>
                  {w.code} · {w.name} — {w.label}
                </LTooltip>
                <Popup className="risk-popup">
                  <div className="w-56 space-y-2 p-1">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-bold">{w.name}</p>
                      <RiskBadge level={w.level} size="sm" />
                    </div>
                    <p className="text-[11px] text-slate-500">Ward {w.code} · {w.population.toLocaleString("en-IN")} people</p>
                    <div className="grid grid-cols-3 gap-1 text-center text-[11px]">
                      <div className="rounded bg-slate-100 p-1"><b>{w.htsi}</b><br />HTSI</div>
                      <div className="rounded bg-slate-100 p-1"><b>{w.vulnerability}</b><br />Vuln</div>
                      <div className="rounded bg-slate-100 p-1"><b>{Math.round(w.score)}</b><br />Risk</div>
                    </div>
                    <button
                      className="w-full rounded-md bg-slate-900 px-2 py-1.5 text-[11px] font-medium text-white"
                      onClick={(e) => {
                        e.stopPropagation();
                        window.location.href = `/ward/${w.id}`;
                      }}
                    >
                      Open ward details →
                    </button>
                  </div>
                </Popup>
              </GeoJSON>
            );
          })}
        </LayerGroup>
      )}

      {activeLayers.includes("hospitals") && (
        <LayerGroup>
          {hospitals.map((h) => (
            <CircleMarker
              key={`h-${h.id}`}
              center={[h.lat, h.lon]}
              radius={9}
              pathOptions={{ color: "#ffffff", weight: 2, fillColor: "#dc2626", fillOpacity: 0.95 }}
            >
              <LTooltip sticky>
                <span className="flex items-center gap-1 text-xs"><Hospital className="h-3 w-3" /> {h.name}</span>
              </LTooltip>
            </CircleMarker>
          ))}
        </LayerGroup>
      )}

      {activeLayers.includes("cooling") && (
        <LayerGroup>
          {cooling.map((c) => (
            <CircleMarker
              key={`c-${c.id}`}
              center={[c.lat, c.lon]}
              radius={8}
              pathOptions={{ color: "#ffffff", weight: 2, fillColor: "#0284c7", fillOpacity: 0.95 }}
            >
              <LTooltip sticky>
                <span className="flex items-center gap-1 text-xs"><Snowflake className="h-3 w-3" /> {c.name}</span>
              </LTooltip>
            </CircleMarker>
          ))}
        </LayerGroup>
      )}

      {activeLayers.includes("water") && (
        <LayerGroup>
          {water.map((p) => (
            <CircleMarker
              key={`w-${p.id}`}
              center={[p.lat, p.lon]}
              radius={6}
              pathOptions={{ color: "#ffffff", weight: 2, fillColor: "#0891b2", fillOpacity: 0.95 }}
            >
              <LTooltip sticky>
                <span className="flex items-center gap-1 text-xs"><Droplets className="h-3 w-3" /> {p.name}</span>
              </LTooltip>
            </CircleMarker>
          ))}
        </LayerGroup>
      )}

      {/* legend */}
      <div className="absolute bottom-4 left-3 z-[500] rounded-lg border border-slate-200 bg-white/95 p-2.5 shadow-md">
        <p className="mb-1.5 text-[10px] font-bold uppercase tracking-wide text-slate-500">
          {activeLayers.includes("thermal") ? "Thermal stress" :
            activeLayers.includes("vulnerability") ? "Vulnerability" :
              activeLayers.includes("green") ? "Green cover / UHI" : "Combined risk"}
        </p>
        <div className="space-y-1">
          {(["green", "yellow", "orange", "red", "maroon"] as RiskKey[]).map((k) => (
            <div key={k} className="flex items-center gap-1.5 text-[11px] text-slate-700">
              <span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: riskMeta(k).color }} />
              {RISK_META[k].label}
            </div>
          ))}
        </div>
      </div>
    </MapContainer>
  );
}

function levelFromScore(score: number, fallback: RiskKey): RiskKey {
  if (score <= 20) return "green";
  if (score <= 40) return "yellow";
  if (score <= 60) return "orange";
  if (score <= 80) return "red";
  return "maroon";
}

function greenColor(vulnerabilityScore: number): string {
  // vulnerability already includes low-green-cover; colour green-ish -> dark
  if (vulnerabilityScore <= 30) return "#22c55e";
  if (vulnerabilityScore <= 50) return "#84cc16";
  if (vulnerabilityScore <= 70) return "#f59e0b";
  return "#b45309";
}