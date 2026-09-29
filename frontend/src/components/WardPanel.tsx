"use client";

import { Link } from "react-router-dom";
import { ArrowRight, Building2, Droplets, Hospital, Snowflake, Users } from "lucide-react";
import { useApi } from "@/lib/useApi";
import { api } from "@/lib/api";
import type { WardRisk } from "@/lib/types";
import { fmt, fmtInt } from "@/lib/utils";
import RiskBadge from "./RiskBadge";
import { Badge, Card, CardContent, Progress, Separator, Spinner } from "./ui";

function Row({ label, value, unit, accent }: { label: string; value: string | number; unit?: string; accent?: string }) {
  return (
    <div className="flex items-center justify-between gap-2 py-1">
      <span className="text-xs text-slate-500">{label}</span>
      <span className="text-xs font-semibold" style={{ color: accent }}>
        {value}
        {unit && <span className="ml-0.5 font-normal text-slate-400">{unit}</span>}
      </span>
    </div>
  );
}

export default function WardPanel({ wardId }: { wardId: number | null }) {
  const { data, loading, error } = useApi<WardRisk | null>(
    () => (wardId ? api.ward(wardId) : Promise.resolve(null)),
    [wardId]
  );

  if (!wardId) {
    return (
      <Card className="flex h-full flex-col items-center justify-center p-8 text-center">
        <Building2 className="mb-2 h-8 w-8 text-slate-300" />
        <p className="text-sm text-slate-500">Select a ward on the map to see its full heat-health profile.</p>
      </Card>
    );
  }

  if (loading) return <Spinner label={`Loading ward ${wardId}…`} />;
  if (error || !data) {
    return <p className="p-4 text-xs text-red-700">{error}</p>;
  }

  const v = data.vulnerability;
  const h = data.health;
  const f = data.final;
  const cur = data.current;

  return (
    <div className="scroll-thin max-h-[calc(100vh-160px)] space-y-3 overflow-y-auto pr-1">
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                Ward {data.ward_code} · ID {data.ward_id}
              </p>
              <h3 className="text-lg font-bold text-slate-900">{data.ward_name}</h3>
            </div>
            <RiskBadge level={f.level} size="md" />
          </div>
          <p className="mt-2 rounded-lg bg-slate-50 p-2 text-[11px] leading-relaxed text-slate-600">
            {f.explanation}
          </p>
          <Link
            to={`/ward/${data.ward_id}`}
            className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-slate-900 hover:underline"
          >
            Full ward details <ArrowRight className="h-3 w-3" />
          </Link>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-4">
          <p className="mb-1 text-xs font-bold text-slate-700">Current conditions</p>
          <div className="grid grid-cols-2 gap-x-3">
            <Row label="Temperature" value={fmt(cur.t)} unit="°C" />
            <Row label="Humidity" value={fmt(cur.rh)} unit="%" />
            <Row label="Wind" value={fmt(cur.wind)} unit="m/s" />
            <Row label="Solar radiation" value={fmt(cur.solar, 0)} unit="W/m²" />
            <Row label="Heat Index" value={fmt(cur.hi)} unit="°C" accent="#f97316" />
            <Row label="Est. WBGT" value={fmt(cur.wbgt)} unit="°C" accent="#dc2626" />
            <Row label="UTCI Proxy" value={fmt(cur.utci_proxy)} unit="°C" accent="#7c3aed" />
          </div>
          <Separator className="my-2" />
          <div className="grid grid-cols-2 gap-x-3">
            <Row label="Daily max T" value={fmt(data.day.tmax)} unit="°C" />
            <Row label="Daily min T" value={fmt(data.day.tmin)} unit="°C" />
            <Row label="Hot days (consec.)" value={data.day.consecutive_high_days ?? 0} unit="days" />
            <Row label="Hours ≥ WBGT 26" value={data.day.exposure_hours ?? 0} unit="h" />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-4">
          <p className="mb-2 text-xs font-bold text-slate-700">Human Thermal Stress Index — {fmt(data.htsi.score)}/100</p>
          {Object.entries(data.htsi.components).map(([k, val]) => (
            <div key={k} className="mb-1.5">
              <div className="flex justify-between text-[11px] text-slate-500">
                <span>{k.replace(/_/g, " ")}</span>
                <span>{fmt(val)}/100</span>
              </div>
              <Progress value={val} color={val > 60 ? "#dc2626" : val > 40 ? "#f97316" : "#16a34a"} />
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-4">
          <p className="mb-2 text-xs font-bold text-slate-700">
            Vulnerability — {fmt(v.score)}/100
            <span className="ml-2 font-normal text-slate-400">weighted contributions</span>
          </p>
          {Object.entries(v.contributions).map(([k, val]) => (
            <div key={k} className="mb-1.5">
              <div className="flex justify-between text-[11px] text-slate-500">
                <span>{v.labels[k]}</span>
                <span>+{fmt(val)} pts</span>
              </div>
              <Progress value={(val / (v.weights[k] * 100)) * 100} color="#7c3aed" />
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-4">
          <p className="mb-1 text-xs font-bold text-slate-700">Health-risk estimate</p>
          <div className="space-y-1">
            <Row label="Hospitalization risk" value={h.hospitalization_risk} />
            <Row label="Health demand ↑" value={h.demand_increase_pct.range_pct} unit="%" accent="#dc2626" />
            <Row label="Mortality band" value={h.mortality_risk_band} />
            <Row label="Confidence" value={h.confidence} />
          </div>
          <p className="mt-2 text-[10px] leading-snug text-slate-400">{h.demand_increase_pct.label}.</p>
          <p className="text-[10px] text-slate-400">Source: {h.demand_increase_pct.source}.</p>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-4">
          <p className="mb-2 text-xs font-bold text-slate-700">Main risk contributors</p>
          {h.drivers.slice(0, 4).map((d) => (
            <div key={d.name} className="mb-1.5">
              <div className="flex justify-between text-[11px] text-slate-500">
                <span>{d.name}</span>
                <span>{d.contribution_pct}%</span>
              </div>
              <Progress value={d.contribution_pct} color="#0f172a" />
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-4">
          <p className="mb-2 text-xs font-bold text-slate-700">Nearest resources</p>
          <div className="space-y-1.5 text-xs">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-slate-600"><Hospital className="h-3.5 w-3.5 text-red-600" /> {data.nearest.hospital.name}</span>
              <span className="font-medium">{data.nearest.hospital.distance_km} km</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-slate-600"><Snowflake className="h-3.5 w-3.5 text-sky-600" /> {data.nearest.cooling_centre.name}</span>
              <span className="font-medium">{data.nearest.cooling_centre.distance_km} km</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-slate-600"><Droplets className="h-3.5 w-3.5 text-cyan-600" /> {data.nearest.water_point.name}</span>
              <span className="font-medium">{data.nearest.water_point.distance_km} km</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-4">
          <p className="mb-2 text-xs font-bold text-slate-700">Recommended actions ({data.actions.length})</p>
          <div className="space-y-1.5">
            {data.actions.map((a, i) => (
              <div key={i} className="rounded-lg border border-slate-100 bg-slate-50 p-2">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-[11px] font-semibold text-slate-800">{a.title}</p>
                  <Badge variant={a.priority === "Immediate" ? "destructive" : "secondary"}>{a.priority}</Badge>
                </div>
                <p className="mt-0.5 text-[10px] text-slate-500">{a.department}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}