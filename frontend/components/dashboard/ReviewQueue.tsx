import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { RiskBadge, CaseStatusBadge } from "@/components/ui/status-badges";
import { EmptyState } from "@/components/ui/empty-state";
import { formatCurrency } from "@/lib/utils";
import type { CaseSummary } from "@/types";
import { Inbox } from "lucide-react";

export function ReviewQueue({ cases }: { cases: CaseSummary[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Review Queue</CardTitle>
        <CardDescription>Open cases sorted by risk score</CardDescription>
      </CardHeader>
      <CardContent>
        {cases.length === 0 ? (
          <EmptyState icon={Inbox} title="Queue is empty" description="No cases currently need review." />
        ) : (
          <div className="flex flex-col divide-y divide-slate-100">
            {cases.map((c) => (
              <Link
                key={c.id}
                href={`/cases/${c.id}`}
                className="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0 hover:bg-slate-50"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-900">{c.case_number}</p>
                  <p className="truncate text-xs text-slate-500">
                    {c.vendor_name || "Unknown vendor"} · {formatCurrency(c.total_amount, c.currency ?? undefined)}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  {c.violation_count > 0 && (
                    <span className="text-xs font-medium text-red-600">{c.violation_count} violation(s)</span>
                  )}
                  <CaseStatusBadge status={c.status} />
                  <RiskBadge level={c.risk_level} />
                </div>
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
