import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function usePolicies() {
  return useQuery({
    queryKey: ["policies"],
    queryFn: api.listPolicies,
    refetchInterval: (query) => {
      const data = query.state.data;
      const isProcessing = data?.some(
        (p) => p.ingestion_status === "PROCESSING" || p.ingestion_status === "PENDING"
      );
      return isProcessing ? 2000 : false;
    },
  });
}

export function usePolicy(id: string | undefined) {
  return useQuery({
    queryKey: ["policies", id],
    queryFn: () => api.getPolicy(id as string),
    enabled: !!id,
    refetchInterval: (query) => {
      const p = query.state.data;
      return p?.ingestion_status === "PROCESSING" || p?.ingestion_status === "PENDING" ? 2000 : false;
    },
  });
}

export function usePolicyChunks(id: string | undefined) {
  return useQuery({
    queryKey: ["policies", id, "chunks"],
    queryFn: () => api.getPolicyChunks(id as string),
    enabled: !!id,
  });
}

export function usePolicyRules(id: string | undefined) {
  return useQuery({
    queryKey: ["policies", id, "rules"],
    queryFn: () => api.getPolicyRules(id as string),
    enabled: !!id,
  });
}

export function useUploadPolicy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      file,
      title,
      version,
      existingPolicyId,
    }: {
      file: File;
      title: string;
      version?: string;
      existingPolicyId?: string;
    }) => api.uploadPolicy(file, title, version, existingPolicyId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["policies"] });
      qc.invalidateQueries({ queryKey: ["rules"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useDeletePolicy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deletePolicy(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["policies"] });
      qc.invalidateQueries({ queryKey: ["rules"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

