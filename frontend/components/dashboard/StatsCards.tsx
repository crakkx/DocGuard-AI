import { Briefcase, ShieldAlert, ShieldCheck, ClipboardList, AlertOctagon, FileCheck2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { DashboardStats } from "@/types";
import { cn } from "@/lib/utils";

const CARDS: {
  key: keyof DashboardStats;
  label: string;
  icon: typeof Briefcase;
  tone: string;
}[] = [
  { key: "total_cases", label: "Total Cases", icon: Briefcase, tone: "text-slate-700 bg-slate-100" },
  { key: "compliant_cases", label: "Compliant", icon: ShieldCheck, tone: "text-emerald-700 bg-emerald-100" },
  { key: "violation_cases", label: "Violations", icon: ShieldAlert, tone: "text-red-700 bg-red-100" },
  { key: "needs_review_cases", label: "Needs Review", icon: ClipboardList, tone: "text-amber-700 bg-amber-100" },
  { key: "high_risk_cases", label: "High Risk", icon: AlertOctagon, tone: "text-orange-700 bg-orange-100" },
  { key: "pending_rules", label: "Pending Rules", icon: FileCheck2, tone: "text-violet-700 bg-violet-100" },
];

export function StatsCards({ stats }: { stats: DashboardStats }) {
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
      {CARDS.map(({ key, label, icon: Icon, tone }) => (
        <Card key={key}>
          <CardContent className="flex flex-col gap-3 p-4">
            <div className={cn("flex h-8 w-8 items-center justify-center rounded-md", tone)}>
              <Icon className="h-4 w-4" />
            </div>
            <div>
              <p className="text-2xl font-semibold text-slate-900">{stats[key] as number}</p>
              <p className="text-xs text-slate-500">{label}</p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
