export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

export const RISK_LEVELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"] as const;

export const SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"] as const;

export const CASE_STATUSES = [
  "OPEN",
  "PENDING",
  "UNDER_REVIEW",
  "COMPLIANT",
  "NEEDS_REVIEW",
  "VIOLATION",
  "APPROVED",
  "REJECTED",
  "ON_HOLD",
] as const;

export const DOCUMENT_TYPES = ["PURCHASE_ORDER", "INVOICE", "GOODS_RECEIPT", "POLICY"] as const;

export const RULE_STATUSES = ["PENDING_REVIEW", "CONFIRMED", "REJECTED", "DISABLED"] as const;

export const TIER_LABELS: Record<string, string> = {
  "1": "PRIMITIVE",
  "2": "EXPRESSION",
  "3": "LLM_EVALUATED",
  PRIMITIVE: "PRIMITIVE",
  EXPRESSION: "EXPRESSION",
  LLM_EVALUATED: "LLM_EVALUATED",
};
