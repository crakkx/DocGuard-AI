"use client";

import { useState } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { formatDate, formatPercent, formatCurrency } from "@/lib/utils";
import { useDocuments } from "@/hooks/useDocuments";
import { useLinkDocument, useUnlinkDocument } from "@/hooks/useCases";
import { useToast } from "@/components/ui/toast";
import { FileText, Link2, Unlink } from "lucide-react";
import type { CaseDetail, DocumentItem, DocumentType } from "@/types";

interface Slot {
  key: "po" | "invoice" | "grn";
  label: string;
  documentType: DocumentType;
  document: DocumentItem | null;
}

function formatFieldValue(fieldName: string, rawValue: string): string {
  if (!rawValue) return "—";

  // Try parsing JSON if it looks like an object or array
  const trimmed = rawValue.trim();
  if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
    try {
      const parsed = JSON.parse(trimmed);
      if (Array.isArray(parsed)) {
        if (parsed.length === 0) return "0 items";
        const first = parsed[0];
        const desc = first?.item_description || first?.description || first?.name || "Item";
        if (parsed.length === 1) return String(desc);
        return `${desc} (+${parsed.length - 1} more)`;
      } else if (typeof parsed === "object" && parsed !== null) {
        // e.g. {"CGST": {"rate": "9%", "amount": "27000.00"}, "SGST": ...}
        const parts: string[] = [];
        for (const [k, v] of Object.entries(parsed)) {
          if (typeof v === "object" && v !== null && "amount" in v) {
            parts.push(`${k}: ${formatCurrency(Number((v as any).amount))}`);
          } else if (typeof v === "object" && v !== null && "rate" in v) {
            parts.push(`${k}: ${(v as any).rate}`);
          } else if (typeof v === "string" || typeof v === "number") {
            parts.push(`${k}: ${v}`);
          }
        }
        if (parts.length > 0) return parts.join(", ");
        return JSON.stringify(parsed);
      }
    } catch {
      // not valid JSON, proceed to standard format
    }
  }

  // Format currency/amounts
  if (["total_amount", "subtotal", "unit_price", "amount"].includes(fieldName.toLowerCase())) {
    const num = Number(rawValue.replace(/,/g, ""));
    if (!Number.isNaN(num)) {
      return formatCurrency(num);
    }
  }

  return rawValue;
}

export function DocumentComparison({ caseDetail }: { caseDetail: CaseDetail }) {
  const slots: Slot[] = [
    { key: "po", label: "Purchase Order", documentType: "PURCHASE_ORDER", document: caseDetail.po_document },
    { key: "invoice", label: "Invoice", documentType: "INVOICE", document: caseDetail.invoice_document },
    { key: "grn", label: "Goods Receipt", documentType: "GOODS_RECEIPT", document: caseDetail.grn_document },
  ];

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
      {slots.map((slot) => (
        <DocumentSlot key={slot.key} caseId={caseDetail.id} slot={slot} />
      ))}
    </div>
  );
}

