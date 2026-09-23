"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Spinner } from "@/components/ui/spinner";
import { Separator } from "@/components/ui/separator";
import { EmptyState } from "@/components/ui/empty-state";
import {
  FindingStatusBadge,
  SeverityBadge,
  TierBadge,
  ReviewStatusBadge,
} from "@/components/ui/status-badges";
import { PolicyEvidence } from "@/components/cases/PolicyEvidence";
import { formatDateTime, formatPercent, isAiAssessed } from "@/lib/utils";
import { useReviewFinding } from "@/hooks/useCases";
import { useToast } from "@/components/ui/toast";
import { CheckCircle2, XCircle, HelpCircle, ShieldCheck } from "lucide-react";
import type { Finding } from "@/types";

export function ComplianceFindings({
  caseId,
  findings,
}: {
  caseId: string;
  findings: Finding[];
}) {
  if (findings.length === 0) {
    return (
      <EmptyState
        icon={ShieldCheck}
        title="No findings yet"
        description="Run the compliance check to generate findings for this case."
      />
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {findings.map((finding) => (
        <FindingCard key={finding.id} caseId={caseId} finding={finding} />
      ))}
    </div>
  );
}

function FindingCard({ caseId, finding }: { caseId: string; finding: Finding }) {
  const [reviewer, setReviewer] = useState("");
  const [comment, setComment] = useState("");
  const { mutate, isPending } = useReviewFinding(caseId);
  const { toast } = useToast();

  const alreadyReviewed = finding.finding_review_status !== "OPEN";

  function review(status: "ACCEPTED" | "REJECTED" | "NEEDS_REVIEW") {
    if (!reviewer.trim()) {
      toast({ title: "Reviewer name required", variant: "error" });
      return;
    }
    mutate(
      { findingId: finding.id, status, reviewer: reviewer.trim(), comment: comment.trim() || undefined },
      {
        onSuccess: () => {
          toast({ title: "Finding reviewed", variant: "success" });
          setComment("");
        },
        onError: (err) =>
          toast({
            title: "Review failed",
            description: err instanceof Error ? err.message : undefined,
            variant: "error",
          }),
      }
    );
  }

  return (
    <Card>
      <CardContent className="flex flex-col gap-3 pt-5">
        <div className="flex flex-wrap items-center gap-2">
          <FindingStatusBadge status={finding.status} />
          <SeverityBadge severity={finding.severity} />
          <TierBadge tier={finding.tier} />
          <span className="text-sm font-semibold text-slate-900">
            {finding.rule_name || finding.finding_type}
          </span>
        </div>

        <div className="grid grid-cols-1 gap-3 text-xs sm:grid-cols-3">
          <div>
            <p className="uppercase tracking-wide text-slate-400">Expected</p>
            <p className="text-slate-700">{finding.expected_value ?? "—"}</p>
          </div>
          <div>
            <p className="uppercase tracking-wide text-slate-400">Actual</p>
            <p className="text-slate-700">{finding.actual_value ?? "—"}</p>
          </div>
          <div>
            <p className="uppercase tracking-wide text-slate-400">Difference</p>
            <p className="text-slate-700">{finding.difference ?? "—"}</p>
          </div>
        </div>

        {finding.explanation && <p className="text-sm text-slate-600">{finding.explanation}</p>}

        {isAiAssessed(finding.tier) && finding.llm_confidence !== null && (
          <p className="text-xs font-medium text-violet-700">
            AI confidence: {formatPercent(finding.llm_confidence)}
          </p>
        )}

        <PolicyEvidence finding={finding} />

        <Separator />

        {alreadyReviewed ? (
          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
            <ReviewStatusBadge status={finding.finding_review_status} />
            <span>
              {finding.reviewer && `by ${finding.reviewer}`}
              {finding.reviewed_at && ` · ${formatDateTime(finding.reviewed_at)}`}
            </span>
            {finding.reviewer_comment && (
              <span className="italic text-slate-400">“{finding.reviewer_comment}”</span>
            )}
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              <Input
                placeholder="Reviewer name"
                value={reviewer}
                onChange={(e) => setReviewer(e.target.value)}
                disabled={isPending}
              />
              <Textarea
                placeholder="Comment (optional)"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                disabled={isPending}
                className="min-h-9 sm:min-h-0"
              />
            </div>
            <div className="flex flex-wrap gap-2">
              <Button size="sm" disabled={isPending} onClick={() => review("ACCEPTED")}>
                {isPending ? <Spinner /> : <CheckCircle2 className="h-4 w-4" />}
                Accept
              </Button>
              <Button
                size="sm"
                variant="destructive"
                disabled={isPending}
                onClick={() => review("REJECTED")}
              >
                {isPending ? <Spinner /> : <XCircle className="h-4 w-4" />}
                Reject
              </Button>
              <Button
                size="sm"
                variant="outline"
                disabled={isPending}
                onClick={() => review("NEEDS_REVIEW")}
              >
                {isPending ? <Spinner /> : <HelpCircle className="h-4 w-4" />}
                Needs Review
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
