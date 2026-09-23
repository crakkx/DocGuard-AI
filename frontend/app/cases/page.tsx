"use client";

import { useEffect, useState } from "react";
import { useCases } from "@/hooks/useCases";
import { CaseList } from "@/components/cases/CaseList";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { CASE_STATUSES, RISK_LEVELS } from "@/lib/constants";
import { WifiOff } from "lucide-react";

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
    <div className="flex flex-col gap-4">
      <Card>
        <CardContent className="flex flex-col gap-3 pt-5 sm:flex-row sm:items-center sm:gap-3">
          <Input
            placeholder="Search vendor, PO, invoice, case number…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="sm:max-w-xs"
          />
          <Select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="sm:max-w-[180px]"
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
            className="sm:max-w-[180px]"
          >
            <option value="">All risk levels</option>
            {RISK_LEVELS.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </Select>
        </CardContent>
      </Card>

      {isLoading ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : isError || !data ? (
        <EmptyState
          icon={WifiOff}
          title="Could not load cases"
          description={
            error instanceof Error
              ? error.message
              : "Check that the backend is running and NEXT_PUBLIC_API_URL is set correctly."
          }
        />
      ) : (
        <Card>
          <CardContent className="pt-5">
            <CaseList cases={data} />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
