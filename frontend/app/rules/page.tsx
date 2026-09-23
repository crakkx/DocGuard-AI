"use client";

import { usePendingRules, useRules } from "@/hooks/useRules";
import { ExtractedRulesList } from "@/components/rules/ExtractedRulesList";
import { ConfirmedRules } from "@/components/rules/ConfirmedRules";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { WifiOff, ShieldOff } from "lucide-react";

function LoadingList() {
  return (
    <div className="flex flex-col gap-3">
      <Skeleton className="h-32" />
      <Skeleton className="h-32" />
    </div>
  );
}

export default function RulesPage() {
  const pending = usePendingRules();
  const confirmed = useRules("CONFIRMED");
  const all = useRules();

  const disabledAndRejected = (all.data ?? []).filter(
    (r) => r.status === "DISABLED" || r.status === "REJECTED"
  );

  return (
    <div className="flex flex-col gap-6">
      <Tabs defaultValue="pending">
        <TabsList>
          <TabsTrigger
            value="pending"
            badge={
              pending.data ? <Badge variant="secondary">{pending.data.length}</Badge> : undefined
            }
          >
            Pending
          </TabsTrigger>
          <TabsTrigger
            value="active"
            badge={
              confirmed.data ? <Badge variant="secondary">{confirmed.data.length}</Badge> : undefined
            }
          >
            Active
          </TabsTrigger>
          <TabsTrigger
            value="disabled"
            badge={
              all.data ? <Badge variant="secondary">{disabledAndRejected.length}</Badge> : undefined
            }
          >
            Disabled
          </TabsTrigger>
        </TabsList>

        <TabsContent value="pending" className="mt-4">
          {pending.isLoading ? (
            <LoadingList />
          ) : pending.isError ? (
            <EmptyState
              icon={WifiOff}
              title="Could not load pending rules"
              description={pending.error instanceof Error ? pending.error.message : undefined}
            />
          ) : (
            <ExtractedRulesList rules={pending.data ?? []} />
          )}
        </TabsContent>

        <TabsContent value="active" className="mt-4">
          {confirmed.isLoading ? (
            <LoadingList />
          ) : confirmed.isError ? (
            <EmptyState
              icon={WifiOff}
              title="Could not load active rules"
              description={confirmed.error instanceof Error ? confirmed.error.message : undefined}
            />
          ) : (
            <ConfirmedRules
              rules={confirmed.data ?? []}
              emptyTitle="No active rules yet"
              emptyDescription="Confirm rules from the Pending tab to activate them."
            />
          )}
        </TabsContent>

        <TabsContent value="disabled" className="mt-4">
          {all.isLoading ? (
            <LoadingList />
          ) : all.isError ? (
            <EmptyState
              icon={WifiOff}
              title="Could not load rules"
              description={all.error instanceof Error ? all.error.message : undefined}
            />
          ) : (
            <ConfirmedRules
              rules={disabledAndRejected}
              emptyTitle="No disabled or rejected rules"
              emptyIcon={ShieldOff}
            />
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
