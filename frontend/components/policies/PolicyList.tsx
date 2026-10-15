"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useToast } from "@/components/ui/toast";
import { useDeletePolicy } from "@/hooks/usePolicies";
import { cn, formatDateTime } from "@/lib/utils";
import type { PolicyDocument } from "@/types";
import { ScrollText, Trash2 } from "lucide-react";

function IngestionBadge({ status, error }: { status: string; error?: string | null }) {
  const s = (status || "PENDING").toUpperCase();
  if (s === "COMPLETED") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/80">
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
        Completed
      </span>
    );
  }
  if (s === "PROCESSING") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200/80">
        <Spinner className="h-3 w-3 text-blue-600" />
        Processing
      </span>
    );
  }
  if (s === "FAILED") {
    return (
      <span
        className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold bg-red-50 text-red-700 border border-red-200/80"
        title={error || "Ingestion failed"}
      >
        <span className="h-1.5 w-1.5 rounded-full bg-red-600" />
        Failed
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
      <span className="h-1.5 w-1.5 rounded-full bg-slate-400" />
      Pending
    </span>
  );
}

export function PolicyList({
  policies,
  selectedId,
  onSelect,
}: {
  policies: PolicyDocument[];
  selectedId?: string | null;
  onSelect: (policy: PolicyDocument) => void;
}) {
  const { toast } = useToast();
  const deletePolicy = useDeletePolicy();
  const [policyToDelete, setPolicyToDelete] = useState<PolicyDocument | null>(null);

  function handleDelete() {
    if (!policyToDelete) return;
    deletePolicy.mutate(policyToDelete.id, {
      onSuccess: () => {
        toast({
          title: "Policy deleted",
          description: `Policy "${policyToDelete.title}" and its rules were deleted.`,
          variant: "success",
        });
        setPolicyToDelete(null);
      },
      onError: (err) => {
        toast({
          title: "Deletion failed",
          description: err instanceof Error ? err.message : "Could not delete policy.",
          variant: "error",
        });
      },
    });
  }

  return (
    <>
      <Card className="overflow-hidden border border-slate-200/90 shadow-sm bg-white">
        <CardHeader className="border-b border-slate-100 py-4 px-6">
          <CardTitle className="text-base font-semibold text-slate-900">Policy documents</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {policies.length === 0 ? (
            <EmptyState
              icon={ScrollText}
              title="No policies uploaded yet"
              description="Upload a policy PDF above to ingest it for RAG search and rule extraction."
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Title</TableHead>
                  <TableHead>Version</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Chunks</TableHead>
                  <TableHead>Rules extracted</TableHead>
                  <TableHead>Uploaded</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {policies.map((policy) => (
                  <TableRow
                    key={policy.id}
                    onClick={() => onSelect(policy)}
                    className={cn(
                      "cursor-pointer",
                      selectedId === policy.id && "bg-slate-50"
                    )}
                  >
                    <TableCell className="font-medium text-slate-900">
                      <div className="flex items-center gap-2">
                        <span>{policy.title}</span>
                        {policy.is_active === false && (
                          <Badge variant="secondary" className="text-xs">
                            SUPERSEDED
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-slate-600">{policy.version || "—"}</TableCell>
                    <TableCell>
                      <IngestionBadge status={policy.ingestion_status} error={policy.error_message} />
                    </TableCell>
                    <TableCell className="text-slate-600">{policy.total_chunks}</TableCell>
                    <TableCell className="text-slate-600">{policy.rules_extracted}</TableCell>
                    <TableCell className="text-slate-500">{formatDateTime(policy.uploaded_at)}</TableCell>
                    <TableCell className="text-right" onClick={(e) => e.stopPropagation()}>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-slate-400 hover:text-red-600"
                        title="Delete policy"
                        onClick={(e) => {
                          e.stopPropagation();
                          setPolicyToDelete(policy);
                        }}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!policyToDelete} onOpenChange={(open) => !open && setPolicyToDelete(null)}>
        <DialogContent onClose={() => setPolicyToDelete(null)}>
          <DialogHeader>
            <DialogTitle>Delete policy document</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete <strong>{policyToDelete?.title}</strong> (Version {policyToDelete?.version || "1.0"})?
              This will permanently remove the policy, its text chunks, and all associated extracted rules.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPolicyToDelete(null)} disabled={deletePolicy.isPending}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deletePolicy.isPending}
            >
              {deletePolicy.isPending ? "Deleting…" : "Delete policy"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

