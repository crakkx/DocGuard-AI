"use client";

import { useState } from "react";
import { Select } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useClassifyDocument } from "@/hooks/useDocuments";
import { useToast } from "@/components/ui/toast";
import { DOCUMENT_TYPES } from "@/lib/constants";
import { formatPercent } from "@/lib/utils";
import { Check } from "lucide-react";

export function ClassificationEditor({
  documentId,
  currentType,
  currentConfidence,
}: {
  documentId: string;
  currentType: string | null;
  currentConfidence: number | null;
}) {
  const [selected, setSelected] = useState(currentType ?? "");
  const { mutate, isPending } = useClassifyDocument();
  const { toast } = useToast();

  const handleSave = () => {
    if (!selected || selected === currentType) return;
    mutate(
      { id: documentId, documentType: selected },
      {
        onSuccess: (result) => {
          toast({
            title: "Classification updated",
            description: `Document reclassified as ${result.document_type.replace(/_/g, " ")}.`,
            variant: "success",
          });
        },
        onError: (err) => {
          toast({
            title: "Reclassification failed",
            description: err instanceof Error ? err.message : "Please try again.",
            variant: "error",
          });
        },
      }
    );
  };

  const hasChanged = selected && selected !== currentType;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col sm:flex-row sm:items-center gap-3">
        <div className="flex-1">
          <Select
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
            disabled={isPending}
            className="w-full bg-white border-slate-200 text-slate-800 font-medium"
          >
            <option value="" disabled>
              Select type…
            </option>
            {DOCUMENT_TYPES.map((t) => (
              <option key={t} value={t}>
                {t.replace(/_/g, " ")}
              </option>
            ))}
          </Select>
        </div>
        <Button
          size="sm"
          onClick={handleSave}
          disabled={isPending || !hasChanged}
          className="shrink-0 bg-blue-600 hover:bg-blue-700 text-white font-medium px-4 h-9 shadow-sm disabled:opacity-50"
        >
          {isPending ? (
            <Spinner className="h-4 w-4 mr-1.5" />
          ) : (
            <Check className="h-3.5 w-3.5 mr-1.5" />
          )}
          Save changes
        </Button>
      </div>

      <div className="flex items-center gap-2 pt-0.5">
        <span className="text-xs text-slate-500">Classifier confidence:</span>
        <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-700">
          {formatPercent(currentConfidence)}
        </span>
      </div>
    </div>
  );
}
