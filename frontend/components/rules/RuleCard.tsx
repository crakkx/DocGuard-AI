import type { ReactNode } from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TierBadge, SeverityBadge } from "@/components/ui/status-badges";
import { tierLabel } from "@/lib/utils";
import type { ComplianceRule } from "@/types";

function statusVariant(status: string) {
  const s = (status || "").toUpperCase();
  if (s === "PENDING_REVIEW") return "warning" as const;
  if (s === "CONFIRMED") return "success" as const;
  if (s === "REJECTED") return "destructive" as const;
  if (s === "DISABLED") return "secondary" as const;
  return "outline" as const;
}

function SourceReference({ rule }: { rule: ComplianceRule }) {
  if (!rule.source_clause && !rule.source_section && rule.source_page == null) return null;

  const refParts: string[] = [];
  if (rule.source_section) refParts.push(`§${rule.source_section}`);
  if (rule.source_page != null) refParts.push(`p.${rule.source_page}`);

  return (
    <div className="rounded-md border border-slate-100 bg-slate-50 px-3 py-2">
      {rule.source_clause && (
        <p className="text-xs italic text-slate-600">&ldquo;{rule.source_clause}&rdquo;</p>
      )}
      {refParts.length > 0 && (
        <p className="mt-1 text-xs font-medium text-slate-400">{refParts.join(", ")}</p>
      )}
    </div>
  );
}

function RuleLogic({ rule }: { rule: ComplianceRule }) {
  const tier = tierLabel(rule.tier);

  if (tier === "PRIMITIVE") {
    return (
      <div className="flex flex-col gap-1">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {rule.primitive || "Primitive check"}
        </p>
        {rule.parameters && (
          <pre className="overflow-x-auto rounded-md bg-slate-900 p-3 text-xs text-slate-100">
            {JSON.stringify(rule.parameters, null, 2)}
          </pre>
        )}
      </div>
    );
  }

  if (tier === "EXPRESSION") {
    return (
      <div className="flex flex-col gap-1">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Expression</p>
        {rule.expression && (
          <pre className="overflow-x-auto rounded-md bg-slate-900 p-3 text-xs text-slate-100">
            {JSON.stringify(rule.expression, null, 2)}
          </pre>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Evaluation prompt</p>
      {rule.evaluation_prompt && (
        <p className="whitespace-pre-wrap rounded-md bg-slate-50 p-3 text-xs text-slate-700">
          {rule.evaluation_prompt}
        </p>
      )}
    </div>
  );
}

export function RuleCard({ rule, actions }: { rule: ComplianceRule; actions?: ReactNode }) {
  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between gap-3">
        <div className="flex flex-col gap-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-semibold text-slate-900">{rule.name}</p>
            <TierBadge tier={rule.tier} />
            <SeverityBadge severity={rule.severity} />
            <Badge variant={statusVariant(rule.status)}>{rule.status.replace(/_/g, " ")}</Badge>
          </div>
          {rule.description && <p className="text-xs text-slate-500">{rule.description}</p>}
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <SourceReference rule={rule} />
        <RuleLogic rule={rule} />
        {actions && <div className="flex flex-wrap items-center gap-2 pt-1">{actions}</div>}
      </CardContent>
    </Card>
  );
}
