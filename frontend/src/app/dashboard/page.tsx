"use client";

import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Activity, AlertTriangle, BellRing, CloudSun, Droplets, Flame, Gauge, Megaphone,
  Radiation, ShieldAlert, Snowflake, Sun, Thermometer, Timer, Users, Wind,
} from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { fmt, fmtDate, fmtInt, fmtTime, RISK_META } from "@/lib/utils";
import type { RiskKey } from "@/lib/types";
import MetricCard from "@/components/MetricCard";
import RiskBadge from "@/components/RiskBadge";
import DisclaimerFooter from "@/components/DisclaimerFooter";
import { filterActionsByRole, ROLE_META, useRole } from "@/lib/role";
import { ChartCard, MultiLine } from "@/components/charts";
import {
  AlertNote, Badge, Button, Card, CardContent, CardDescription, CardHeader,
  CardTitle, ErrorState, Select, Spinner,
} from "@/components/ui";

const ICON_TOOLTIPS: Record<string, string> = {
  t: "Air temperature 2 m above ground (dry-bulb)",
  rh: "Relative humidity 2 m above ground",
  wind: "Wind speed 10 m above ground",
  solar: "Incoming shortwave radiation (proxy for solar load)",
  hi: "NOAA/NWS Heat Index — combines temperature and humidity",
  wbgt: "Estimated outdoor Wet-Bulb Globe Temperature = 0.7·Tnwb + 0.2·Tg + 0.1·Tdb. An estimate, not a calibrated instrument.",
  utci: "UTCI Proxy — documented stand-in for the Universal Thermal Climate Index (not official UTCI)",
  htsi: "Human Thermal Stress Index (0-100) — weighted blend of WBGT, Heat Index, UTCI proxy, night recovery and cumulative exposure",
};

