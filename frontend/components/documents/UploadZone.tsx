"use client";

import { useCallback, useRef, useState } from "react";
import { UploadCloud, FileCheck2 } from "lucide-react";
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
        "relative flex cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed py-10 px-6 sm:py-12 text-center transition-all duration-200",
        isDragging
          ? "border-blue-500 bg-blue-50/50 shadow-inner"
          : "border-slate-200/90 bg-white hover:border-slate-300 hover:bg-slate-50/40 shadow-xs",
        uploading && "pointer-events-none cursor-default opacity-80"
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
        <div className="flex flex-col items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-50 text-blue-600">
            <Spinner className="h-6 w-6" />
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-800">
              Uploading {currentFileName ?? "…"} ({Math.min(queueDone + 1, queueTotal)}/{queueTotal})
            </p>
            <p className="text-xs text-slate-500 mt-0.5">Please wait while the document is processed</p>
          </div>
          <Progress value={(queueDone / queueTotal) * 100} className="w-56 mt-1" />
        </div>
      ) : (
        <>
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-50 text-blue-600 transition-transform group-hover:scale-105">
            <UploadCloud className="h-6 w-6" />
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-800">
              Drag & drop your PDF documents here, or <span className="text-blue-600 underline underline-offset-2">browse</span>
            </p>
            <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
              Supports Purchase Orders, Invoices, Goods Receipts, and Compliance Policies
            </p>
          </div>
          <div className="mt-1 flex flex-wrap items-center justify-center gap-2">
            <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] font-medium text-slate-600">
              <FileCheck2 className="h-3 w-3 text-slate-400" /> PDF only
            </span>
            <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] font-medium text-slate-600">
              Up to 50 MB
            </span>
            <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] font-medium text-slate-600">
              Auto classification & OCR
            </span>
          </div>
        </>
      )}
    </div>
  );
}
