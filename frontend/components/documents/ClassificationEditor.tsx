"use client";

import { useState } from "react";
import { Select } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useClassifyDocument } from "@/hooks/useDocuments";
import { useToast } from "@/components/ui/toast";
import { DOCUMENT_TYPES } from "@/lib/constants";
import { formatPercent } from "@/lib/utils";

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

  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex flex-wrap items-center gap-2">
        <Select
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
          disabled={isPending}
          className="w-48"
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
        <span className="text-xs text-slate-500">
          Classifier confidence: {formatPercent(currentConfidence)}
        </span>
      </div>
      <Button size="sm" onClick={handleSave} disabled={isPending || !selected || selected === currentType}>
        {isPending && <Spinner className="h-3.5 w-3.5" />}
        Save
      </Button>
    </div>
  );
}
