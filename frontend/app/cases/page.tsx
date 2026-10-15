"use client";

import { useEffect, useState } from "react";
import { useCases } from "@/hooks/useCases";
import { CaseList } from "@/components/cases/CaseList";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { CASE_STATUSES, RISK_LEVELS } from "@/lib/constants";
import { Search, WifiOff } from "lucide-react";

export default function CasesPage() {
  const [status, setStatus] = useState("");
  const [riskLevel, setRiskLevel] = useState("");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  const { data, isLoading, isError, error } = useCases({
    status: status || undefined,
    risk_level: riskLevel || undefined,
    search: debouncedSearch || undefined,
  });

  return (
    <div className="flex flex-col gap-6">
      {/* Filter Toolbar Card */}
      <Card className="border border-slate-200/90 shadow-sm bg-white p-4 sm:p-5">
        <div className="flex flex-col md:flex-row items-stretch md:items-center gap-3">
          <div className="relative flex-1 min-w-0">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input
              placeholder="Search vendor, PO, invoice, case number…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-10 h-10 bg-slate-50 border-slate-200 text-sm rounded-lg w-full"
            />
          </div>
          <div className="flex items-center gap-2.5 shrink-0">
            <Select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="w-40 sm:w-48 h-10 bg-slate-50 border-slate-200 text-sm font-medium rounded-lg"
            >
              <option value="">All statuses</option>
              {CASE_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s.replace(/_/g, " ")}
                </option>
              ))}
            </Select>
            <Select
              value={riskLevel}
              onChange={(e) => setRiskLevel(e.target.value)}
              className="w-40 sm:w-48 h-10 bg-slate-50 border-slate-200 text-sm font-medium rounded-lg"
            >
              <option value="">All risk levels</option>
              {RISK_LEVELS.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </Select>
          </div>
        </div>
      </Card>

      {/* Main Cases Table Card */}
      {isLoading ? (
        <Card className="border border-slate-200/90 p-6">
          <div className="flex flex-col gap-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full rounded-lg" />
            ))}
          </div>
        </Card>
      ) : isError || !data ? (
        <Card className="border border-slate-200/90 p-8">
          <EmptyState
            icon={WifiOff}
            title="Could not load cases"
            description={
              error instanceof Error
                ? error.message
                : "Check that the backend is running and NEXT_PUBLIC_API_URL is set correctly."
            }
          />
        </Card>
      ) : (
        <Card className="overflow-hidden border border-slate-200/90 shadow-sm bg-white">
          <CardHeader className="border-b border-slate-100 py-4 px-6">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base font-semibold text-slate-900">Procurement Cases</CardTitle>
                <CardDescription className="text-xs text-slate-500 mt-0.5">
                  Review compliance findings and audit histories for all transactions.
                </CardDescription>
              </div>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
                {data.length} {data.length === 1 ? "case" : "cases"}
              </span>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <CaseList cases={data} />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
