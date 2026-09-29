"use client";

import { Link, useLocation, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import {
  Activity, Building2, FlaskConical, HeartPulse, Hospital, Map, MapPin, Megaphone,
  Shield, ShieldAlert, User, Wrench, ArrowLeftRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { API_URL } from "@/lib/api";
import { Badge } from "@/components/ui";
import { ROLE_META, useRole, type Role } from "@/lib/role";

const LINKS = [
  { href: "/dashboard", label: "Command Centre", icon: Activity },
  { href: "/map", label: "GIS Risk Map", icon: Map },
  { href: "/hyperlocal", label: "Hyperlocal Map", icon: MapPin },
  { href: "/analytics", label: "Forecast & Analytics", icon: FlaskConical },
  { href: "/alerts", label: "Alerts Centre", icon: Megaphone },
  { href: "/resources", label: "Resources", icon: Hospital },
  { href: "/citizen", label: "Citizen View", icon: User },
  { href: "/admin", label: "Admin Settings", icon: Wrench },
];

export default function NavBar() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { role, setRole } = useRole();
  const [demo, setDemo] = useState(true);
  const [scenario, setScenario] = useState("");

  useEffect(() => {
    fetch(`${API_URL}/api/v1/settings`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (d) {
          setDemo(d.settings.weather_provider === "demo");
          setScenario(d.settings.demo_scenario);
        }
      })
      .catch(() => setDemo(true));
  }, []);

  const changeRole = (key: string) => {
    const r = key as Role;
    if (r === role) return;
    setRole(r);
    navigate(ROLE_META[r].home);
  };

  const isCitizen = role === "citizen";
  const visibleLinks = isCitizen ? LINKS.filter((l) => l.href === "/citizen") : LINKS;

  return (
    <header className="sticky top-0 z-40 border-b border-slate-800 bg-slate-900 text-white no-print">
      <div className="mx-auto flex max-w-[1500px] items-center gap-4 px-4 py-2.5 sm:px-6">
        <Link to={isCitizen ? "/citizen" : "/"} className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-orange-500 to-red-600">
            <Shield className="h-5 w-5 text-white" />
          </span>
          <span className="leading-tight">
            <span className="block text-sm font-bold tracking-wide">HEATSHIELD INDIA</span>
            <span className="block text-[10px] text-slate-400">
              {isCitizen ? "Citizen heat alerts" : "Predicting what heat will do to people"}
            </span>
          </span>
        </Link>

        <nav className="hidden items-center gap-1 lg:flex">
          {visibleLinks.map((l) => (
            <Link
              key={l.href}
              to={l.href}
              className={cn(
                "flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors",
                pathname === l.href || pathname.startsWith(l.href + "/")
                  ? "bg-slate-800 text-white"
                  : "text-slate-400 hover:bg-slate-800 hover:text-white"
              )}
            >
              <l.icon className="h-3.5 w-3.5" />
              {l.label}
            </Link>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          {demo && (
            <Badge className="bg-amber-500/15 text-amber-300 ring-1 ring-amber-500/40" title="Offline demo weather generator active">
              Demo Data
              {scenario && <span className="ml-1 hidden text-amber-400/80 sm:inline">· {scenario.replace(/_/g, " ")}</span>}
            </Badge>
          )}
          <span className="hidden items-center gap-1 text-[11px] text-slate-400 sm:flex">
            <ArrowLeftRight className="h-3 w-3" />
            Role
          </span>
          <select
            aria-label="Select your role"
            value={role}
            onChange={(e) => changeRole(e.target.value)}
            className="h-8 rounded-lg border border-slate-700 bg-slate-800 px-2 text-xs text-slate-200 focus:outline-none"
          >
            {Object.entries(ROLE_META).map(([key, meta]) => (
              <option key={key} value={key}>
                {meta.label}
              </option>
            ))}
          </select>
        </div>
      </div>
      {/* mobile nav */}
      <nav className="flex items-center gap-1 overflow-x-auto border-t border-slate-800 px-3 py-1.5 lg:hidden">
        {visibleLinks.map((l) => (
          <Link
            key={l.href}
            to={l.href}
            className={cn(
              "whitespace-nowrap rounded-md px-2 py-1 text-[11px] font-medium",
              pathname === l.href ? "bg-slate-800 text-white" : "text-slate-400"
            )}
          >
            {l.label}
          </Link>
        ))}
      </nav>
    </header>
  );
}