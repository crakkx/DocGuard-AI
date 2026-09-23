import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { CaseSummary } from "@/types";
import { cn } from "@/lib/utils";

const LEVELS: { key: string; label: string; barClass: string }[] = [
  { key: "CRITICAL", label: "Critical", barClass: "bg-red-500" },
  { key: "HIGH", label: "High", barClass: "bg-orange-500" },
  { key: "MEDIUM", label: "Medium", barClass: "bg-blue-500" },
  { key: "LOW", label: "Low", barClass: "bg-emerald-500" },
];

export function RiskDistribution({ cases }: { cases: CaseSummary[] }) {
  const total = cases.length || 1;
  const counts = LEVELS.map((l) => ({
    ...l,
    count: cases.filter((c) => (c.risk_level || "LOW").toUpperCase() === l.key).length,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Risk Distribution</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {counts.map((l) => (
          <div key={l.key} className="flex items-center gap-3">
            <span className="w-16 shrink-0 text-xs font-medium text-slate-600">{l.label}</span>
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
              <div
                className={cn("h-full rounded-full", l.barClass)}
                style={{ width: `${(l.count / total) * 100}%` }}
              />
            </div>
            <span className="w-6 shrink-0 text-right text-xs text-slate-500">{l.count}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
