"use client";

import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, ReferenceLine,
  ResponsiveContainer, Scatter, ScatterChart, Tooltip as RTooltip, XAxis, YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui";
import { riskMeta } from "@/lib/utils";
import type { RiskKey } from "@/lib/types";

const AXIS = { fontSize: 11, fill: "#64748b" };

export function ChartCard({
  title,
  description,
  children,
  height = 260,
  className,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
  height?: number;
  className?: string;
}) {
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent>
        <div style={{ height }}>{children}</div>
      </CardContent>
    </Card>
  );
}

const SERIES_COLORS: Record<string, string> = {
  t: "#0ea5e9", apparent: "#818cf8", hi: "#f97316", wbgt: "#dc2626",
  utci_proxy: "#7c3aed", htsi: "#be123c", tmax: "#0ea5e9", tmin: "#38bdf8",
  hi_max: "#f97316", wbgt_max: "#dc2626", utci_max: "#7c3aed",
  load_increase_pct: "#f97316", heat_admissions: "#dc2626",
};

export function MultiLine({
  data,
  series,
  height = 260,
  unit = "°C",
  yDomain,
}: {
  data: any[];
  series: { key: string; name: string }[];
  height?: number;
  unit?: string;
  yDomain?: [number | "auto", number | "auto"];
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -18 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="label" tick={AXIS} tickLine={false} axisLine={{ stroke: "#cbd5e1" }} />
        <YAxis tick={AXIS} tickLine={false} axisLine={false} domain={yDomain ?? ["auto", "auto"]} unit={unit} />
        <RTooltip
          contentStyle={{ borderRadius: 10, border: "1px solid #e2e8f0", fontSize: 12 }}
        />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        {series.map((s) => (
          <Line
            key={s.key}
            type="monotone"
            dataKey={s.key}
            name={s.name}
            stroke={SERIES_COLORS[s.key] || "#0f172a"}
            strokeWidth={2}
            dot={false}
            connectNulls
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

export function RiskBars({ data }: { data: { label: string; risk: number; level: RiskKey }[] }) {
  // Temperature risk bars: value = daily max air temperature (°C); colour =
  // category (Low ≤30 · Moderate 30-35 · High 35-40 · Very High 40-44 · Extreme ≥45).
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -22 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="label" tick={AXIS} tickLine={false} axisLine={{ stroke: "#cbd5e1" }} />
        <YAxis tick={AXIS} tickLine={false} axisLine={false} domain={[20, 50]} unit="°C" />
        <RTooltip
          contentStyle={{ borderRadius: 10, border: "1px solid #e2e8f0", fontSize: 12 }}
          formatter={(v: any) => [`${v} °C`, "Daily max temperature"]}
        />
        <ReferenceLine y={30} stroke="#16a34a" strokeDasharray="4 4" />
        <ReferenceLine y={35} stroke="#eab308" strokeDasharray="4 4" />
        <ReferenceLine y={40} stroke="#f97316" strokeDasharray="4 4" />
        <ReferenceLine y={45} stroke="#7f1d1d" strokeDasharray="4 4" />
        <Bar dataKey="risk" radius={[6, 6, 0, 0]}>
          {data.map((d, i) => (
            <Cell key={i} fill={riskMeta(d.level).color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function ScatterRisk({
  data,
  height = 280,
}: {
  data: { ward: string; x: number; y: number; risk: RiskKey }[];
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <ScatterChart margin={{ top: 8, right: 16, bottom: 4, left: -14 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis type="number" dataKey="x" name="Vulnerability" tick={AXIS} tickLine={false}
          axisLine={{ stroke: "#cbd5e1" }} domain={[0, 100]} unit=" /100" label={{ value: "Vulnerability", position: "insideBottom", offset: -2, fontSize: 10, fill: "#64748b" }} />
        <YAxis type="number" dataKey="y" name="Thermal stress" tick={AXIS} tickLine={false}
          axisLine={false} domain={[0, 100]} label={{ value: "HTSI", angle: -90, position: "insideLeft", offset: 12, fontSize: 10, fill: "#64748b" }} />
        <RTooltip
          cursor={{ strokeDasharray: "3 3" }}
          contentStyle={{ borderRadius: 10, border: "1px solid #e2e8f0", fontSize: 12 }}
          formatter={(v: any, n: any) => [`${v}/100`, n]}
          labelFormatter={(l: any) => {
            const p = data.find((d) => d.ward === l);
            return p ? p.ward : l;
          }}
        />
        <Scatter data={data} dataKey="y">
          {data.map((d, i) => (
            <Cell key={i} fill={riskMeta(d.risk).color} fillOpacity={0.85} />
          ))}
        </Scatter>
      </ScatterChart>
    </ResponsiveContainer>
  );
}

export function TwinBar({
  data,
  keys,
  names,
  colors,
  height = 260,
  unit = "%",
}: {
  data: any[];
  keys: string[];
  names: string[];
  colors: string[];
  height?: number;
  unit?: string;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -18 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="label" tick={AXIS} tickLine={false} axisLine={{ stroke: "#cbd5e1" }} />
        <YAxis tick={AXIS} tickLine={false} axisLine={false} unit={unit} />
        <RTooltip contentStyle={{ borderRadius: 10, border: "1px solid #e2e8f0", fontSize: 12 }} />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        {keys.map((k, i) => (
          <Bar key={k} dataKey={k} name={names[i]} fill={colors[i]} radius={[5, 5, 0, 0]} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}