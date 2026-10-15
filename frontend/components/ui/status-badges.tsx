import { Badge } from "@/components/ui/badge";
import { tierLabel } from "@/lib/utils";
import { AlertTriangle, Brain, CheckCircle2, GitBranch, ListChecks, ShieldAlert } from "lucide-react";

export function RiskBadge({ level }: { level: string | null | undefined }) {
  const l = (level || "LOW").toUpperCase();
  if (l === "CRITICAL") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold bg-red-50 text-red-700 border border-red-200/80">
        <span className="h-1.5 w-1.5 rounded-full bg-red-600 animate-pulse" />
        Critical
      </span>
    );
  }
  if (l === "HIGH") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-200/80">
        <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
        High
      </span>
    );
  }
  if (l === "MEDIUM") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200/80">
        <span className="h-1.5 w-1.5 rounded-full bg-blue-500" />
        Medium
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/80">
      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
      Low
    </span>
  );
}

export function SeverityBadge({ severity }: { severity: string | null | undefined }) {
  const s = (severity || "LOW").toUpperCase();
  if (s === "CRITICAL") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold bg-red-50 text-red-700 border border-red-200/80">
        <span className="h-1.5 w-1.5 rounded-full bg-red-600" />
        Critical
      </span>
    );
  }
  if (s === "HIGH") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold bg-amber-50 text-amber-800 border border-amber-200/80">
        <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
        High
      </span>
    );
  }
  if (s === "MEDIUM") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200/80">
        <span className="h-1.5 w-1.5 rounded-full bg-blue-500" />
        Medium
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200/80">
      <span className="h-1.5 w-1.5 rounded-full bg-slate-400" />
      Low
    </span>
  );
}

export function TierBadge({ tier }: { tier: string | number | null | undefined }) {
  const label = tierLabel(tier);
  if (label === "LLM_EVALUATED") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium bg-purple-50 text-purple-700 border border-purple-200/80">
        <Brain className="h-3 w-3 text-purple-600" /> AI Assessed
      </span>
    );
  }
  if (label === "EXPRESSION") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200/80">
        <GitBranch className="h-3 w-3 text-blue-600" /> Expression
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200/80">
      <ListChecks className="h-3 w-3 text-slate-500" /> Deterministic
    </span>
  );
}

function formatStatusText(str: string): string {
  return str
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(" ");
}

export function CaseStatusBadge({ status }: { status: string | null | undefined }) {
  const s = (status || "OPEN").toUpperCase();
  const label = formatStatusText(s);

  if (s === "APPROVED" || s === "COMPLIANT") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200/80">
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
        {label}
      </span>
    );
  }
  if (s === "REJECTED" || s === "VIOLATION") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium bg-red-50 text-red-700 border border-red-200/80">
        <span className="h-1.5 w-1.5 rounded-full bg-red-600" />
        {label}
      </span>
    );
  }
  if (s === "ON_HOLD" || s === "NEEDS_REVIEW") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200/80">
        <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
        {label}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200/80">
      <span className="h-1.5 w-1.5 rounded-full bg-slate-400" />
      {label}
    </span>
  );
}

export function FindingStatusBadge({ status }: { status: string | null | undefined }) {
  const s = (status || "OPEN").toUpperCase();
  if (s === "VIOLATION") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold bg-red-50 text-red-700 border border-red-200/80">
        <AlertTriangle className="h-3 w-3 text-red-600" /> Violation
      </span>
    );
  }
  if (s === "NEEDS_REVIEW") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-200/80">
        <span className="h-1.5 w-1.5 rounded-full bg-amber-500" /> Needs Review
      </span>
    );
  }
  if (s === "PASS") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/80">
        <CheckCircle2 className="h-3 w-3 text-emerald-600" /> Pass
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200/80">
      {formatStatusText(s)}
    </span>
  );
}

export function ReviewStatusBadge({ status }: { status: string | null | undefined }) {
  const s = (status || "OPEN").toUpperCase();
  const label = formatStatusText(s);
  if (s === "ACCEPTED") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200/80">
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> {label}
      </span>
    );
  }
  if (s === "REJECTED") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium bg-red-50 text-red-700 border border-red-200/80">
        <span className="h-1.5 w-1.5 rounded-full bg-red-600" /> {label}
      </span>
    );
  }
  if (s === "NEEDS_REVIEW") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200/80">
        <span className="h-1.5 w-1.5 rounded-full bg-amber-500" /> {label}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium bg-white text-slate-600 border border-slate-200">
      {label}
    </span>
  );
}
