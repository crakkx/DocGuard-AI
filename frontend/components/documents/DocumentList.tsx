"use client";

import { useState } from "react";
import { FileText, Inbox, WifiOff } from "lucide-react";
import { useDocuments, useDeleteDocument } from "@/hooks/useDocuments";
import { DOCUMENT_TYPES } from "@/lib/constants";
import { formatDate, formatPercent } from "@/lib/utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Select } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { DocumentViewer } from "@/components/documents/DocumentViewer";
import type { DocumentItem } from "@/types";

const TYPE_BADGE_VARIANT: Record<string, BadgeProps["variant"]> = {
  PURCHASE_ORDER: "info",
  INVOICE: "purple",
  GOODS_RECEIPT: "success",
  POLICY: "warning",
};

export function DocumentTypeBadge({ type }: { type: string | null | undefined }) {
  if (!type) return <Badge variant="secondary">UNCLASSIFIED</Badge>;
  return <Badge variant={TYPE_BADGE_VARIANT[type] ?? "secondary"}>{type.replace(/_/g, " ")}</Badge>;
}

export function DocumentList() {
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [selectedDoc, setSelectedDoc] = useState<DocumentItem | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const { data: documents, isLoading, isError, error } = useDocuments(typeFilter || undefined);
  const { mutateAsync: deleteDocument } = useDeleteDocument();

  return (
    <>
      <Card>
        <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle>Documents</CardTitle>
            <CardDescription>
              All uploaded purchase orders, invoices, goods receipts and policies.
            </CardDescription>
          </div>
          <Select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="w-full sm:w-56"
            aria-label="Filter by document type"
          >
            <option value="">All types</option>
            {DOCUMENT_TYPES.map((t) => (
              <option key={t} value={t}>
                {t.replace(/_/g, " ")}
              </option>
            ))}
          </Select>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex flex-col gap-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : isError ? (
            <EmptyState
              icon={WifiOff}
              title="Could not load documents"
              description={
                error instanceof Error
                  ? error.message
                  : "Check that the backend is running and NEXT_PUBLIC_API_URL is set correctly."
              }
            />
          ) : !documents || documents.length === 0 ? (
            <EmptyState
              icon={Inbox}
              title="No documents yet"
              description="Upload a PO, invoice, goods receipt or policy above to get started."
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Filename</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Confidence</TableHead>
                  <TableHead>Pages</TableHead>
                  <TableHead>Uploaded</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {documents.map((doc) => (
                  <TableRow key={doc.id}>
                    <TableCell className="max-w-[220px] font-medium text-slate-900">
                      <span className="flex items-center gap-2">
                        <FileText className="h-3.5 w-3.5 shrink-0 text-slate-400" />
                        <span className="truncate">{doc.original_filename}</span>
                      </span>
                    </TableCell>
                    <TableCell>
                      <DocumentTypeBadge type={doc.document_type} />
                    </TableCell>
                    <TableCell>
                      {doc.classification_confidence == null ? (
                        <span className="text-slate-400">—</span>
                      ) : (
                        <div className="flex items-center gap-2">
                          <Progress value={doc.classification_confidence * 100} className="w-16" />
                          <span className="text-xs text-slate-500">
                            {formatPercent(doc.classification_confidence)}
                          </span>
                        </div>
                      )}
                    </TableCell>
                    <TableCell className="text-slate-600">{doc.page_count ?? "—"}</TableCell>
                    <TableCell className="text-slate-500">{formatDate(doc.uploaded_at)}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button variant="outline" size="sm" onClick={() => setSelectedDoc(doc)}>
                          View
                        </Button>
                        {doc.document_type !== "POLICY" && (
                          <Button
                            variant="destructive"
                            size="sm"
                            disabled={deletingId === doc.id}
                            onClick={async () => {
                              if (!confirm(`Delete "${doc.original_filename}"? This cannot be undone.`)) return;
                              setDeletingId(doc.id);
                              try {
                                await deleteDocument(doc.id);
                              } catch (err) {
                                alert("Failed to delete: " + (err instanceof Error ? err.message : String(err)));
                              } finally {
                                setDeletingId(null);
                              }
                            }}
                          >
                            {deletingId === doc.id ? "Deleting…" : "Delete"}
                          </Button>
                        )}
                      </div>
                    </TableCell>

                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Dialog open={!!selectedDoc} onOpenChange={(open) => !open && setSelectedDoc(null)}>
        <DialogContent onClose={() => setSelectedDoc(null)}>
          <DialogHeader>
            <DialogTitle>Document details</DialogTitle>
          </DialogHeader>
          {selectedDoc && <DocumentViewer documentId={selectedDoc.id} />}
        </DialogContent>
      </Dialog>
    </>
  );
}
