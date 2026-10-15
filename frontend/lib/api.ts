import { API_BASE_URL } from "./constants";
import type {
  CaseDetail,
  CaseSummary,
  ComplianceRule,
  DashboardStats,
  DocumentItem,
  PolicyChunk,
  PolicyDocument,
  UploadDocumentResult,
} from "@/types";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers:
      init?.body && !(init.body instanceof FormData)
        ? { "Content-Type": "application/json", ...init?.headers }
        : init?.headers,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ? JSON.stringify(body.detail) : detail;
    } catch {
      // ignore parse errors
    }
    throw new ApiError(res.status, detail || `Request to ${path} failed`);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

function toJsonBody(data: unknown): RequestInit {
  return { method: "PATCH", body: JSON.stringify(data) };
}

export const api = {
  // Documents
  uploadDocument: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<UploadDocumentResult>("/api/documents/upload", { method: "POST", body: form });
  },
  listDocuments: (params?: { document_type?: string }) => {
    const qs = new URLSearchParams();
    if (params?.document_type) qs.set("document_type", params.document_type);
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return request<DocumentItem[]>(`/api/documents/${suffix}`);
  },
  getDocument: (id: string) => request<DocumentItem>(`/api/documents/${id}`),
  deleteDocument: (id: string) =>
    request<{ deleted: boolean; id: string }>(`/api/documents/${id}`, { method: "DELETE" }),
  classifyDocument: (id: string, document_type: string) =>
    request<{ id: string; document_type: string; user_corrected: boolean }>(
      `/api/documents/${id}/classify`,
      { ...toJsonBody({ document_type }) }
    ),

  // Cases
  listCases: (params?: { status?: string; risk_level?: string; search?: string }) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.risk_level) qs.set("risk_level", params.risk_level);
    if (params?.search) qs.set("search", params.search);
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return request<CaseSummary[]>(`/api/cases/${suffix}`);
  },
  getCase: (id: string) => request<CaseDetail>(`/api/cases/${id}`),
  linkDocument: (caseId: string, documentId: string) =>
    request(`/api/cases/${caseId}/link`, {
      method: "POST",
      body: JSON.stringify({ document_id: documentId }),
    }),
  unlinkDocument: (caseId: string, documentId: string) =>
    request(`/api/cases/${caseId}/documents/${documentId}`, { method: "DELETE" }),
  runCompliance: (caseId: string) =>
    request(`/api/cases/${caseId}/run-compliance`, { method: "POST" }),
  getCaseAudit: (caseId: string) => request(`/api/cases/${caseId}/audit`),
  deleteCase: (caseId: string) =>
    request<{ deleted: boolean; id: string }>(`/api/cases/${caseId}`, { method: "DELETE" }),

  // Review
  reviewFinding: (
    findingId: string,
    data: { status: string; reviewer: string; reviewer_comment?: string }
  ) =>
    request(`/api/review/findings/${findingId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  makeCaseDecision: (
    caseId: string,
    data: { decision: "APPROVE" | "REJECT" | "HOLD"; reviewer: string; comment?: string }
  ) =>
    request(`/api/review/cases/${caseId}/decision`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Rules
  listRules: (status?: string) => {
    const qs = status ? `?status=${encodeURIComponent(status)}` : "";
    return request<ComplianceRule[]>(`/api/rules/${qs}`);
  },
  listPendingRules: () => request<ComplianceRule[]>("/api/rules/pending"),
  getRule: (id: string) => request<ComplianceRule>(`/api/rules/${id}`),
  updateRule: (id: string, data: Partial<ComplianceRule>) =>
    request<ComplianceRule>(`/api/rules/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  confirmRule: (id: string, confirmed_by: string) =>
    request<ComplianceRule>(`/api/rules/${id}/confirm`, {
      method: "POST",
      body: JSON.stringify({ confirmed_by }),
    }),
  rejectRule: (id: string, reason: string) =>
    request<ComplianceRule>(`/api/rules/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  disableRule: (id: string) =>
    request<ComplianceRule>(`/api/rules/${id}/disable`, { method: "POST" }),
  enableRule: (id: string) =>
    request<ComplianceRule>(`/api/rules/${id}/enable`, { method: "POST" }),
  deleteRule: (id: string) =>
    request<{ status: string; message: string }>(`/api/rules/${id}`, { method: "DELETE" }),

  // Policies
  uploadPolicy: (file: File, title: string, version?: string, existingPolicyId?: string) => {
    const form = new FormData();
    form.append("file", file);
    form.append("title", title);
    if (version) form.append("version", version);
    if (existingPolicyId) form.append("existing_policy_id", existingPolicyId);
    return request<PolicyDocument>("/api/policies/upload", { method: "POST", body: form });
  },
  listPolicies: () => request<PolicyDocument[]>("/api/policies/"),
  getPolicy: (id: string) => request<PolicyDocument>(`/api/policies/${id}`),
  getPolicyChunks: (id: string) => request<PolicyChunk[]>(`/api/policies/${id}/chunks`),
  getPolicyRules: (id: string) => request<ComplianceRule[]>(`/api/policies/${id}/rules`),
  deletePolicy: (id: string) =>
    request<{ status: string; message: string }>(`/api/policies/${id}`, { method: "DELETE" }),

  // Dashboard
  getDashboardStats: () => request<DashboardStats>("/api/dashboard/stats"),
  getDashboardQueue: () => request<CaseSummary[]>("/api/dashboard/queue"),

  // Health
  health: () => request<{ status: string; service: string }>("/api/health"),
};
