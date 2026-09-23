"use client";

import { Card, CardContent } from "@/components/ui/card";
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
    <Card>
      <CardContent className="flex flex-col gap-4 pt-5">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">{caseDetail.case_number}</h2>
            <p className="text-sm text-slate-500">{caseDetail.vendor_name || "Unknown vendor"}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <CaseStatusBadge status={caseDetail.status} />
            <RiskBadge level={caseDetail.risk_level} />
            {caseDetail.risk_score !== null && (
              <span className="text-xs text-slate-500">
                risk score {caseDetail.risk_score}
              </span>
            )}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-400">PO Number</p>
            <p className="text-slate-700">{caseDetail.po_number || "—"}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-400">Invoice Number</p>
            <p className="text-slate-700">{caseDetail.invoice_number || "—"}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-400">Amount</p>
            <p className="text-slate-700">
              {formatCurrency(caseDetail.total_amount, caseDetail.currency ?? undefined)}
            </p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-400">Department</p>
            <p className="text-slate-700">{caseDetail.department || "—"}</p>
          </div>
        </div>

        <div>
          <Button size="sm" onClick={handleRunCompliance} disabled={isPending}>
            {isPending ? <Spinner /> : <PlayCircle className="h-4 w-4" />}
            Run Compliance Check
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
