'use client';

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
import { FolderSearch } from "lucide-react";

export function CaseList({ cases }: { cases: CaseSummary[] }) {
  if (cases.length === 0) {
    return (
      <EmptyState
        icon={FolderSearch}
        title="No cases found"
        description="Try adjusting your filters or search term."
      />
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Case</TableHead>
          <TableHead>Vendor</TableHead>
          <TableHead>PO / Invoice</TableHead>
          <TableHead>Amount</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Risk</TableHead>
          <TableHead>Findings</TableHead>
          <TableHead>Created</TableHead>
          <TableHead className="text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {cases.map((c) => (
          <TableRow key={c.id}>
            <TableCell>
              <Link
                href={`/cases/${c.id}`}
                className="font-medium text-slate-900 hover:underline"
              >
                {c.case_number}
              </Link>
            </TableCell>
            <TableCell className="text-slate-600">{c.vendor_name || "—"}</TableCell>
            <TableCell className="text-slate-600">
              <div className="flex flex-col text-xs">
                <span>{c.po_number || "—"}</span>
                <span className="text-slate-400">{c.invoice_number || "—"}</span>
              </div>
            </TableCell>
            <TableCell className="text-slate-600">
              {formatCurrency(c.total_amount, c.currency ?? undefined)}
            </TableCell>
            <TableCell>
              <CaseStatusBadge status={c.status} />
            </TableCell>
            <TableCell>
              <RiskBadge level={c.risk_level} />
            </TableCell>
            <TableCell className="text-slate-600">
              {c.findings_count}
              {c.violation_count > 0 && (
                <span className="text-red-600"> ({c.violation_count} violation{c.violation_count === 1 ? "" : "s"})</span>
              )}
            </TableCell>
            <TableCell className="text-slate-500">{formatDate(c.created_at)}</TableCell>
            <TableCell className="text-right">
              <button
                className="text-xs text-red-600 hover:text-red-800 border border-red-200 hover:border-red-400 rounded px-2 py-1 transition-colors"
                onClick={async (e) => {
                  e.stopPropagation();
                  if (!confirm(`Delete case ${c.case_number}? All findings and audit entries will be permanently removed.`)) return;
                  try {
                    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/api/cases/${c.id}`, {
                      method: 'DELETE',
                    });
                    if (!res.ok) throw new Error(await res.text());
                    window.location.reload();
                  } catch (err) {
                    alert('Failed to delete case: ' + String(err));
                  }
                }}
              >
                Delete
              </button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
