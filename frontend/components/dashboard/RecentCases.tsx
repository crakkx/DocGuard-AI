import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { RiskBadge, CaseStatusBadge } from "@/components/ui/status-badges";
import { EmptyState } from "@/components/ui/empty-state";
import { formatCurrency, formatDate } from "@/lib/utils";
import type { CaseSummary } from "@/types";
import { FolderClock } from "lucide-react";

export function RecentCases({ cases }: { cases: CaseSummary[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Cases</CardTitle>
      </CardHeader>
      <CardContent>
        {cases.length === 0 ? (
          <EmptyState icon={FolderClock} title="No cases yet" description="Upload PO / Invoice / GRN documents to create cases." />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Case</TableHead>
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
                    <Link href={`/cases/${c.id}`} className="font-medium text-slate-900 hover:underline">
                      {c.case_number}
                    </Link>
                  </TableCell>
                  <TableCell className="text-slate-600">{c.vendor_name || "—"}</TableCell>
                  <TableCell className="text-slate-600">
                    {formatCurrency(c.total_amount, c.currency ?? undefined)}
                  </TableCell>
                  <TableCell>
                    <CaseStatusBadge status={c.status} />
                  </TableCell>
                  <TableCell>
                    <RiskBadge level={c.risk_level} />
                  </TableCell>
                  <TableCell className="text-slate-500">{formatDate(c.created_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
