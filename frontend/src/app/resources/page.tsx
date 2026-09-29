"use client";

import { Bed, Droplets, FlaskConical, HeartPulse, Hospital, MapPin, Snowflake, Users } from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { fmt, fmtInt } from "@/lib/utils";
import DisclaimerFooter from "@/components/DisclaimerFooter";
import RiskBadge from "@/components/RiskBadge";
import {
  AlertNote, Badge, Card, CardContent, CardDescription, CardHeader, CardTitle,
  ErrorState, Progress, Spinner, Table, Td, Th,
} from "@/components/ui";

export default function ResourcesPage() {
  const { data: hospitals, loading: l1, error: e1, refresh: r1 } = useApi(() => api.hospitals());
  const { data: cooling, loading: l2, error: e2, refresh: r2 } = useApi(() => api.coolingCentres());
  const { data: water } = useApi(() => api.waterPoints());
  const { data: coverage } = useApi(() => api.coverage());

  if (l1 || l2) return <Spinner label="Loading resources…" />;
  if (e1 || e2) return <ErrorState message={e1 || e2 || "Error"} onRetry={() => { r1(); r2(); }} />;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-bold text-slate-900">Resource Management</h1>
        <Badge className="bg-slate-100 text-slate-700">
          {hospitals?.length} hospitals · {cooling?.length} cooling centres · {water?.length} water points
        </Badge>
      </div>

      <AlertNote tone="info" title="Simulated data">
        Hospital capacity, occupancy, stock levels and expected admissions are simulated for the demo and labelled as estimates.
      </AlertNote>

      {/* hospitals */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Hospital className="h-4 w-4 text-red-500" /> Hospitals — expected heat-related admissions (next 3–5 days)</CardTitle>
          <CardDescription>Simulated surge estimates based on nearby ward risk and population</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <thead>
              <tr>
                <Th>Hospital</Th>
                <Th>Type</Th>
                <Th>Beds</Th>
                <Th>Emergency</Th>
                <Th>Available E.R.</Th>
                <Th>Occupancy</Th>
                <Th>ORS / IV</Th>
                <Th>Expected heat admissions</Th>
              </tr>
            </thead>
            <tbody>
              {(hospitals ?? []).map((h) => (
                <tr key={h.id} className="hover:bg-slate-50">
                  <Td className="font-medium">{h.name}</Td>
                  <Td>{h.type}</Td>
                  <Td>{h.beds}</Td>
                  <Td>{h.emergency_beds}</Td>
                  <Td className="font-semibold text-emerald-700">{h.available_emergency_beds}</Td>
                  <Td>
                    <div className="flex items-center gap-2">
                      <div className="w-20"><Progress value={h.occupancy_pct} color={h.occupancy_pct > 80 ? "#dc2626" : "#f97316"} /></div>
                      <span className="text-xs">{h.occupancy_pct}%</span>
                    </div>
                  </Td>
                  <Td className="text-xs">{fmtInt(h.ors_units)} / {fmtInt(h.iv_fluids_units)}</Td>
                  <Td className="font-bold text-red-700">{fmtInt(h.expected_heat_admissions_3_5d)}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
          <p className="mt-2 text-[10px] text-slate-400">{(hospitals ?? [])[0]?.note}</p>
        </CardContent>
      </Card>

      {/* cooling centres */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Snowflake className="h-4 w-4 text-sky-500" /> Cooling centres — capacity, occupancy, stocks</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {(cooling ?? []).map((c) => (
              <div key={c.id} className="rounded-xl border border-slate-100 bg-slate-50 p-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-bold text-slate-800">{c.name}</p>
                    <p className="text-[11px] text-slate-500">Open {c.opens}–{c.closes}</p>
                  </div>
                  <Badge variant={c.occupancy_pct > 75 ? "destructive" : "secondary"}>{c.occupancy_pct}% full</Badge>
                </div>
                <div className="mt-2 grid grid-cols-3 gap-2 text-center">
                  <div className="rounded-lg bg-white p-2">
                    <Users className="mx-auto h-4 w-4 text-slate-400" />
                    <p className="mt-0.5 text-sm font-bold">{c.current_occupancy}/{c.capacity}</p>
                    <p className="text-[10px] text-slate-400">occupancy</p>
                  </div>
                  <div className="rounded-lg bg-white p-2">
                    <Droplets className="mx-auto h-4 w-4 text-cyan-500" />
                    <p className="mt-0.5 text-sm font-bold">{fmtInt(c.water_stock_l)} L</p>
                    <p className="text-[10px] text-slate-400">water</p>
                  </div>
                  <div className="rounded-lg bg-white p-2">
                    <FlaskConical className="mx-auto h-4 w-4 text-amber-500" />
                    <p className="mt-0.5 text-sm font-bold">{fmtInt(c.ors_units)}</p>
                    <p className="text-[10px] text-slate-400">ORS units</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* coverage gaps */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><MapPin className="h-4 w-4 text-orange-500" /> Ward coverage gaps — temporary cooling-centre recommendations</CardTitle>
          <CardDescription>Transparent rule: vulnerable residents exposed × distance to nearest cooling centre</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <thead>
              <tr>
                <Th>Ward</Th>
                <Th>Risk</Th>
                <Th>Vulnerable exposed</Th>
                <Th>Nearest cooling centre</Th>
                <Th>Distance</Th>
                <Th>Recommendation</Th>
              </tr>
            </thead>
            <tbody>
              {(coverage ?? []).map((g) => (
                <tr key={g.ward_id} className="hover:bg-slate-50">
                  <Td className="font-medium">{g.ward_code} · {g.ward_name}</Td>
                  <Td><RiskBadge level={g.risk_level} label={g.risk_label} size="sm" /></Td>
                  <Td className="font-semibold">{fmtInt(g.vulnerable_exposed)}</Td>
                  <Td>{g.nearest_cooling_centre}</Td>
                  <Td>{g.distance_km} km</Td>
                  <Td className="max-w-sm text-[11px] leading-snug text-slate-600">{g.recommendation}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </CardContent>
      </Card>

      {/* water points */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Droplets className="h-4 w-4 text-cyan-500" /> Water points</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {(water ?? []).map((p) => (
              <span key={p.id} className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-700">
                <Droplets className="h-3.5 w-3.5 text-cyan-500" />
                {p.name}
                <Badge variant={p.status === "Operational" ? "secondary" : "destructive"} className="ml-1">{p.status}</Badge>
              </span>
            ))}
          </div>
        </CardContent>
      </Card>

      <DisclaimerFooter />
    </div>
  );
}