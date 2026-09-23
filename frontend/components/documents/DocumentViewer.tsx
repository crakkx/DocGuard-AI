"use client";

import { useDocument } from "@/hooks/useDocuments";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ClassificationEditor } from "@/components/documents/ClassificationEditor";
import { DocumentTypeBadge } from "@/components/documents/DocumentList";
import { formatDateTime, formatPercent } from "@/lib/utils";
import { AlertTriangle, FileSearch } from "lucide-react";
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
      <div className="flex flex-col gap-3">
        <Skeleton className="h-5 w-2/3" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-32 w-full" />
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
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="break-all text-sm font-medium text-slate-900">{doc.original_filename}</p>
          <p className="text-xs text-slate-500">
            Uploaded {formatDateTime(doc.uploaded_at)} · {doc.page_count ?? "—"}{" "}
            {doc.page_count === 1 ? "page" : "pages"}
          </p>
        </div>
        <DocumentTypeBadge type={doc.document_type} />
      </div>

      <div className="rounded-lg border border-slate-200 p-3">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Classification
        </p>
        <ClassificationEditor
          documentId={doc.id}
          currentType={doc.document_type}
          currentConfidence={doc.classification_confidence}
        />
      </div>

      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Extracted Fields ({doc.extracted_data.length})
        </p>
        {doc.extracted_data.length === 0 ? (
          <EmptyState
            icon={FileSearch}
            title="No extracted fields"
            description="This document has no extracted data yet."
          />
        ) : (
          <div className="flex flex-col gap-2">
            {doc.extracted_data.map((field) => (
              <div key={field.id} className="rounded-md border border-slate-200 p-2.5">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-slate-500">{field.field_name}</p>
                    <p className="truncate text-sm text-slate-900">{formatFieldValue(field)}</p>
                  </div>
                  <Badge variant="outline" className="shrink-0">
                    {field.source_page != null ? `p.${field.source_page}` : "—"}
                  </Badge>
                </div>
                <div className="mt-2 flex items-center gap-2">
                  <Progress value={(field.confidence ?? 0) * 100} className="h-1 flex-1" />
                  <span className="w-9 shrink-0 text-xs text-slate-500">
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
