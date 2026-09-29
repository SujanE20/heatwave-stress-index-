"use client";

import { Card, InfoTip } from "@/components/ui";
import { cn } from "@/lib/utils";

export default function MetricCard({
  label,
  value,
  unit,
  sub,
  icon,
  tooltip,
  accent,
  className,
}: {
  label: string;
  value: string | number;
  unit?: string;
  sub?: string;
  icon?: React.ReactNode;
  tooltip?: string;
  accent?: string;
  className?: string;
}) {
  return (
    <Card className={cn("relative overflow-hidden p-4", className)}>
      {accent && (
        <span aria-hidden className="absolute inset-x-0 top-0 h-1" style={{ backgroundColor: accent }} />
      )}
      <div className="flex items-start justify-between gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
          {label}
          {tooltip && <InfoTip text={tooltip} />}
        </p>
        {icon}
      </div>
      <p className="mt-1.5 text-2xl font-bold text-slate-900">
        {value}
        {unit && <span className="ml-1 text-sm font-medium text-slate-500">{unit}</span>}
      </p>
      {sub && <p className="mt-0.5 text-[11px] text-slate-500">{sub}</p>}
    </Card>
  );
}