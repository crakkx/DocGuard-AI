"use client";

import { useState } from "react";
import { Eye, FileText, Filter, Inbox, Trash2, WifiOff } from "lucide-react";
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
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { DocumentViewer } from "@/components/documents/DocumentViewer";
import type { DocumentItem } from "@/types";

export function DocumentTypeBadge({ type }: { type: string | null | undefined }) {
  if (!type) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200">
        <span className="h-1.5 w-1.5 rounded-full bg-slate-400" />
        Unclassified
      </span>
    );
  }
  const t = type.toUpperCase();
  if (t === "PURCHASE_ORDER") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200/80">
        <span className="h-1.5 w-1.5 rounded-full bg-blue-500" />
        Purchase Order
      </span>
    );
  }
  if (t === "INVOICE") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold bg-purple-50 text-purple-700 border border-purple-200/80">
        <span className="h-1.5 w-1.5 rounded-full bg-purple-500" />
        Invoice
      </span>
    );
  }
  if (t === "GOODS_RECEIPT") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/80">
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
        Goods Receipt
      </span>
    );
  }
  if (t === "POLICY") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-200/80">
        <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
        Policy
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
      {type.replace(/_/g, " ")}
    </span>
  );
}

export function DocumentList() {
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [selectedDoc, setSelectedDoc] = useState<DocumentItem | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const { data: documents, isLoading, isError, error } = useDocuments(typeFilter || undefined);
  const { mutateAsync: deleteDocument } = useDeleteDocument();

  return (
    <>
      <Card className="overflow-hidden border border-slate-200/90 shadow-sm">
        <CardHeader className="border-b border-slate-100 bg-white py-5 px-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle className="text-base font-semibold text-slate-900">Documents</CardTitle>
              <CardDescription className="text-xs text-slate-500 mt-0.5">
                All uploaded purchase orders, invoices, goods receipts and compliance policies.
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-slate-400 shrink-0" />
              <Select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="w-full sm:w-52 h-9 text-xs font-medium bg-slate-50 border-slate-200"
                aria-label="Filter by document type"
              >
                <option value="">All document types</option>
                {DOCUMENT_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t.replace(/_/g, " ")}
                  </option>
                ))}
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex flex-col gap-3 p-6">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full rounded-lg" />
              ))}
            </div>
          ) : isError ? (
            <div className="p-8">
              <EmptyState
                icon={WifiOff}
                title="Could not load documents"
                description={
                  error instanceof Error
                    ? error.message
                    : "Check that the backend is running and NEXT_PUBLIC_API_URL is set correctly."
                }
              />
            </div>
          ) : !documents || documents.length === 0 ? (
            <div className="p-8">
              <EmptyState
                icon={Inbox}
                title="No documents yet"
                description="Upload a PO, invoice, goods receipt or policy above to get started."
              />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="whitespace-nowrap min-w-[200px]">Filename</TableHead>
                  <TableHead className="whitespace-nowrap min-w-[130px]">Type</TableHead>
                  <TableHead className="whitespace-nowrap min-w-[120px]">Confidence</TableHead>
                  <TableHead className="whitespace-nowrap min-w-[80px]">Pages</TableHead>
                  <TableHead className="whitespace-nowrap min-w-[110px]">Uploaded</TableHead>
                  <TableHead className="text-right whitespace-nowrap min-w-[120px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {documents.map((doc) => (
                  <TableRow key={doc.id}>
                    <TableCell className="max-w-[260px] font-medium text-slate-900">
                      <div className="flex items-center gap-3">
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-500">
                          <FileText className="h-4 w-4" />
                        </div>
                        <span className="truncate text-sm font-medium text-slate-900" title={doc.original_filename}>
                          {doc.original_filename}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="whitespace-nowrap">
                      <DocumentTypeBadge type={doc.document_type} />
                    </TableCell>
                    <TableCell className="whitespace-nowrap">
                      {doc.classification_confidence == null ? (
                        <span className="text-slate-400 text-xs">—</span>
                      ) : (
                        <div className="flex items-center gap-2.5">
                          <Progress
                            value={doc.classification_confidence * 100}
                            className="w-20"
                            indicatorClassName={
                              doc.classification_confidence >= 0.9
                                ? "bg-emerald-500"
                                : doc.classification_confidence >= 0.7
                                  ? "bg-blue-600"
                                  : "bg-amber-500"
                            }
                          />
                          <span className="text-xs font-medium text-slate-600 tabular-nums">
                            {formatPercent(doc.classification_confidence)}
                          </span>
                        </div>
                      )}
                    </TableCell>
                    <TableCell className="text-xs text-slate-500 tabular-nums whitespace-nowrap">
                      {doc.page_count != null ? `${doc.page_count} pg` : "—"}
                    </TableCell>
                    <TableCell className="text-xs text-slate-500 tabular-nums whitespace-nowrap">
                      {formatDate(doc.uploaded_at)}
                    </TableCell>
                    <TableCell className="text-right whitespace-nowrap">
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setSelectedDoc(doc)}
                          className="h-8 gap-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 border-slate-200"
                        >
                          <Eye className="h-3.5 w-3.5 text-slate-500" />
                          View
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={deletingId === doc.id}
                          className="h-8 gap-1.5 text-xs text-slate-400 hover:text-red-600 hover:bg-red-50"
                          title="Delete document"
                          onClick={async () => {
                            if (!confirm(`Delete "${doc.original_filename}"? This will permanently delete it from the database.`)) return;
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
                          <Trash2 className="h-3.5 w-3.5" />
                          {deletingId === doc.id ? "Deleting…" : "Delete"}
                        </Button>
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
        <DialogContent className="max-w-2xl p-6 sm:p-7" onClose={() => setSelectedDoc(null)}>
          <DialogHeader>
            <DialogTitle>Document Details</DialogTitle>
          </DialogHeader>
          {selectedDoc && <DocumentViewer documentId={selectedDoc.id} />}
        </DialogContent>
      </Dialog>
    </>
  );
}
