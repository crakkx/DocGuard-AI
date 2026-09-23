import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useCases(params?: { status?: string; risk_level?: string; search?: string }) {
  return useQuery({
    queryKey: ["cases", params ?? {}],
    queryFn: () => api.listCases(params),
  });
}

export function useCase(id: string | undefined) {
  return useQuery({
    queryKey: ["cases", id],
    queryFn: () => api.getCase(id as string),
    enabled: !!id,
  });
}

export function useRunCompliance(caseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.runCompliance(caseId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cases", caseId] });
      qc.invalidateQueries({ queryKey: ["cases"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useLinkDocument(caseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (documentId: string) => api.linkDocument(caseId, documentId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cases", caseId] });
      qc.invalidateQueries({ queryKey: ["cases"] });
    },
  });
}

export function useUnlinkDocument(caseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (documentId: string) => api.unlinkDocument(caseId, documentId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cases", caseId] });
      qc.invalidateQueries({ queryKey: ["cases"] });
    },
  });
}

export function useReviewFinding(caseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      findingId,
      status,
      reviewer,
      comment,
    }: {
      findingId: string;
      status: string;
      reviewer: string;
      comment?: string;
    }) => api.reviewFinding(findingId, { status, reviewer, reviewer_comment: comment }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cases", caseId] });
    },
  });
}

export function useCaseDecision(caseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      decision,
      reviewer,
      comment,
    }: {
      decision: "APPROVE" | "REJECT" | "HOLD";
      reviewer: string;
      comment?: string;
    }) => api.makeCaseDecision(caseId, { decision, reviewer, comment }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cases", caseId] });
      qc.invalidateQueries({ queryKey: ["cases"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}
