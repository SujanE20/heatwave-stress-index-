"use client";

import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { fmt, fmtDate, fmtInt, RISK_META } from "@/lib/utils";
import { ChartCard, MultiLine, RiskBars, ScatterRisk, TwinBar } from "@/components/charts";
import DisclaimerFooter from "@/components/DisclaimerFooter";
import RiskBadge from "@/components/RiskBadge";
import { Badge, Card, CardContent, CardDescription, CardHeader, CardTitle, ErrorState, Spinner, Table, Td, Th } from "@/components/ui";

export default function AnalyticsPage() {
  const { data, loading, error, refresh } = useApi(() => api.trends());

  if (loading) return <Spinner label="Loading analytics…" />;
  if (error || !data) return <ErrorState message={error || "No data"} onRetry={refresh} />;

  const fc = data.forecast.map((d) => ({
    label: fmtDate(d.date).split(",")[0],
    tmax: d.tmax, tmin: d.tmin, hi_max: d.hi_max, wbgt_max: d.wbgt_max, utci_max: d.utci_max, htsi: d.htsi,
  }));

  const hourly = data.hourly.map((h) => ({ label: h.hour, t: h.t, apparent: h.apparent, hi: h.hi, wbgt: h.wbgt, utci_proxy: h.utci_proxy }));

  const history = data.hospital_load_history.slice(-60).map((h) => ({
    label: h.date.slice(5),
    load_increase_pct: h.load_increase_pct,
    heat_admissions: h.heat_admissions,
  }));

  const riskBars = data.forecast.map((d) => ({ label: fmtDate(d.date).split(",")[0], risk: d.tmax, level: d.risk_level }));

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-bold text-slate-900">Forecast & Analytics</h1>
        {data.weather.is_demo && (
          <Badge className="bg-amber-100 text-amber-800 ring-1 ring-amber-300">Demo weather · offline</Badge>
        )}
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        <ChartCard title="Hourly forecast — next 48 h" description="Temperature, apparent temperature, Heat Index, estimated WBGT, UTCI proxy">
          <MultiLine
            data={hourly.slice(0, 48)}
            series={[
              { key: "t", name: "T" },
              { key: "apparent", name: "Apparent" },
              { key: "hi", name: "Heat Index" },
              { key: "wbgt", name: "Est. WBGT" },
              { key: "utci_proxy", name: "UTCI proxy" },
            ]}
          />
        </ChartCard>

        <ChartCard title="5-day daily forecast" description="Daily maxima for temperature, Heat Index, WBGT and UTCI proxy">
          <MultiLine
            data={fc}
            series={[
              { key: "tmax", name: "T max" },
              { key: "tmin", name: "T min" },
              { key: "hi_max", name: "Heat Index" },
              { key: "wbgt_max", name: "Est. WBGT" },
              { key: "utci_max", name: "UTCI proxy" },
            ]}
          />
        </ChartCard>
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        <ChartCard title="Daily temperature risk" description="Daily max air temperature → Low ≤30 · Moderate 30-35 · High 35-40 · Very High 40-44 · Extreme ≥45 °C">
          <RiskBars data={riskBars} />
        </ChartCard>

        <ChartCard title="Vulnerability vs thermal stress" description="Every ward plotted — risk colour = combined risk level">
          <ScatterRisk data={data.scatter} />
        </ChartCard>
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        <ChartCard title="Historical hospital load (last 60 days)" description="Synthetic history — increase above baseline and heat admissions">
          <TwinBar
            data={history}
            keys={["load_increase_pct", "heat_admissions"]}
            names={["Demand increase %", "Heat admissions"]}
            colors={["#f97316", "#dc2626"]}
            unit=""
          />
        </ChartCard>

        <ChartCard title="Intervention effectiveness (demo placeholder)" description={data.intervention_effectiveness.note}>
          <MultiLine
            data={data.intervention_effectiveness.series.map((s) => ({ label: s.day.split("(")[0].trim(), excess_health_demand_pct: s.excess_health_demand_pct }))}
            series={[{ key: "excess_health_demand_pct", name: "Excess health demand %" }]}
            unit="%"
          />
          <p className="mt-2 text-[11px] text-slate-500">{data.intervention_effectiveness.estimated_effect}</p>
        </ChartCard>
      </div>

      {/* ward comparison table */}
      <Card>
        <CardHeader>
          <CardTitle>Ward comparison — sorted by risk</CardTitle>
          <CardDescription>Current combined risk per ward</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <thead>
              <tr>
                <Th>Ward</Th>
                <Th>Risk</Th>
                <Th>Score</Th>
                <Th>HTSI</Th>
                <Th>Vulnerability</Th>
                <Th>Health</Th>
                <Th>Peak WBGT</Th>
                <Th>Consec. days</Th>
                <Th>Population</Th>
              </tr>
            </thead>
            <tbody>
              {data.ward_comparison.map((w) => (
                <tr key={w.id} className="hover:bg-slate-50">
                  <Td className="font-medium">
                    <Link to={`/ward/${w.id}`} className="hover:underline">
                      {w.code} · {w.name}
                    </Link>
                  </Td>
                  <Td><RiskBadge level={w.risk_level} label={w.risk_label} size="sm" /></Td>
                  <Td className="font-semibold">{Math.round(w.risk_score)}</Td>
                  <Td>{fmt(w.htsi)}</Td>
                  <Td>{fmt(w.vulnerability)}</Td>
                  <Td>{fmt(w.health_score)}</Td>
                  <Td>{fmt(w.wbgt_max)}°C</Td>
                  <Td>{w.consecutive_days}</Td>
                  <Td>{fmtInt(w.population)}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </CardContent>
      </Card>

      {/* alert history */}
      <Card>
        <CardHeader>
          <CardTitle>Alert history</CardTitle>
          <CardDescription>{data.alert_history.length} alerts recorded (simulated delivery)</CardDescription>
        </CardHeader>
        <CardContent>
          {data.alert_history.length === 0 ? (
            <p className="text-sm text-slate-500">No alerts yet — generate some from the Alerts Centre.</p>
          ) : (
            <Table>
              <thead>
                <tr>
                  <Th>Time</Th><Th>Title</Th><Th>Severity</Th><Th>Status</Th><Th>Channels</Th>
                </tr>
              </thead>
              <tbody>
                {data.alert_history.slice(0, 15).map((a) => (
                  <tr key={a.id} className="hover:bg-slate-50">
                    <Td>{fmtDate(a.ts)} {a.ts.slice(11, 16)}</Td>
                    <Td className="font-medium">{a.title}</Td>
                    <Td><Badge variant={a.severity === "extreme" ? "destructive" : "secondary"}>{a.severity}</Badge></Td>
                    <Td>{a.status}</Td>
                    <Td>{a.channels.join(", ")}</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </CardContent>
      </Card>

      <DisclaimerFooter />
    </div>
  );
}