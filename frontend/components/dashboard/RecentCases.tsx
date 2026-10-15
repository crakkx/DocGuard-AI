import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { RiskBadge, CaseStatusBadge } from "@/components/ui/status-badges";
import { EmptyState } from "@/components/ui/empty-state";
import { formatCurrency, formatDate } from "@/lib/utils";
import type { CaseSummary } from "@/types";
import { ArrowRight, FolderOpen } from "lucide-react";

export function RecentCases({ cases }: { cases: CaseSummary[] }) {
  return (
    <Card className="overflow-hidden border border-slate-200/90 shadow-sm">
      <CardHeader className="border-b border-slate-100 bg-white py-4 px-6">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base font-semibold text-slate-900">Recent Cases</CardTitle>
            <p className="text-xs text-slate-500 mt-0.5">Recently reviewed and audited procurement cases</p>
          </div>
          <Link
            href="/cases"
            className="inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-700 transition-colors"
          >
            View all
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        {cases.length === 0 ? (
          <div className="p-8">
            <EmptyState
              icon={FolderOpen}
              title="No cases yet"
              description="Upload PO / Invoice / GRN documents to create cases."
            />
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Case ID</TableHead>
                <TableHead>Vendor</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Risk</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {cases.map((c) => (
                <TableRow key={c.id}>
                  <TableCell>
                    <Link
                      href={`/cases/${c.id}`}
                      className="inline-flex items-center rounded-md bg-blue-50/80 px-2.5 py-1 font-mono text-xs font-semibold text-blue-700 border border-blue-200/60 hover:bg-blue-100 transition-colors"
                    >
                      {c.case_number}
                    </Link>
                  </TableCell>
                  <TableCell className="font-medium text-slate-900">
                    {c.vendor_name || "—"}
                  </TableCell>
                  <TableCell className="font-semibold text-slate-900 tabular-nums">
                    {formatCurrency(c.total_amount, c.currency ?? undefined)}
                  </TableCell>
                  <TableCell>
                    <CaseStatusBadge status={c.status} />
                  </TableCell>
                  <TableCell>
                    <RiskBadge level={c.risk_level} />
                  </TableCell>
                  <TableCell className="text-xs text-slate-500 tabular-nums">
                    {formatDate(c.created_at)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
