"use client";

// Leaflet map wrapped in next/dynamic (ssr:false) by the parent so it only
// loads in the browser — required because Leaflet touches `window`.
import "leaflet/dist/leaflet.css";

import { useEffect, useRef } from "react";
import L from "leaflet";
import { GeoJSON, LayerGroup, MapContainer, Popup, TileLayer, Tooltip as LTooltip, useMap, ZoomControl } from "react-leaflet";
import type { RiskKey } from "@/lib/types";
import type { HyperlocalWardOutline, HyperlocalZone } from "@/lib/types";
import { RISK_META, riskMeta } from "@/lib/utils";
import RiskBadge from "./RiskBadge";

/** Bounds covering a set of zone polygons. */
function zoneBounds(zones: HyperlocalZone[]): L.LatLngBounds | null {
  let minLat = Infinity,
    maxLat = -Infinity,
    minLon = Infinity,
    maxLon = -Infinity;
  for (const z of zones) {
    const ring = z.geojson?.geometry?.coordinates?.[0];
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
  return L.latLngBounds([minLat, minLon], [maxLat, maxLon]);
}

/**
 * Framing controller: fits the whole city once per data snapshot, then
 * zooms into a specific ward whenever the user picks one in the dropdown.
 */
function FitView({ zones, focusWard, center }: {
  zones: HyperlocalZone[];
  focusWard: string | null;
  center: [number, number];
}) {
  const map = useMap();
  const fitted = useRef<string | null>(null);

  useEffect(() => {
    if (focusWard) {
      const subset = zones.filter((z) => z.ward_code === focusWard);
      const b = zoneBounds(subset.length ? subset : zones);
      if (b) map.fitBounds(b, { padding: [50, 50], maxZoom: 16 });
      return;
    }
    const key = zones.map((z) => z.id).join(",");
    if (fitted.current === key) return;
    fitted.current = key;
    const b = zoneBounds(zones);
    if (b) map.fitBounds(b, { padding: [40, 40], maxZoom: 14 });
    else map.setView(center, 12);
  }, [zones, focusWard, center, map]);
  return null;
}

export default function HyperlocalMapInner({
  zones,
  outlines,
  selectedId,
  onSelect,
  focusWard,
  center,
}: {
  zones: HyperlocalZone[];
  outlines: HyperlocalWardOutline[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  focusWard: string | null;
  center: [number, number];
}) {
  const zoneById = new Map(zones.map((z) => [z.id, z]));

  const zoneStyle = (z: HyperlocalZone) => {
    const meta = riskMeta(z.level);
    return {
      weight: z.id === selectedId ? 3 : 1,
      color: z.id === selectedId ? "#0f172a" : "#ffffff",
      opacity: 1,
      fillColor: meta.color,
      fillOpacity: z.id === selectedId ? 0.8 : 0.62,
    };
  };

  const outlineStyle = {
    weight: 1.6,
    color: "#334155",
    opacity: 0.9,
    fillOpacity: 0,
  };

  return (
    <MapContainer
      center={center}
      zoom={12}
      zoomControl={false}
      style={{ height: "100%", width: "100%" }}
      scrollWheelZoom={false}
    >
      <ZoomControl position="bottomright" />
      <FitView zones={zones} focusWard={focusWard} center={center} />

      <TileLayer
        attribution='&copy; OpenStreetMap contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {/* hyperlocal pockets */}
      <LayerGroup>
        {zones.map((z) => (
          <GeoJSON
            key={z.id}
            data={z.geojson}
            style={() => zoneStyle(z)}
            eventHandlers={{ click: () => onSelect(z.id) }}
          >
            <LTooltip sticky>
              {z.ward_code} · {z.name.replace(/^.*? · /, "")} — {z.label}
            </LTooltip>
            <Popup className="risk-popup">
              <div className="w-60 space-y-2 p-1">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-bold leading-tight">{z.name}</p>
                  <RiskBadge level={z.level} size="sm" />
                </div>
                <p className="text-[11px] text-slate-500">
                  Ward {z.ward_code} · {z.population.toLocaleString("en-IN")} people · {z.kind}
                </p>
                <p className="rounded bg-slate-50 p-1.5 text-[11px] leading-snug text-slate-600">
                  {z.explanation.split(". Hyperlocal risk:")[0]}.
                </p>
                <div className="grid grid-cols-3 gap-1 text-center text-[11px]">
                  <div className="rounded bg-slate-100 p-1"><b>{z.htsi}</b><br />Ward HTSI</div>
                  <div className="rounded bg-slate-100 p-1"><b>{Math.round(z.exposure.score)}</b><br />Exposure</div>
                  <div className="rounded bg-slate-100 p-1"><b>{Math.round(z.score)}</b><br />Zone risk</div>
                </div>
              </div>
            </Popup>
          </GeoJSON>
        ))}
      </LayerGroup>

      {/* ward outlines on top so zones read as pockets inside a ward */}
      <LayerGroup>
        {outlines.map((w) => (
          <GeoJSON
            key={`outline-${w.id}`}
            data={w.geojson}
            interactive={false}
            style={outlineStyle}
          />
        ))}
      </LayerGroup>

      {/* legend */}
      <div className="absolute bottom-4 left-3 z-[500] rounded-xl border border-slate-200/80 bg-white/90 p-2.5 shadow-lg backdrop-blur-sm">
        <p className="mb-1.5 text-[10px] font-bold uppercase tracking-wide text-slate-500">
          Hyperlocal risk
        </p>
        <div className="space-y-1">
          {(["green", "yellow", "orange", "red", "maroon"] as RiskKey[]).map((k) => (
            <div key={k} className="flex items-center gap-1.5 text-[11px] text-slate-700">
              <span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: RISK_META[k].color }} />
              {RISK_META[k].label}
            </div>
          ))}
        </div>
      </div>
    </MapContainer>
  );
}
