"use client";

import { Link, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { useRole } from "@/lib/role";
import {
  Activity, Building2, Flame, HeartPulse, Map, Megaphone, Shield, ShieldAlert,
  ThermometerSun, User, Users, Waves,
} from "lucide-react";
import { API_URL } from "@/lib/api";
import { Badge, Card, CardContent } from "@/components/ui";

const ROLES = [
  {
    key: "officer",
    title: "Municipal Command Centre Officer",
    desc: "City-wide risk dashboard, GIS ward map, Heat Action Plan trigger and alerts.",
    href: "/dashboard",
    icon: ShieldAlert,
  },
  {
    key: "hospital",
    title: "Hospital Administrator",
    desc: "Expected heat-related admissions, surge planning and resource stocks.",
    href: "/resources",
    icon: HeartPulse,
  },
  {
    key: "labour",
    title: "Labour Department Officer",
    desc: "Outdoor-worker exposure, work-timing advisories and welfare checks.",
    href: "/map",
    icon: Building2,
  },
  {
    key: "citizen",
    title: "Citizen",
    desc: "Simple, mobile-friendly heat alerts in English and Kannada.",
    href: "/citizen",
    icon: User,
  },
];

const PIPELINE = [
  { icon: ThermometerSun, label: "Weather forecast" },
  { icon: Flame, label: "Human thermal stress" },
  { icon: Users, label: "Ward vulnerability" },
  { icon: Activity, label: "Health-risk estimate" },
  { icon: ShieldAlert, label: "Recommended action" },
  { icon: Megaphone, label: "Citizen & municipal alerts" },
];

export default function LandingPage() {
  const navigate = useNavigate();
  const { setRole } = useRole();
  const [demo, setDemo] = useState(true);
  const [summary, setSummary] = useState<any>(null);

  useEffect(() => {
    fetch(`${API_URL}/api/v1/dashboard/summary`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (d) {
          setSummary(d);
          setDemo(d.weather.is_demo);
        }
      })
      .catch(() => undefined);
  }, []);

  const choose = (role: string, href: string) => {
    setRole(role as any);
    navigate(href);
  };

  return (
    <div className="mx-auto max-w-5xl">
      {/* hero */}
      <section className="relative overflow-hidden rounded-2xl bg-slate-900 px-6 py-12 text-white sm:px-12">
        <div className="pointer-events-none absolute inset-0 opacity-20"
          style={{ background: "radial-gradient(600px 200px at 80% -10%, #f97316, transparent), radial-gradient(500px 200px at 10% 110%, #dc2626, transparent)" }} />
        <div className="relative">
          <div className="flex items-center gap-2">
            <Shield className="h-8 w-8 text-orange-400" />
            <div>
              <h1 className="text-2xl font-extrabold tracking-tight sm:text-3xl">HEATSHIELD INDIA</h1>
              <p className="text-sm text-orange-300">Smart India Hackathon · Heat-Health Early Warning System</p>
            </div>
            {demo && <Badge className="ml-auto bg-amber-500/20 text-amber-300 ring-1 ring-amber-500/40">Demo Data Mode</Badge>}
          </div>
          <p className="mt-5 max-w-2xl text-lg font-medium leading-snug text-slate-100">
            “Predicting what heat will do to <span className="text-orange-300">people</span>,
            not just what the weather will be.”
          </p>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-slate-300">
            HEATSHIELD transforms a 5-day weather forecast into ward-level human thermal stress,
            vulnerability, hospitalization-risk estimates and concrete municipal actions — for
            Mysore today, and any Indian city tomorrow.
          </p>
          <div className="mt-6 flex flex-wrap items-center gap-2">
            {PIPELINE.map((p, i) => (
              <span key={p.label} className="flex items-center gap-1.5 text-[11px] font-medium text-slate-200">
                <p.icon className="h-3.5 w-3.5 text-orange-300" />
                {p.label}
                {i < PIPELINE.length - 1 && <Waves className="ml-1 h-3 w-3 text-slate-500" />}
              </span>
            ))}
          </div>
          {summary && (
            <div className="mt-6 flex flex-wrap gap-4 rounded-xl bg-white/5 p-4 text-xs">
              <div>
                <p className="text-slate-400">City</p>
                <p className="font-semibold">{summary.city.name}</p>
              </div>
              <div>
                <p className="text-slate-400">Current conditions</p>
                <p className="font-semibold">{summary.current_conditions.t}°C · HI {summary.current_conditions.hi}°C · WBGT {summary.current_conditions.wbgt}°C</p>
              </div>
              <div>
                <p className="text-slate-400">City risk</p>
                <p className="font-semibold text-orange-300">
                  {summary.risk.city_label} ·{" "}
                  {(() => {
                    const names: Record<string, string> = {
                      green: "Low", yellow: "Moderate", orange: "High", red: "Very High", maroon: "Extreme",
                    };
                    const parts = Object.entries(summary.risk.ward_counts)
                      .filter(([, n]) => (n as number) > 0)
                      .map(([k, n]) => `${n} ${names[k] ?? k}`);
                    return parts.length ? parts.join(", ") : "no ward data";
                  })()}
                </p>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* role selection */}
      <section className="mt-10">
        <h2 className="mb-4 text-center text-sm font-bold uppercase tracking-widest text-slate-500">
          Choose your role to enter the platform
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {ROLES.map((r) => (
            <Card key={r.key} className="group cursor-pointer transition-all hover:-translate-y-0.5 hover:shadow-lg">
              <button className="w-full text-left" onClick={() => choose(r.key, r.href)}>
                <CardContent className="flex h-full flex-col p-5">
                  <span className="mb-3 inline-flex h-11 w-11 items-center justify-center rounded-xl bg-slate-900 text-white transition-colors group-hover:bg-orange-600">
                    <r.icon className="h-5 w-5" />
                  </span>
                  <p className="text-sm font-bold text-slate-900">{r.title}</p>
                  <p className="mt-1.5 flex-1 text-xs leading-relaxed text-slate-500">{r.desc}</p>
                  <p className="mt-3 text-xs font-semibold text-orange-600 group-hover:underline">Enter platform →</p>
                </CardContent>
              </button>
            </Card>
          ))}
        </div>
      </section>

      <section className="mt-8 grid gap-3 sm:grid-cols-3">
        <Link to="/map" className="rounded-xl border border-slate-200 bg-white p-4 text-sm font-medium text-slate-700 hover:border-slate-400">
          🗺️ Interactive GIS ward map
        </Link>
        <Link to="/analytics" className="rounded-xl border border-slate-200 bg-white p-4 text-sm font-medium text-slate-700 hover:border-slate-400">
          📈 5-day forecast & analytics
        </Link>
        <Link to="/admin" className="rounded-xl border border-slate-200 bg-white p-4 text-sm font-medium text-slate-700 hover:border-slate-400">
          ⚙️ Admin settings & demo model
        </Link>
      </section>

      <p className="mt-8 text-center text-[11px] text-slate-400">
        Decision-support prototype — must be calibrated with local meteorological and public-health data before operational deployment.
      </p>
    </div>
  );
}