"use client";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { RiskBadge, CaseStatusBadge } from "@/components/ui/status-badges";
import { formatCurrency } from "@/lib/utils";
import { useRunCompliance } from "@/hooks/useCases";
import { useToast } from "@/components/ui/toast";
import { PlayCircle } from "lucide-react";
import type { CaseDetail } from "@/types";

interface RunComplianceResult {
  findings_count?: number;
  violations?: number;
}

export function CaseHeader({ caseDetail }: { caseDetail: CaseDetail }) {
  const { mutate: runCompliance, isPending } = useRunCompliance(caseDetail.id);
  const { toast } = useToast();

  function handleRunCompliance() {
    runCompliance(undefined, {
      onSuccess: (data) => {
        const result = data as RunComplianceResult | undefined;
        toast({
          title: "Compliance check complete",
          description:
            result?.findings_count !== undefined
              ? `${result.findings_count} finding(s), ${result.violations ?? 0} violation(s)`
              : undefined,
          variant: "success",
        });
      },
      onError: (err) => {
        toast({
          title: "Compliance check failed",
          description: err instanceof Error ? err.message : undefined,
          variant: "error",
        });
      },
    });
  }

  return (
    <Card className="border border-slate-200/90 shadow-sm bg-white overflow-hidden">
      <div className="p-6 sm:p-7 flex flex-col gap-4 sm:gap-5">
        {/* Top Header Row with generous top breathing space */}
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <div>
            <div className="flex items-center gap-2.5">
              <h2 className="text-xl font-bold tracking-tight text-slate-900">{caseDetail.case_number}</h2>
              <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200/60">
                Procurement Case
              </span>
            </div>
            <p className="text-sm font-medium text-slate-600 mt-1 flex items-center gap-1.5">
              <span className="text-slate-400">Vendor:</span>
              <span className="text-slate-900 font-semibold">{caseDetail.vendor_name || "Unknown vendor"}</span>
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <CaseStatusBadge status={caseDetail.status} />
            <RiskBadge level={caseDetail.risk_level} />
            {caseDetail.risk_score !== null && (
              <span className="text-xs font-medium text-slate-500 bg-slate-50 border border-slate-200 rounded-md px-2 py-0.5">
                Score {caseDetail.risk_score}
              </span>
            )}
          </div>
        </div>

        {/* Compact, Sleek Metrics Info Grid */}
        <div className="grid grid-cols-2 gap-3 sm:gap-4 sm:grid-cols-4 rounded-lg bg-slate-50/80 px-4 py-3 sm:px-5 sm:py-3.5 border border-slate-200/70">
          <div className="flex flex-col gap-0.5">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">PO Number</p>
            <p className="text-sm font-semibold font-mono text-slate-800">{caseDetail.po_number || "—"}</p>
          </div>
          <div className="flex flex-col gap-0.5">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Invoice Number</p>
            <p className="text-sm font-semibold font-mono text-slate-800">{caseDetail.invoice_number || "—"}</p>
          </div>
          <div className="flex flex-col gap-0.5">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Total Amount</p>
            <p className="text-sm font-bold text-slate-900 tabular-nums">
              {formatCurrency(caseDetail.total_amount, caseDetail.currency ?? undefined)}
            </p>
          </div>
          <div className="flex flex-col gap-0.5">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Department</p>
            <p className="text-sm font-medium text-slate-700">{caseDetail.department || "—"}</p>
          </div>
        </div>

        {/* Action Button Row */}
        <div className="flex items-center justify-between pt-0.5">
          <Button
            size="sm"
            onClick={handleRunCompliance}
            disabled={isPending}
            className="h-9 px-4 gap-2 text-xs font-semibold shadow-xs"
          >
            {isPending ? <Spinner /> : <PlayCircle className="h-3.5 w-3.5" />}
            Run Compliance Check
          </Button>
          <p className="text-xs text-slate-400 hidden sm:block">
            All documents and compliance rules will be evaluated.
          </p>
        </div>
      </div>
    </Card>
  );
}
