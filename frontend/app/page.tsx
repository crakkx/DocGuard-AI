"use client";

import { useDashboardStats } from "@/hooks/useDashboard";
import { StatsCards } from "@/components/dashboard/StatsCards";
import { ReviewQueue } from "@/components/dashboard/ReviewQueue";
import { RiskDistribution } from "@/components/dashboard/RiskDistribution";
import { RecentCases } from "@/components/dashboard/RecentCases";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { WifiOff } from "lucide-react";

export default function DashboardPage() {
  const { data: stats, isLoading, isError, error } = useDashboardStats();

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (isError || !stats) {
    return (
      <EmptyState
        icon={WifiOff}
        title="Could not reach the DocGuard API"
        description={
          error instanceof Error
            ? error.message
            : "Check that the backend is running and NEXT_PUBLIC_API_URL is set correctly."
        }
      />
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <StatsCards stats={stats} />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <ReviewQueue cases={stats.queue} />
        </div>
        <RiskDistribution cases={stats.queue} />
      </div>
      <RecentCases cases={stats.recent_cases} />
    </div>
  );
}
