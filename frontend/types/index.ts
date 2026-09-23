// Types mirror the ACTUAL JSON shapes returned by the FastAPI routers
// (backend/app/routers/*.py return hand-built dicts, not the Pydantic
// schemas in backend/app/schemas/ — those are currently unused by the API).

export type DocumentType = "PURCHASE_ORDER" | "INVOICE" | "GOODS_RECEIPT" | "POLICY";

export type DocumentStatus = "UPLOADED" | "CLASSIFIED" | "EXTRACTED" | "FAILED";

export interface ExtractedField {
  id: string;
  field_name: string;
  field_value: string;
  field_type: string;
  confidence: number;
  source_page: number | null;
}

export interface DocumentItem {
  id: string;
  filename: string;
  original_filename: string;
  document_type: DocumentType | string | null;
  classification_confidence: number | null;
  page_count: number | null;
  uploaded_at: string;
  extracted_data: ExtractedField[];
}

export interface UploadDocumentResult {
  id: string;
  filename: string;
  original_filename: string;
  document_type: string | null;
  classification_confidence: number | null;
  page_count: number | null;
  uploaded_at: string;
  case_id: string | null;
  case_number: string | null;
  extracted_fields_count: number;
}

export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type CaseStatus =
  | "OPEN"
  | "PENDING"
  | "UNDER_REVIEW"
  | "COMPLIANT"
  | "NEEDS_REVIEW"
  | "VIOLATION"
  | "APPROVED"
  | "REJECTED"
  | "ON_HOLD"
  | string;

export interface CaseSummary {
  id: string;
  case_number: string;
  vendor_name: string | null;
  po_number: string | null;
  invoice_number: string | null;
  total_amount: number | null;
  currency: string | null;
  status: CaseStatus;
  risk_level: RiskLevel | string;
  risk_score: number | null;
  findings_count: number;
  violation_count: number;
  created_at: string;
}

export interface CaseDetail extends CaseSummary {
  department: string | null;
  project_code: string | null;
  explanation: string | null;
  updated_at: string;
  po_document: DocumentItem | null;
  invoice_document: DocumentItem | null;
  grn_document: DocumentItem | null;
  findings: Finding[];
  audit_entries: AuditEntry[];
}

export type FindingTier = "PRIMITIVE" | "EXPRESSION" | "LLM_EVALUATED" | string;
export type FindingStatus = "VIOLATION" | "NEEDS_REVIEW" | "OPEN" | "PASS" | string;
export type FindingReviewStatus = "OPEN" | "ACCEPTED" | "REJECTED" | "NEEDS_REVIEW" | string;
export type Severity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" | string;

export interface Finding {
  id: string;
  case_id: string;
  rule_id: string | null;
  finding_type: string;
  severity: Severity;
  tier: FindingTier | null;
  rule_name: string | null;
  status: FindingStatus;
  finding_review_status: FindingReviewStatus;
  expected_value: string | null;
  actual_value: string | null;
  difference: string | null;
  explanation: string | null;
  policy_clause_text: string | null;
  policy_document_name: string | null;
  policy_section: string | null;
  policy_page: number | null;
  policy_similarity_score: number | null;
  llm_confidence: number | null;
  reviewer: string | null;
  reviewer_comment: string | null;
  reviewed_at: string | null;
  created_at: string;
}

export interface AuditEntry {
  id: string;
  action: string;
  actor: string;
  detail: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export type RuleTier = "1" | "2" | "3" | string; // 1=PRIMITIVE 2=EXPRESSION 3=LLM_EVALUATED
export type RuleStatus = "PENDING_REVIEW" | "CONFIRMED" | "REJECTED" | "DISABLED" | string;

export interface ComplianceRule {
  id: string;
  name: string;
  description: string | null;
  tier: RuleTier;
  primitive: string | null;
  parameters: Record<string, unknown> | null;
  expression: Record<string, unknown> | null;
  evaluation_prompt: string | null;
  severity: Severity;
  on_violation: string;
  source_policy_id: string | null;
  source_clause: string | null;
  source_section: string | null;
  source_page: number | null;
  status: RuleStatus;
  confirmed_by?: string | null;
  confirmed_at?: string | null;
  enabled: boolean;
  created_at: string;
}

export interface PolicyDocument {
  id: string;
  document_id: string | null;
  title: string;
  version: string | null;
  effective_date: string | null;
  total_chunks: number;
  rules_extracted: number;
  ingestion_status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED" | string;
  error_message?: string | null;
  is_active?: boolean;
  uploaded_at: string;
}

export interface PolicyChunk {
  id: string;
  policy_id: string;
  chunk_index: number;
  content: string;
  section_number: string | null;
  section_title: string | null;
  page_number: number | null;
}

export interface DashboardStats {
  total_cases: number;
  compliant_cases: number;
  violation_cases: number;
  needs_review_cases: number;
  high_risk_cases: number;
  pending_rules: number;
  recent_cases: CaseSummary[];
  queue: CaseSummary[];
}
