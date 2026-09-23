"use client";

import { useRef, useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useToast } from "@/components/ui/toast";
import { useUploadPolicy, usePolicies } from "@/hooks/usePolicies";
import { UploadCloud, RefreshCw, PlusCircle } from "lucide-react";

export function PolicyUpload() {
  const { data: policies = [] } = usePolicies();
  const activePolicies = policies.filter((p) => p.is_active !== false);

  const [mode, setMode] = useState<"new" | "update">("new");
  const [selectedPolicyId, setSelectedPolicyId] = useState<string>("");
  const [title, setTitle] = useState("");
  const [version, setVersion] = useState("1.0");
  const [file, setFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();
  const uploadPolicy = useUploadPolicy();

  function handleModeChange(newMode: "new" | "update") {
    setMode(newMode);
    if (newMode === "update" && activePolicies.length > 0) {
      const target = activePolicies[0];
      setSelectedPolicyId(target.id);
      setTitle(target.title);
      const v = target.version || "1.0";
      const parts = v.split(".");
      const nextVer = parts.length > 1 ? `${parts[0]}.${parseInt(parts[1] || "0", 10) + 1}` : `${v}.1`;
      setVersion(nextVer);
    } else {
      setSelectedPolicyId("");
      setTitle("");
      setVersion("1.0");
    }
  }

  function handlePolicySelect(id: string) {
    setSelectedPolicyId(id);
    const target = activePolicies.find((p) => p.id === id);
    if (target) {
      setTitle(target.title);
      const v = target.version || "1.0";
      const parts = v.split(".");
      const nextVer = parts.length > 1 ? `${parts[0]}.${parseInt(parts[1] || "0", 10) + 1}` : `${v}.1`;
      setVersion(nextVer);
    }
  }

  const canSubmit = title.trim().length > 0 && !!file && !uploadPolicy.isPending;

  function reset() {
    if (mode === "new") {
      setTitle("");
      setVersion("1.0");
    }
    setFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file || !title.trim()) return;
    uploadPolicy.mutate(
      {
        file,
        title: title.trim(),
        version: version.trim() || undefined,
        existingPolicyId: mode === "update" ? selectedPolicyId : undefined,
      },
      {
        onSuccess: (policy) => {
          toast({
            title: mode === "update" ? "Updated policy uploaded" : "Policy uploaded",
            description: `"${policy.title}" (Version ${policy.version || "1.0"}) is processing in the background. Chunks and rules will appear shortly.`,
            variant: "success",
          });
          reset();
        },
        onError: (err) => {
          toast({
            title: "Upload rejected",
            description: err instanceof Error ? err.message : "Could not upload the policy document.",
            variant: "error",
          });
        },
      }
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div>
            <CardTitle>Upload policy document</CardTitle>
            <CardDescription>
              Upload a PDF to ingest it for retrieval-augmented search and rule extraction.
            </CardDescription>
          </div>
          {activePolicies.length > 0 && (
            <div className="flex gap-1.5 rounded-lg border border-slate-200 bg-slate-50 p-1 text-xs">
              <button
                type="button"
                onClick={() => handleModeChange("new")}
                className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 font-medium transition-colors ${
                  mode === "new"
                    ? "bg-white text-slate-900 shadow-sm"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                <PlusCircle className="h-3.5 w-3.5" /> New policy
              </button>
              <button
                type="button"
                onClick={() => handleModeChange("update")}
                className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 font-medium transition-colors ${
                  mode === "update"
                    ? "bg-white text-slate-900 shadow-sm"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                <RefreshCw className="h-3.5 w-3.5" /> Update existing
              </button>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {mode === "update" && activePolicies.length > 0 && (
            <div className="flex flex-col gap-1.5">
              <label htmlFor="select-existing-policy" className="text-xs font-medium text-slate-700">
                Select policy to update <span className="text-red-500">*</span>
              </label>
              <select
                id="select-existing-policy"
                value={selectedPolicyId}
                onChange={(e) => handlePolicySelect(e.target.value)}
                className="h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-slate-950"
              >
                {activePolicies.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.title} (Current: Version {p.version || "1.0"})
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-1.5">
              <label htmlFor="policy-title" className="text-xs font-medium text-slate-700">
                Title <span className="text-red-500">*</span>
              </label>
              <Input
                id="policy-title"
                placeholder="e.g. Procurement Policy 2026"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label htmlFor="policy-version" className="text-xs font-medium text-slate-700">
                Version <span className="text-slate-400">{mode === "update" ? "(bumped)" : "(optional)"}</span>
              </label>
              <Input
                id="policy-version"
                placeholder="e.g. 1.1"
                value={version}
                onChange={(e) => setVersion(e.target.value)}
              />
            </div>
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="policy-file" className="text-xs font-medium text-slate-700">
              PDF file <span className="text-red-500">*</span>
            </label>
            <Input
              id="policy-file"
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              required
            />
          </div>
          <div>
            <Button type="submit" disabled={!canSubmit}>
              {uploadPolicy.isPending ? (
                <>
                  <Spinner /> Uploading…
                </>
              ) : (
                <>
                  <UploadCloud className="h-4 w-4" /> {mode === "update" ? "Upload & update policy" : "Upload policy"}
                </>
              )}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

