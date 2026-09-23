import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ComplianceRule } from "@/types";

export function useRules(status?: string) {
  return useQuery({
    queryKey: ["rules", status ?? "all"],
    queryFn: () => api.listRules(status),
  });
}

export function usePendingRules() {
  return useQuery({
    queryKey: ["rules", "pending"],
    queryFn: api.listPendingRules,
  });
}

function invalidateRules(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ["rules"] });
  qc.invalidateQueries({ queryKey: ["dashboard"] });
  qc.invalidateQueries({ queryKey: ["policies"] });
}

export function useUpdateRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<ComplianceRule> }) =>
      api.updateRule(id, data),
    onSuccess: () => invalidateRules(qc),
  });
}

export function useConfirmRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, confirmedBy }: { id: string; confirmedBy: string }) =>
      api.confirmRule(id, confirmedBy),
    onSuccess: () => invalidateRules(qc),
  });
}

export function useRejectRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => api.rejectRule(id, reason),
    onSuccess: () => invalidateRules(qc),
  });
}

export function useDisableRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.disableRule(id),
    onSuccess: () => invalidateRules(qc),
  });
}

export function useEnableRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.enableRule(id),
    onSuccess: () => invalidateRules(qc),
  });
}

export function useDeleteRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteRule(id),
    onSuccess: () => invalidateRules(qc),
  });
}

