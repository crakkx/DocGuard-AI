"use client";

import { useDocument } from "@/hooks/useDocuments";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ClassificationEditor } from "@/components/documents/ClassificationEditor";
import { DocumentTypeBadge } from "@/components/documents/DocumentList";
import { formatDateTime, formatPercent } from "@/lib/utils";
import { AlertTriangle, FileSearch, FileText } from "lucide-react";
import type { ExtractedField } from "@/types";

function formatFieldValue(field: ExtractedField): string {
  const value = field.field_value;
  if (value == null || value === "") return "—";
  const type = (field.field_type || "").toLowerCase();
  const looksNumeric = ["amount", "currency", "price", "total", "quantity", "number"].some((k) =>
    type.includes(k)
  );
  if (looksNumeric) {
    const num = Number(value);
    if (!Number.isNaN(num)) {
      return num.toLocaleString("en-IN", { maximumFractionDigits: 2 });
    }
  }
  return value;
}

export function DocumentViewer({ documentId }: { documentId: string }) {
  const { data: doc, isLoading, isError, error } = useDocument(documentId);

  if (isLoading) {
    return (
      <div className="flex flex-col gap-4 py-2">
        <Skeleton className="h-10 w-2/3 rounded-lg" />
        <Skeleton className="h-28 w-full rounded-xl" />
        <Skeleton className="h-44 w-full rounded-xl" />
      </div>
    );
  }

  if (isError || !doc) {
    return (
      <EmptyState
        icon={AlertTriangle}
        title="Could not load this document"
        description={error instanceof Error ? error.message : "Please try again."}
      />
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {/* File Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-2 border-b border-slate-100">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600 border border-blue-100">
            <FileText className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <p className="break-all text-sm font-semibold text-slate-900 leading-snug">
              {doc.original_filename}
            </p>
            <p className="text-xs text-slate-500 mt-0.5">
              Uploaded {formatDateTime(doc.uploaded_at)} · {doc.page_count ?? "—"}{" "}
              {doc.page_count === 1 ? "page" : "pages"}
            </p>
          </div>
        </div>
        <DocumentTypeBadge type={doc.document_type} />
      </div>

      {/* Classification Card */}
      <div className="rounded-xl border border-slate-200/90 bg-slate-50/60 p-4">
        <p className="mb-2.5 text-xs font-semibold uppercase tracking-wider text-slate-600">
          Classification & Type
        </p>
        <ClassificationEditor
          documentId={doc.id}
          currentType={doc.document_type}
          currentConfidence={doc.classification_confidence}
        />
      </div>

      {/* Extracted Fields */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-600">
            Extracted Fields
          </p>
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
            {doc.extracted_data.length} fields
          </span>
        </div>

        {doc.extracted_data.length === 0 ? (
          <EmptyState
            icon={FileSearch}
            title="No extracted fields"
            description="This document has no extracted data yet."
          />
        ) : (
          <div className="flex flex-col gap-2.5 max-h-[360px] overflow-y-auto pr-1">
            {doc.extracted_data.map((field) => (
              <div
                key={field.id}
                className="rounded-xl border border-slate-200/80 bg-white p-3.5 shadow-xs transition-shadow hover:shadow-sm"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                      {field.field_name}
                    </p>
                    <p className="mt-0.5 truncate text-sm font-medium text-slate-900">
                      {formatFieldValue(field)}
                    </p>
                  </div>
                  <Badge variant="outline" className="shrink-0 text-slate-600 font-mono text-[11px]">
                    {field.source_page != null ? `p.${field.source_page}` : "—"}
                  </Badge>
                </div>
                <div className="mt-2.5 flex items-center gap-2.5">
                  <Progress value={(field.confidence ?? 0) * 100} className="h-1.5 flex-1" />
                  <span className="shrink-0 text-xs font-medium text-slate-500 tabular-nums">
                    {formatPercent(field.confidence)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
