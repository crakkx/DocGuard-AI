import { Badge } from "@/components/ui/badge";
import { tierLabel } from "@/lib/utils";
import { AlertTriangle, Brain, GitBranch, ListChecks } from "lucide-react";

export function RiskBadge({ level }: { level: string | null | undefined }) {
  const l = (level || "LOW").toUpperCase();
  const variant =
    l === "CRITICAL" ? "destructive" : l === "HIGH" ? "warning" : l === "MEDIUM" ? "info" : "success";
  return <Badge variant={variant}>{l}</Badge>;
}

export function SeverityBadge({ severity }: { severity: string | null | undefined }) {
  const s = (severity || "LOW").toUpperCase();
  const variant =
    s === "CRITICAL" ? "destructive" : s === "HIGH" ? "warning" : s === "MEDIUM" ? "info" : "secondary";
  return <Badge variant={variant}>{s}</Badge>;
}

export function TierBadge({ tier }: { tier: string | number | null | undefined }) {
  const label = tierLabel(tier);
  if (label === "LLM_EVALUATED") {
    return (
      <Badge variant="purple">
        <Brain className="h-3 w-3" /> AI_ASSESSED
      </Badge>
    );
  }
  if (label === "EXPRESSION") {
    return (
      <Badge variant="info">
        <GitBranch className="h-3 w-3" /> EXPRESSION
      </Badge>
    );
  }
  return (
    <Badge variant="secondary">
      <ListChecks className="h-3 w-3" /> PRIMITIVE
    </Badge>
  );
}

export function CaseStatusBadge({ status }: { status: string | null | undefined }) {
  const s = (status || "OPEN").toUpperCase();
  const variant =
    s === "APPROVED" || s === "COMPLIANT"
      ? "success"
      : s === "REJECTED" || s === "VIOLATION"
        ? "destructive"
        : s === "ON_HOLD" || s === "NEEDS_REVIEW"
          ? "warning"
          : "secondary";
  return <Badge variant={variant}>{s.replace(/_/g, " ")}</Badge>;
}

export function FindingStatusBadge({ status }: { status: string | null | undefined }) {
  const s = (status || "OPEN").toUpperCase();
  if (s === "VIOLATION")
    return (
      <Badge variant="destructive">
        <AlertTriangle className="h-3 w-3" /> VIOLATION
      </Badge>
    );
  if (s === "NEEDS_REVIEW") return <Badge variant="warning">NEEDS REVIEW</Badge>;
  if (s === "PASS") return <Badge variant="success">PASS</Badge>;
  return <Badge variant="secondary">{s}</Badge>;
}

export function ReviewStatusBadge({ status }: { status: string | null | undefined }) {
  const s = (status || "OPEN").toUpperCase();
  const variant =
    s === "ACCEPTED" ? "success" : s === "REJECTED" ? "destructive" : s === "NEEDS_REVIEW" ? "warning" : "outline";
  return <Badge variant={variant}>{s.replace(/_/g, " ")}</Badge>;
}
