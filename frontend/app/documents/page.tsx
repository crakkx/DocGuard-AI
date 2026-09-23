"use client";

import { UploadZone } from "@/components/documents/UploadZone";
import { DocumentList } from "@/components/documents/DocumentList";

export default function DocumentsPage() {
  return (
    <div className="flex flex-col gap-6">
      <UploadZone />
      <DocumentList />
    </div>
  );
}
