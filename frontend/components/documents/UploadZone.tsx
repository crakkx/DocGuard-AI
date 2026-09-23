"use client";

import { useCallback, useRef, useState } from "react";
import { UploadCloud } from "lucide-react";
import { useUploadDocument } from "@/hooks/useDocuments";
import { useToast } from "@/components/ui/toast";
import { Spinner } from "@/components/ui/spinner";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";

export function UploadZone() {
  const [isDragging, setIsDragging] = useState(false);
  const [queueTotal, setQueueTotal] = useState(0);
  const [queueDone, setQueueDone] = useState(0);
  const [currentFileName, setCurrentFileName] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const { mutateAsync } = useUploadDocument();
  const { toast } = useToast();

  const uploading = queueTotal > 0 && queueDone < queueTotal;

  const uploadFiles = useCallback(
    async (files: File[]) => {
      const pdfFiles = files.filter(
        (f) => f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf")
      );
      const skipped = files.length - pdfFiles.length;
      if (skipped > 0) {
        toast({
          title: "Some files were skipped",
          description: `${skipped} file${skipped === 1 ? "" : "s"} were not PDFs and were ignored.`,
          variant: "error",
        });
      }
      if (pdfFiles.length === 0) return;

      setQueueTotal(pdfFiles.length);
      setQueueDone(0);

      for (const file of pdfFiles) {
        setCurrentFileName(file.name);
        try {
          const result = await mutateAsync(file);
          const description = result.case_id
            ? `Linked to case ${result.case_number ?? result.case_id}.`
            : result.document_type === "POLICY"
              ? "Classified as POLICY — ingest it from the Policies page instead."
              : "Uploaded successfully.";
          toast({ title: `${file.name} uploaded`, description, variant: "success" });
        } catch (err) {
          toast({
            title: `Failed to upload ${file.name}`,
            description: err instanceof Error ? err.message : "Please try again.",
            variant: "error",
          });
        } finally {
          setQueueDone((prev) => prev + 1);
        }
      }

      setCurrentFileName(null);
      setQueueTotal(0);
      setQueueDone(0);
    },
    [mutateAsync, toast]
  );

  const handleFiles = useCallback(
    (fileList: FileList | null) => {
      if (!fileList || fileList.length === 0) return;
      void uploadFiles(Array.from(fileList));
    },
    [uploadFiles]
  );

  return (
    <div
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 text-center transition-colors",
        isDragging ? "border-slate-400 bg-slate-50" : "border-slate-200 bg-white",
        uploading && "pointer-events-none cursor-default opacity-70"
      )}
      onDragOver={(e) => {
        e.preventDefault();
        if (!uploading) setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragging(false);
        if (!uploading) handleFiles(e.dataTransfer.files);
      }}
      role="button"
      tabIndex={0}
      onClick={() => !uploading && inputRef.current?.click()}
      onKeyDown={(e) => {
        if ((e.key === "Enter" || e.key === " ") && !uploading) {
          e.preventDefault();
          inputRef.current?.click();
        }
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        multiple
        className="hidden"
        disabled={uploading}
        onChange={(e) => {
          handleFiles(e.target.files);
          e.target.value = "";
        }}
      />
      {uploading ? (
        <>
          <Spinner className="h-6 w-6 text-slate-500" />
          <p className="text-sm font-medium text-slate-700">
            Uploading {currentFileName ?? "…"} ({Math.min(queueDone + 1, queueTotal)}/{queueTotal})
          </p>
          <Progress value={(queueDone / queueTotal) * 100} className="mt-1 w-48" />
        </>
      ) : (
        <>
          <UploadCloud className="h-6 w-6 text-slate-400" />
          <p className="text-sm font-medium text-slate-700">
            Drag & drop a PDF here, or click to browse
          </p>
          <p className="text-xs text-slate-500">
            Purchase orders, invoices, goods receipts and policies (PDF only)
          </p>
        </>
      )}
    </div>
  );
}
