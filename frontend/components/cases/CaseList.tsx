"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EmptyState } from "@/components/ui/empty-state";
import { RiskBadge, CaseStatusBadge } from "@/components/ui/status-badges";
import { formatCurrency, formatDate } from "@/lib/utils";
import type { CaseSummary } from "@/types";
import { Eye, FolderSearch, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useDeleteCase } from "@/hooks/useCases";

export function CaseList({ cases }: { cases: CaseSummary[] }) {
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const { mutateAsync: deleteCase } = useDeleteCase();

  if (cases.length === 0) {
    return (
      <div className="p-8">
        <EmptyState
          icon={FolderSearch}
          title="No cases found"
          description="Try adjusting your filters or search term."
        />
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="whitespace-nowrap text-center min-w-[140px]">Case ID</TableHead>
          <TableHead className="whitespace-nowrap text-center min-w-[170px]">Vendor</TableHead>
          <TableHead className="whitespace-nowrap text-center min-w-[130px]">PO / Invoice</TableHead>
          <TableHead className="whitespace-nowrap text-center min-w-[110px]">Amount</TableHead>
          <TableHead className="whitespace-nowrap text-center min-w-[120px]">Status</TableHead>
          <TableHead className="whitespace-nowrap text-center min-w-[90px]">Risk</TableHead>
          <TableHead className="whitespace-nowrap text-center min-w-[140px]">Findings</TableHead>
          <TableHead className="whitespace-nowrap text-center min-w-[110px]">Created</TableHead>
          <TableHead className="whitespace-nowrap text-center min-w-[100px]">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {cases.map((c) => (
          <TableRow key={c.id}>
            <TableCell className="whitespace-nowrap font-mono text-center">
              <div className="flex items-center justify-center">
                <Link
                  href={`/cases/${c.id}`}
                  className="inline-flex items-center rounded-md bg-blue-50/80 px-2.5 py-1 font-mono text-xs font-semibold text-blue-700 border border-blue-200/60 hover:bg-blue-100 transition-colors whitespace-nowrap"
                >
                  {c.case_number}
                </Link>
              </div>
            </TableCell>
            <TableCell className="font-medium text-slate-900 whitespace-nowrap text-center">
              {c.vendor_name || "—"}
            </TableCell>
            <TableCell className="whitespace-nowrap text-center">
              <div className="flex flex-col items-center justify-center gap-1 text-xs whitespace-nowrap">
                {c.po_number && (
                  <span className="font-mono text-slate-700 font-medium whitespace-nowrap">
                    {c.po_number}
                  </span>
                )}
                {c.invoice_number && (
                  <span className="font-mono text-slate-400 whitespace-nowrap">
                    {c.invoice_number}
                  </span>
                )}
                {!c.po_number && !c.invoice_number && (
                  <span className="text-slate-400">—</span>
                )}
              </div>
            </TableCell>
            <TableCell className="font-semibold text-slate-900 tabular-nums whitespace-nowrap text-center">
              {c.total_amount != null ? formatCurrency(c.total_amount, c.currency ?? undefined) : "—"}
            </TableCell>
            <TableCell className="whitespace-nowrap text-center">
              <div className="flex items-center justify-center">
                <CaseStatusBadge status={c.status} />
              </div>
            </TableCell>
            <TableCell className="whitespace-nowrap text-center">
              <div className="flex items-center justify-center">
                <RiskBadge level={c.risk_level} />
              </div>
            </TableCell>
            <TableCell className="whitespace-nowrap text-center">
              <div className="flex items-center justify-center">
                {c.violation_count > 0 ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-semibold text-red-700 border border-red-200/80 whitespace-nowrap">
                    {c.findings_count} ({c.violation_count} {c.violation_count === 1 ? "violation" : "violations"})
                  </span>
                ) : (
                  <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600 whitespace-nowrap">
                    {c.findings_count} {c.findings_count === 1 ? "finding" : "findings"}
                  </span>
                )}
              </div>
            </TableCell>
            <TableCell className="text-xs text-slate-500 tabular-nums whitespace-nowrap text-center">
              {formatDate(c.created_at)}
            </TableCell>
            <TableCell className="whitespace-nowrap text-center">
              <div className="flex items-center justify-center gap-2">
                <Button
                  asChild
                  variant="outline"
                  size="sm"
                  className="h-8 w-8 p-0 text-slate-500 hover:text-blue-600 hover:bg-blue-50 border-slate-200"
                  title="Review case"
                >
                  <Link href={`/cases/${c.id}`} className="flex items-center justify-center">
                    <Eye className="h-4 w-4" />
                  </Link>
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={deletingId === c.id}
                  className="h-8 w-8 p-0 text-slate-400 hover:text-red-600 hover:bg-red-50"
                  title="Delete case"
                  onClick={async (e) => {
                    e.stopPropagation();
                    if (!confirm(`Delete case ${c.case_number}? All findings and audit entries will be permanently removed.`)) return;
                    setDeletingId(c.id);
                    try {
                      await deleteCase(c.id);
                    } catch (err) {
                      alert('Failed to delete case: ' + (err instanceof Error ? err.message : String(err)));
                    } finally {
                      setDeletingId(null);
                    }
                  }}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
