"use client";

// Role-based access context. The selected role drives navigation, the nav
// links shown, and which department's actions are highlighted on dashboards.

import { createContext, useContext, useEffect, useState } from "react";

export type Role = "officer" | "hospital" | "labour" | "citizen";

export const ROLE_META: Record<
  Role,
  { label: string; short: string; home: string; departments: string[]; focus: string }
> = {
  officer: {
    label: "Municipal Command Centre Officer",
    short: "Command Centre",
    home: "/dashboard",
    departments: [], // all
    focus: "City-wide coordination: alerts, cooling centres, water, public awareness",
  },
  hospital: {
    label: "Hospital Administrator",
    short: "Hospital",
    home: "/resources",
    departments: ["Health"],
    focus: "Surge planning, PHC supplies, emergency staffing, heat admissions",
  },
  labour: {
    label: "Labour Department Officer",
    short: "Labour",
    home: "/map",
    departments: ["Labour"],
    focus: "Outdoor-worker exposure, work-timing advisories, welfare checks",
  },
  citizen: {
    label: "Citizen",
    short: "Citizen",
    home: "/citizen",
    departments: [],
    focus: "Personal safety: hydration, cooling centres, ward alerts",
  },
};

const STORAGE_KEY = "heatshield-role";

interface RoleCtx {
  role: Role;
  setRole: (r: Role) => void;
}

const RoleContext = createContext<RoleCtx | null>(null);

export function RoleProvider({ children }: { children: React.ReactNode }) {
  const [role, setRoleState] = useState<Role>("officer");

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY) as Role | null;
      if (saved && saved in ROLE_META) setRoleState(saved);
    } catch {
      /* storage unavailable */
    }
  }, []);

  const setRole = (r: Role) => {
    setRoleState(r);
    try {
      localStorage.setItem(STORAGE_KEY, r);
    } catch {
      /* ignore */
    }
  };

  return <RoleContext.Provider value={{ role, setRole }}>{children}</RoleContext.Provider>;
}

export function useRole(): RoleCtx {
  const ctx = useContext(RoleContext);
  if (!ctx) throw new Error("useRole must be used within RoleProvider");
  return ctx;
}

/** Filter actions by the current role's departments (empty list = all). */
export function filterActionsByRole<T extends { department?: string }>(role: Role, actions: T[]): T[] {
  const deps = ROLE_META[role].departments;
  if (role === "officer" || deps.length === 0) return actions;
  return actions.filter((a) => deps.some((d) => (a.department ?? "").toLowerCase().includes(d.toLowerCase())));
}