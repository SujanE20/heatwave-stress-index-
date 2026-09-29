"use client";

import type { ComponentProps } from "react";
import RiskMapInner from "./RiskMapInner";
import type { LayerKey, MapWard, PointItem } from "./RiskMapInner";

// NOTE: LAYERS must live here (outside the Leaflet module) so the map page can
// import it without pulling Leaflet into the server bundle.
export const LAYERS: { key: LayerKey; label: string }[] = [
  { key: "combined", label: "Combined Risk" },
  { key: "thermal", label: "Thermal Stress" },
  { key: "vulnerability", label: "Vulnerability" },
  { key: "hospitals", label: "Hospitals" },
  { key: "cooling", label: "Cooling Centres" },
  { key: "water", label: "Water Points" },
  { key: "green", label: "Green Cover / UHI" },
];

export type { LayerKey, MapWard, PointItem };

export default function RiskMap(props: ComponentProps<typeof RiskMapInner>) {
  return <RiskMapInner {...props} />;
}