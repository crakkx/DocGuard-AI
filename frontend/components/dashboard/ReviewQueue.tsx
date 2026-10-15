import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { RiskBadge, CaseStatusBadge } from "@/components/ui/status-badges";
import { EmptyState } from "@/components/ui/empty-state";
import { formatCurrency } from "@/lib/utils";
import type { CaseSummary } from "@/types";
import { Inbox, ChevronRight } from "lucide-react";

export function ReviewQueue({ cases }: { cases: CaseSummary[] }) {
  return (
    <Card>
      <CardHeader>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <CardTitle>Review Queue</CardTitle>
            <CardDescription>Open cases sorted by risk score</CardDescription>
          </div>
          <span style={{
            display: "flex", alignItems: "center", justifyContent: "center",
            width: 22, height: 22, borderRadius: 99,
            background: "#EFF6FF", color: "#3B82F6",
            fontSize: 11, fontWeight: 700,
          }}>
            {cases.length}
          </span>
        </div>
      </CardHeader>
      <CardContent>
        {cases.length === 0 ? (
          <EmptyState icon={Inbox} title="Queue is empty" description="No cases currently need review." />
        ) : (
          <div style={{ display: "flex", flexDirection: "column" }}>
            {cases.map((c) => (
              <Link
                key={c.id}
                href={`/cases/${c.id}`}
                className="dg-queue-row"
              >
                <div style={{ minWidth: 0, flex: 1 }}>
                  <p style={{ fontSize: 13.5, fontWeight: 600, color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {c.case_number}
                  </p>
                  <p style={{ fontSize: 11.5, color: "var(--text-muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", marginTop: 1 }}>
                    {c.vendor_name || "Unknown vendor"} · {formatCurrency(c.total_amount, c.currency ?? undefined)}
                  </p>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 7, flexShrink: 0 }}>
                  {c.violation_count > 0 && (
                    <span style={{
                      fontSize: 11, fontWeight: 600, color: "#EF4444",
                      background: "#FFF1F2",
                      padding: "2px 7px", borderRadius: 99,
                    }}>
                      {c.violation_count} issue{c.violation_count !== 1 ? "s" : ""}
                    </span>
                  )}
                  <CaseStatusBadge status={c.status} />
                  <RiskBadge level={c.risk_level} />
                  <ChevronRight size={13} color="var(--text-muted)" />
                </div>
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
