"use client";

import { useState } from "react";
import Link from "next/link";
import { usePolicies, usePolicyChunks, usePolicyRules } from "@/hooks/usePolicies";
import { PolicyUpload } from "@/components/policies/PolicyUpload";
import { PolicyList } from "@/components/policies/PolicyList";
import { ChunkViewer } from "@/components/policies/ChunkViewer";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { TierBadge } from "@/components/ui/status-badges";
import { Badge } from "@/components/ui/badge";
import { WifiOff, ScrollText } from "lucide-react";
import type { PolicyDocument } from "@/types";

function statusVariant(status: string) {
  const s = (status || "").toUpperCase();
  if (s === "PENDING_REVIEW") return "warning" as const;
  if (s === "CONFIRMED") return "success" as const;
  if (s === "REJECTED") return "destructive" as const;
  return "secondary" as const;
}

function PolicyDetailDialog({
  policy,
  onOpenChange,
}: {
  policy: PolicyDocument;
  onOpenChange: (open: boolean) => void;
}) {
  const { data: chunks, isLoading: chunksLoading, isError: chunksError } = usePolicyChunks(policy.id);
  const { data: rules, isLoading: rulesLoading, isError: rulesError } = usePolicyRules(policy.id);

  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl" onClose={() => onOpenChange(false)}>
        <DialogHeader>
          <DialogTitle>{policy.title}</DialogTitle>
          <DialogDescription>
            {policy.version ? `Version ${policy.version} · ` : ""}
            {policy.total_chunks} chunks · {policy.rules_extracted} rules extracted
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="chunks">
          <TabsList>
            <TabsTrigger value="chunks">Chunks</TabsTrigger>
            <TabsTrigger value="rules" badge={rules?.length ? <Badge variant="secondary">{rules.length}</Badge> : undefined}>
              Rules extracted
            </TabsTrigger>
          </TabsList>

          <TabsContent value="chunks" className="mt-4 max-h-[55vh] overflow-y-auto">
            {chunksLoading ? (
              <div className="flex flex-col gap-3">
                <Skeleton className="h-20" />
                <Skeleton className="h-20" />
              </div>
            ) : chunksError ? (
              <EmptyState icon={WifiOff} title="Could not load chunks" />
            ) : (
              <ChunkViewer chunks={chunks ?? []} />
            )}
          </TabsContent>

          <TabsContent value="rules" className="mt-4 max-h-[55vh] overflow-y-auto">
            {rulesLoading ? (
              <div className="flex flex-col gap-3">
                <Skeleton className="h-16" />
                <Skeleton className="h-16" />
              </div>
            ) : rulesError ? (
              <EmptyState icon={WifiOff} title="Could not load rules" />
            ) : !rules || rules.length === 0 ? (
              <EmptyState
                icon={ScrollText}
                title="No rules extracted from this policy yet"
                description="Rule extraction runs separately from ingestion and may not have populated rules yet."
              />
            ) : (
              <div className="flex flex-col gap-2">
                {rules.map((rule) => (
                  <div
                    key={rule.id}
                    className="flex flex-col gap-1.5 rounded-lg border border-slate-200 p-3"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-medium text-slate-900">{rule.name}</p>
                      <Badge variant={statusVariant(rule.status)}>{rule.status.replace(/_/g, " ")}</Badge>
                    </div>
                    {rule.description && <p className="text-xs text-slate-500">{rule.description}</p>}
                    <TierBadge tier={rule.tier} />
                  </div>
                ))}
                <Link href="/rules" className="mt-1 text-xs font-medium text-slate-900 hover:underline">
                  View all rules on the Rules page →
                </Link>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}

export default function PoliciesPage() {
  const { data: policies, isLoading, isError, error } = usePolicies();
  const [selected, setSelected] = useState<PolicyDocument | null>(null);

  return (
    <div className="flex flex-col gap-6">
      <PolicyUpload />

      {isLoading ? (
        <div className="flex flex-col gap-3">
          <Skeleton className="h-10" />
          <Skeleton className="h-40" />
        </div>
      ) : isError ? (
        <EmptyState
          icon={WifiOff}
          title="Could not reach the DocGuard API"
          description={error instanceof Error ? error.message : "Check that the backend is running."}
        />
      ) : (
        <PolicyList policies={policies ?? []} selectedId={selected?.id} onSelect={setSelected} />
      )}

      {selected && <PolicyDetailDialog policy={selected} onOpenChange={(open) => !open && setSelected(null)} />}
    </div>
  );
}