function DocumentSlot({ caseId, slot }: { caseId: string; slot: Slot }) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const { mutate: unlink, isPending: isUnlinking } = useUnlinkDocument(caseId);
  const { toast } = useToast();

  function handleUnlink() {
    if (!slot.document) return;
    unlink(slot.document.id, {
      onSuccess: () => toast({ title: `${slot.label} unlinked`, variant: "success" }),
      onError: (err) =>
        toast({
          title: "Unlink failed",
          description: err instanceof Error ? err.message : undefined,
          variant: "error",
        }),
    });
  }

  return (
    <Card className="overflow-hidden min-w-0 border border-slate-200/90 shadow-sm bg-white flex flex-col">
      <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0 pb-3 border-b border-slate-100">
        <div className="min-w-0 flex-1">
          <CardTitle className="text-base font-semibold text-slate-900">{slot.label}</CardTitle>
          {slot.document && (
            <CardDescription className="truncate text-xs text-slate-500 mt-0.5" title={slot.document.original_filename}>
              {slot.document.original_filename}
            </CardDescription>
          )}
        </div>
        {slot.document && (
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-slate-400 hover:text-red-600 hover:bg-red-50 shrink-0"
            onClick={handleUnlink}
            disabled={isUnlinking}
            title="Unlink document"
          >
            {isUnlinking ? <Spinner /> : <Unlink className="h-4 w-4" />}
          </Button>
        )}
      </CardHeader>
      <CardContent className="p-4 sm:p-5 flex-1 flex flex-col min-w-0">
        {slot.document ? (
          <div className="flex flex-col gap-3 min-w-0">
            <p className="text-xs text-slate-400 pb-1 border-b border-slate-100/80">
              Uploaded {formatDate(slot.document.uploaded_at)}
              {slot.document.page_count ? ` · ${slot.document.page_count} page(s)` : ""}
            </p>
            {slot.document.extracted_data.length === 0 ? (
              <p className="text-xs italic text-slate-400 py-3">No extracted fields.</p>
            ) : (
              <dl className="flex flex-col divide-y divide-slate-100 text-xs min-w-0">
                {slot.document.extracted_data.map((f) => (
                  <div key={f.id} className="flex items-center justify-between gap-3 py-2 min-w-0">
                    <dt className="text-slate-500 font-medium shrink-0 max-w-[120px] truncate text-[11.5px]" title={f.field_name}>
                      {f.field_name.replace(/_/g, " ")}
                    </dt>
                    <dd className="flex items-center justify-end gap-1.5 text-right font-medium text-slate-800 min-w-0 flex-1">
                      <span
                        className="truncate text-xs text-slate-800 font-medium block min-w-0"
                        title={typeof f.field_value === "string" ? f.field_value : JSON.stringify(f.field_value)}
                      >
                        {formatFieldValue(f.field_name, f.field_value)}
                      </span>
                      <span className="shrink-0 rounded-full bg-slate-100 px-1.5 py-0.5 text-[10px] font-normal text-slate-500 tabular-nums">
                        {formatPercent(f.confidence)}
                      </span>
                    </dd>
                  </div>
                ))}
              </dl>
            )}
          </div>
        ) : (
          <EmptyState
            icon={FileText}
            title="Not linked"
            description={`No ${slot.label.toLowerCase()} linked to this case yet.`}
            action={
              <Button
                size="sm"
                variant="outline"
                className="h-8 gap-1.5 text-xs font-medium text-slate-700 border-slate-200 mt-2"
                onClick={() => setPickerOpen(true)}
              >
                <Link2 className="h-3.5 w-3.5" />
                Link Document
              </Button>
            }
          />
        )}
      </CardContent>
      <DocumentPicker
        open={pickerOpen}
        onOpenChange={setPickerOpen}
        caseId={caseId}
        slotLabel={slot.label}
        documentType={slot.documentType}
      />
    </Card>
  );
}

function DocumentPicker({
  open,
  onOpenChange,
  caseId,
  slotLabel,
  documentType,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  caseId: string;
  slotLabel: string;
  documentType: DocumentType;
}) {
  const { data: documents, isLoading } = useDocuments();
  const { mutate: link, isPending } = useLinkDocument(caseId);
  const { toast } = useToast();

  const candidates = (documents ?? []).filter((d) => d.document_type === documentType);

  function handleLink(documentId: string) {
    link(documentId, {
      onSuccess: () => {
        toast({ title: `${slotLabel} linked`, variant: "success" });
        onOpenChange(false);
      },
      onError: (err) =>
        toast({
          title: "Link failed",
          description: err instanceof Error ? err.message : undefined,
          variant: "error",
        }),
    });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent onClose={() => onOpenChange(false)}>
        <DialogHeader>
          <DialogTitle>Link a {slotLabel}</DialogTitle>
          <DialogDescription>
            Select an uploaded {documentType.replace(/_/g, " ").toLowerCase()} document to link to this case.
          </DialogDescription>
        </DialogHeader>
        {isLoading ? (
          <div className="flex justify-center py-6">
            <Spinner />
          </div>
        ) : candidates.length === 0 ? (
          <EmptyState
            icon={FileText}
            title="No matching documents"
            description="Upload a document of this type first."
          />
        ) : (
          <div className="flex max-h-72 flex-col divide-y divide-slate-100 overflow-y-auto">
            {candidates.map((doc) => (
              <button
                key={doc.id}
                onClick={() => handleLink(doc.id)}
                disabled={isPending}
                className="flex items-center justify-between gap-2 py-2.5 text-left text-sm hover:bg-slate-50 disabled:opacity-50"
              >
                <span className="truncate">{doc.original_filename}</span>
                <span className="shrink-0 text-xs text-slate-400">{formatDate(doc.uploaded_at)}</span>
              </button>
            ))}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
