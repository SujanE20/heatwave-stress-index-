"use client";

import { useParams } from "react-router-dom";
import {
  Activity, Building2, CalendarClock, Droplets, Flame, Gauge, Hospital, MapPin,
  ShieldAlert, Snowflake, Sun, Thermometer, Users, Wind,
} from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { fmt, fmtDate, fmtInt } from "@/lib/utils";
import RiskBadge from "@/components/RiskBadge";
import DisclaimerFooter from "@/components/DisclaimerFooter";
import { ChartCard, MultiLine, RiskBars } from "@/components/charts";
import {
  Badge, Card, CardContent, CardDescription, CardHeader, CardTitle,
  ErrorState, Progress, Separator, Spinner,
} from "@/components/ui";

function Stat({ label, value, unit, icon }: { label: string; value: string | number; unit?: string; icon?: React.ReactNode }) {
  return (
    <div className="rounded-lg bg-slate-50 p-2.5">
      <p className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
        {icon}{label}
      </p>
      <p className="mt-0.5 text-lg font-bold text-slate-900">
        {value}{unit && <span className="ml-0.5 text-xs font-medium text-slate-400">{unit}</span>}
      </p>
    </div>
  );
}

export default function WardPage() {
  const params = useParams();
  const id = String(params.id);
  const { data, loading, error, refresh } = useApi(() => api.ward(id));
  const { data: forecast } = useApi(() => api.wardForecast(id));
  const { data: wardLite } = useApi(() => api.wards(false));

  if (loading) return <Spinner label="Loading ward…" />;
  if (error || !data) return <ErrorState message={error || "Ward not found"} onRetry={refresh} />;

  const wl = wardLite?.find((w) => String(w.id) === id);

  const cur = data.current;
  const v = data.vulnerability;
  const h = data.health;
  const f = data.final;

  const bars = (forecast?.daily ?? []).map((d) => ({
    label: fmtDate(d.date).split(",")[0],
    risk: d.tmax,
    level: d.risk_level,
  }));

  return (
    <div className="space-y-5">
      {/* header */}
      <div className="flex flex-wrap items-center gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-400">
            Ward {data.ward_code} · ID {data.ward_id}
          </p>
          <h1 className="text-2xl font-bold text-slate-900">{data.ward_name}</h1>
        </div>
        <RiskBadge level={f.level} label={f.label} size="lg" />
        <div className="ml-auto flex items-center gap-2 text-xs text-slate-500">
          <MapPin className="h-3.5 w-3.5" />
          {data.ward_code} · {fmtDate(data.date)}
        </div>
      </div>

      {/* explanation */}
      <Card className="border-l-4" style={{ borderLeftColor: `var(--risk-${f.level})` }}>
        <CardContent className="pt-4">
          <p className="text-sm leading-relaxed text-slate-700">{f.explanation}</p>
          {f.escalations.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {f.escalations.map((e, i) => (
                <Badge key={i} variant="destructive">{e}</Badge>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* score bars */}
      <div className="grid gap-3 sm:grid-cols-3">
        <Card>
          <CardContent className="pt-4">
            <div className="flex justify-between text-xs">
              <span className="font-semibold text-slate-700">HTSI (thermal stress)</span>
              <span className="font-bold">{fmt(data.htsi.score)}/100</span>
            </div>
            <div className="mt-2"><Progress value={data.htsi.score} color="#be123c" /></div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex justify-between text-xs">
              <span className="font-semibold text-slate-700">Vulnerability</span>
              <span className="font-bold">{fmt(v.score)}/100</span>
            </div>
            <div className="mt-2"><Progress value={v.score} color="#7c3aed" /></div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex justify-between text-xs">
              <span className="font-semibold text-slate-700">Final risk score</span>
              <span className="font-bold">{fmt(f.score)}/100</span>
            </div>
            <div className="mt-2"><Progress value={f.score} color="#dc2626" /></div>
            <p className="mt-1 text-[10px] text-slate-400">from today's max temperature (25→45 °C scaled to 0-100)</p>
          </CardContent>
        </Card>
      </div>

      {/* demographics + current conditions */}
      <div className="grid gap-3 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><Users className="h-4 w-4" /> Ward demographics</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              <Stat label="Population" value={fmtInt(wl?.population)} icon={<Users className="h-3 w-3" />} />
              <Stat label="Area" value={fmt(wl?.area_km2, 2)} unit="km²" />
              <Stat label="Density" value={fmtInt(wl?.population_density)} unit="/km²" />
              <Stat label="Elderly" value={`${fmt(wl?.elderly_pct)}%`} />
              <Stat label="Outdoor workers" value={fmtInt(wl?.outdoor_worker_density)} unit="/km²" />
              <Stat label="Green cover" value={`${fmt(wl?.green_cover_pct)}%`} />
              <Stat label="Informal housing" value={`${fmt(wl?.informal_housing_pct)}%`} />
              <Stat label="Hospital access" value={fmt(wl?.hospital_access_score)} unit="/100" />
              <Stat label="Chronic disease" value={`${fmt(wl?.chronic_disease_pct)}%`} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><Thermometer className="h-4 w-4 text-sky-500" /> Current conditions</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              <Stat label="Temperature" value={fmt(cur.t)} unit="°C" icon={<Thermometer className="h-3 w-3" />} />
              <Stat label="Humidity" value={fmt(cur.rh)} unit="%" icon={<Droplets className="h-3 w-3" />} />
              <Stat label="Wind" value={fmt(cur.wind)} unit="m/s" icon={<Wind className="h-3 w-3" />} />
              <Stat label="Solar radiation" value={fmt(cur.solar, 0)} unit="W/m²" icon={<Sun className="h-3 w-3" />} />
              <Stat label="Heat Index" value={fmt(cur.hi)} unit="°C" icon={<Flame className="h-3 w-3" />} />
              <Stat label="Est. WBGT" value={fmt(cur.wbgt)} unit="°C" icon={<Sun className="h-3 w-3" />} />
              <Stat label="UTCI Proxy" value={fmt(cur.utci_proxy)} unit="°C" icon={<Gauge className="h-3 w-3" />} />
              <Stat label="HTSI" value={fmt(data.htsi.score)} unit="/100" icon={<Activity className="h-3 w-3" />} />
              <Stat label="Consec. hot days" value={data.day.consecutive_high_days ?? 0} icon={<CalendarClock className="h-3 w-3" />} />
            </div>
            <p className="mt-3 text-[10px] leading-snug text-slate-400">
              WBGT and UTCI Proxy are decision-support estimates derived from weather data — not instrument measurements.
            </p>
          </CardContent>
        </Card>
      </div>

      {/* vulnerability contributions */}
      <Card>
        <CardHeader>
          <CardTitle>Vulnerability contributors — {fmt(v.score)}/100</CardTitle>
          <CardDescription>Each factor's weighted contribution to the ward's vulnerability score</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-x-6 gap-y-2 sm:grid-cols-2">
            {Object.entries(v.contributions).map(([k, val]) => (
              <div key={k}>
                <div className="flex justify-between text-xs text-slate-500">
                  <span>{v.labels[k]}</span>
                  <span className="font-semibold text-slate-700">+{fmt(val)}</span>
                </div>
                <Progress value={(val / (v.weights[k] * 100)) * 100} color="#7c3aed" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* health risk */}
      <div className="grid gap-3 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><Activity className="h-4 w-4 text-red-500" /> Health-risk estimate</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-2">
              <Stat label="Hospitalization risk" value={h.hospitalization_risk} />
              <Stat label="Mortality band" value={h.mortality_risk_band} />
              <Stat label="Health demand ↑" value={h.demand_increase_pct.range_pct} unit="%" />
              <Stat label="Confidence" value={h.confidence} />
            </div>
            <Separator className="my-3" />
            <p className="text-xs font-semibold text-slate-700">Main risk drivers</p>
            <div className="mt-2 space-y-1.5">
              {h.drivers.map((d) => (
                <div key={d.name} className="flex justify-between text-xs">
                  <span className="text-slate-600">{d.name}</span>
                  <span className="font-semibold">{d.contribution_pct}%</span>
                </div>
              ))}
            </div>
            <ul className="mt-3 space-y-1 text-[10px] leading-relaxed text-slate-400">
              {h.safety_notes.map((n, i) => <li key={i}>• {n}</li>)}
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><Building2 className="h-4 w-4" /> Recommended actions</CardTitle></CardHeader>
          <CardContent className="scroll-thin max-h-[420px] space-y-2 overflow-y-auto">
            {data.actions.map((a, i) => (
              <div key={i} className="rounded-lg border border-slate-100 p-2.5">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-xs font-semibold text-slate-800">{a.title}</p>
                  <Badge variant={a.priority === "Immediate" ? "destructive" : a.priority === "Today" ? "secondary" : "outline"}>{a.priority}</Badge>
                </div>
                <p className="mt-0.5 text-[10px] text-slate-500">{a.department} · {a.status}</p>
                <p className="mt-1 text-[10px] leading-snug text-slate-400">{a.reason}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* nearest resources */}
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><MapPin className="h-4 w-4 text-red-500" /> Nearest resources</CardTitle></CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-lg bg-red-50 p-3">
              <p className="flex items-center gap-1.5 text-xs font-semibold text-red-800"><Hospital className="h-4 w-4" /> {data.nearest.hospital.name}</p>
              <p className="mt-1 text-xs text-red-700">{data.nearest.hospital.distance_km} km away</p>
            </div>
            <div className="rounded-lg bg-sky-50 p-3">
              <p className="flex items-center gap-1.5 text-xs font-semibold text-sky-800"><Snowflake className="h-4 w-4" /> {data.nearest.cooling_centre.name}</p>
              <p className="mt-1 text-xs text-sky-700">{data.nearest.cooling_centre.distance_km} km away</p>
            </div>
            <div className="rounded-lg bg-cyan-50 p-3">
              <p className="flex items-center gap-1.5 text-xs font-semibold text-cyan-800"><Droplets className="h-4 w-4" /> {data.nearest.water_point.name}</p>
              <p className="mt-1 text-xs text-cyan-700">{data.nearest.water_point.distance_km} km away</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 5-day forecast */}
      {forecast && (
        <div className="grid gap-3 lg:grid-cols-2">
          <ChartCard title="5-day risk forecast" description="Daily max air temperature → Low ≤30 · Moderate 30-35 · High 35-40 · Very High 40-44 · Extreme ≥45 °C">
            <RiskBars data={bars} />
          </ChartCard>
          <ChartCard title="Forecast detail" description="Daily maxima">
            <MultiLine
              data={(forecast.daily ?? []).map((d) => ({ label: fmtDate(d.date).split(",")[0], tmax: d.tmax, hi_max: d.hi_max, wbgt_max: d.wbgt_max, utci_max: d.utci_max }))}
              series={[
                { key: "tmax", name: "T max" },
                { key: "hi_max", name: "Heat Index" },
                { key: "wbgt_max", name: "Est. WBGT" },
                { key: "utci_max", name: "UTCI proxy" },
              ]}
            />
          </ChartCard>
        </div>
      )}

      <DisclaimerFooter />
    </div>
  );
}