export default function DashboardPage() {
  const navigate = useNavigate();
  const { role } = useRole();
  const { data, loading, error, refresh } = useApi(() => api.dashboard());
  const [busy, setBusy] = useState<"plan" | "alerts" | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  if (loading) return <Spinner label="Loading city risk dashboard…" />;
  if (error || !data) return <ErrorState message={error || "No data"} onRetry={refresh} />;

  const cc = data.current_conditions;
  const risk = data.risk;
  const roleActions = filterActionsByRole(role, data.recommended_actions);

  const triggerPlan = async () => {
    setBusy("plan");
    try {
      const res = await api.triggerHeatActionPlan();
      setToast(`✅ ${res.message} — plan #${res.detail.plan_id} is now Active.`);
      refresh();
    } catch (e: any) {
      setToast(`⚠️ ${e.message}`);
    } finally {
      setBusy(null);
    }
  };

  const generateAlerts = async () => {
    setBusy("alerts");
    try {
      const res = await api.generateAlerts();
      setToast(`✅ Generated ${res.generated} bilingual alerts. Opening Alerts Centre…`);
      setTimeout(() => navigate("/alerts"), 700);
    } catch (e: any) {
      setToast(`⚠️ ${e.message}`);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="space-y-5">
      {/* header row */}
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-bold text-slate-900">
          Command Centre Dashboard — {data.city.name}
        </h1>
        <RiskBadge level={risk.city_level} label={risk.city_label} size="lg" />
        {data.weather.is_demo && (
          <Badge className="bg-amber-100 text-amber-800 ring-1 ring-amber-300">Demo weather · {data.weather.scenario.replace(/_/g, " ")}</Badge>
        )}
        <div className="ml-auto flex gap-2">
          <Button
            variant="destructive"
            loading={busy === "plan"}
            onClick={triggerPlan}
            disabled={!!data.action_plan}
            title={data.action_plan ? "Heat Action Plan already active" : "Activate the city Heat Action Plan"}
          >
            <ShieldAlert className="h-4 w-4" />
            {data.action_plan ? "HAP Active" : "Trigger Heat Action Plan"}
          </Button>
          <Button variant="default" loading={busy === "alerts"} onClick={generateAlerts}>
            <Megaphone className="h-4 w-4" />
            Generate Alerts
          </Button>
        </div>
      </div>

      {toast && (
        <AlertNote tone={toast.startsWith("⚠️") ? "warning" : "success"}>{toast}</AlertNote>
      )}

      {data.action_plan && (
        <AlertNote tone="warning" title={`Heat Action Plan #${data.action_plan.id} is ${data.action_plan.status}`}>
          {data.action_plan.summary}
        </AlertNote>
      )}

      {role !== "officer" && (
        <AlertNote tone="info" title={`Viewing as ${ROLE_META[role].label}`}>
          {ROLE_META[role].focus}. Recommended actions below are filtered to your department
          {ROLE_META[role].departments.length > 0 ? ` (${ROLE_META[role].departments.join(", ")})` : ""}.
        </AlertNote>
      )}

      {/* risk strip */}
      <Card className="overflow-hidden">
        <div className="grid grid-cols-5">
          {(["green", "yellow", "orange", "red", "maroon"] as RiskKey[]).map((k) => (
            <div key={k} className="border-r border-white/20 p-3 text-center last:border-r-0"
              style={{ backgroundColor: RISK_META[k].color }}>
              <p className="text-[10px] font-semibold uppercase tracking-wide text-white/90">{RISK_META[k].label}</p>
              <p className="text-2xl font-extrabold text-white">{risk.ward_counts[k]}</p>
              <p className="text-[10px] text-white/80">wards</p>
            </div>
          ))}
        </div>
      </Card>

      {/* KPI grid */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <MetricCard label="Temperature" value={fmt(cc.t)} unit="°C" icon={<Thermometer className="h-4 w-4 text-sky-500" />} tooltip={ICON_TOOLTIPS.t} sub={`min ${data.wards.length ? "—" : "—"} · observed ${fmtTime(cc.observed_at)}`} />
        <MetricCard label="Relative humidity" value={fmt(cc.rh)} unit="%" icon={<Droplets className="h-4 w-4 text-cyan-500" />} tooltip={ICON_TOOLTIPS.rh} />
        <MetricCard label="Wind speed" value={fmt(cc.wind)} unit="m/s" icon={<Wind className="h-4 w-4 text-teal-500" />} tooltip={ICON_TOOLTIPS.wind} sub={`dir ${Math.round(cc.wind_dir)}°`} />
        <MetricCard label="Solar radiation" value={fmt(cc.solar, 0)} unit="W/m²" icon={<Radiation className="h-4 w-4 text-amber-500" />} tooltip={ICON_TOOLTIPS.solar} sub={`cloud ${fmt(cc.cloud, 0)}%`} />
        <MetricCard label="Heat Index" value={fmt(cc.hi)} unit="°C" accent={cc.hi > 45 ? "#dc2626" : cc.hi > 38 ? "#f97316" : "#16a34a"} icon={<Flame className="h-4 w-4 text-orange-500" />} tooltip={ICON_TOOLTIPS.hi} />
        <MetricCard label="Estimated WBGT" value={fmt(cc.wbgt)} unit="°C" accent={cc.wbgt > 32 ? "#dc2626" : cc.wbgt > 28 ? "#f97316" : "#16a34a"} icon={<Sun className="h-4 w-4 text-red-500" />} tooltip={ICON_TOOLTIPS.wbgt} sub="outdoor estimate" />
        <MetricCard label="UTCI Proxy" value={fmt(cc.utci_proxy)} unit="°C" icon={<Gauge className="h-4 w-4 text-violet-500" />} tooltip={ICON_TOOLTIPS.utci} sub="not official UTCI" />
        <MetricCard label="HTSI" value={fmt(cc.htsi ?? 0)} unit="/100" accent={(cc.htsi ?? 0) > 60 ? "#dc2626" : (cc.htsi ?? 0) > 40 ? "#f97316" : "#16a34a"} icon={<Activity className="h-4 w-4 text-rose-500" />} tooltip={ICON_TOOLTIPS.htsi} sub="Human Thermal Stress Index" />
        <MetricCard label="High-risk wards" value={risk.high_risk_wards} unit={`/ ${data.wards.length}`} icon={<AlertTriangle className="h-4 w-4 text-red-500" />} tooltip="Wards at Very High or Extreme risk" sub={risk.high_risk_ward_names.slice(0, 3).join(", ") || "none"} />
        <MetricCard label="People exposed" value={fmtInt(risk.people_exposed)} icon={<Users className="h-4 w-4 text-slate-500" />} tooltip="Population in wards at High risk or above" sub={`${fmtInt(risk.vulnerable_exposed)} vulnerable (elderly + outdoor workers)`} />
        <MetricCard label="Hospital load ↑" value={data.health.demand_range_pct} unit="%" accent="#dc2626" icon={<Activity className="h-4 w-4 text-red-500" />} tooltip="Predicted increase in health demand above baseline (decision-support estimate)" sub={data.health.label.split("(")[0].trim()} />
        <MetricCard label="Active alerts" value={data.alerts.active} icon={<BellRing className="h-4 w-4 text-amber-500" />} tooltip="Draft alerts not yet sent" sub={data.alerts.active ? "drafts ready to send" : "no drafts — generate alerts"} />
      </div>

      {/* severe window + recommended actions */}
      <div className="grid gap-3 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Timer className="h-4 w-4 text-orange-500" /> Upcoming severe-risk period
            </CardTitle>
            <CardDescription>Next day when WBGT reaches ≥ 30 °C city-wide</CardDescription>
          </CardHeader>
          <CardContent>
            {data.severe_window ? (
              <div className="flex flex-wrap items-center gap-4">
                <div className="rounded-xl bg-orange-50 px-5 py-4 text-center">
                  <p className="text-[11px] font-semibold uppercase text-orange-700">{fmtDate(data.severe_window.date)}</p>
                  <p className="text-2xl font-extrabold text-orange-700">
                    {data.severe_window.start}–{data.severe_window.end}
                  </p>
                  <p className="text-[11px] text-orange-600">peak WBGT {fmt(data.severe_window.peak_wbgt)}°C</p>
                </div>
                <div className="flex-1 text-xs leading-relaxed text-slate-600">
                  Dangerous conditions are expected during the late morning and afternoon.
                  Schedule outdoor work outside these hours and prepare cooling centres and
                  hydration points ahead of the window.
                </div>
              </div>
            ) : (
              <p className="text-sm text-slate-500">No severe-risk window in the 5-day forecast.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CloudSun className="h-4 w-4 text-sky-500" /> Recommended city actions
            </CardTitle>
            <CardDescription>Based on the current city risk level ({risk.city_label})</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="mb-2 flex items-center gap-2 text-[11px] text-slate-500">
              <Badge className="bg-slate-900 text-white">{ROLE_META[role].short}</Badge>
              {role === "officer" ? "All departments" : `Filtered: ${ROLE_META[role].departments.join(", ")} department`}
            </div>
            <div className="space-y-2">
              {roleActions.map((a, i) => (
                <div key={i} className="flex items-center justify-between gap-2 rounded-lg bg-slate-50 p-2.5">
                  <div>
                    <p className="text-xs font-semibold text-slate-800">{a.title}</p>
                    <p className="text-[10px] text-slate-500">{a.department}</p>
                  </div>
                  <Badge variant={a.priority === "Immediate" ? "destructive" : a.priority === "Today" ? "secondary" : "outline"}>
                    {a.priority}
                  </Badge>
                </div>
              ))}
            </div>
            <Link to="/map" className="mt-3 inline-block text-xs font-semibold text-slate-900 hover:underline">
              View ward-level actions on the GIS map →
            </Link>
          </CardContent>
        </Card>
      </div>

      {/* forecast + ward overview */}
      <div className="grid gap-3 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <ForecastChart city={data.city.name} />
        </div>
        <Card>
          <CardHeader>
            <CardTitle>Ward risk overview</CardTitle>
            <CardDescription>Tap a ward to open details</CardDescription>
          </CardHeader>
          <CardContent className="scroll-thin max-h-72 space-y-1 overflow-y-auto">
            {[...data.wards].sort((a, b) => b.score - a.score).map((w) => (
              <Link key={w.id} to={`/ward/${w.id}`}
                className="flex items-center justify-between gap-2 rounded-lg px-2 py-1.5 text-xs hover:bg-slate-50">
                <span className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: RISK_META[w.level].color }} />
                  <span className="font-medium text-slate-800">{w.code} · {w.name}</span>
                </span>
                <span className="text-slate-400">{Math.round(w.score)}/100</span>
              </Link>
            ))}
          </CardContent>
        </Card>
      </div>

      <DisclaimerFooter extra={data.disclaimers.slice(4)} />
    </div>
  );
}

function ForecastChart({ city }: { city: string }) {
  const { data, loading, error } = useApi(() => api.trends());
  if (loading) return <Card><CardHeader><CardTitle>5-day forecast</CardTitle></CardHeader><CardContent><Spinner /></CardContent></Card>;
  if (error || !data) return <Card><CardContent><ErrorState message={error || ""} /></CardContent></Card>;
  const series = data.forecast.map((d) => ({
    label: fmtDate(d.date).split(",")[0],
    tmax: d.tmax, hi_max: d.hi_max, wbgt_max: d.wbgt_max, utci_max: d.utci_max, htsi: d.htsi,
  }));
  return (
    <ChartCard title={`5-day forecast — ${city}`} description="Maximum temperature, Heat Index, estimated WBGT, UTCI proxy and HTSI">
      <MultiLine
        data={series}
        series={[
          { key: "tmax", name: "T max" },
          { key: "hi_max", name: "Heat Index" },
          { key: "wbgt_max", name: "Est. WBGT" },
          { key: "utci_max", name: "UTCI proxy" },
          { key: "htsi", name: "HTSI" },
        ]}
      />
    </ChartCard>
  );
}