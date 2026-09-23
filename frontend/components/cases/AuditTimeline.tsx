import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { formatDateTime } from "@/lib/utils";
import { History } from "lucide-react";
import type { AuditEntry } from "@/types";

export function AuditTimeline({ entries }: { entries: AuditEntry[] }) {
  if (entries.length === 0) {
    return (
      <EmptyState
        icon={History}
        title="No audit history yet"
        description="Actions taken on this case will appear here."
      />
    );
  }

  return (
    <ol className="flex flex-col gap-0">
      {entries.map((entry, i) => (
        <li key={entry.id} className="relative flex gap-3 pb-6 last:pb-0">
          {i !== entries.length - 1 && (
            <span className="absolute left-[7px] top-4 h-full w-px bg-slate-200" aria-hidden />
          )}
          <span className="relative z-10 mt-1 h-3.5 w-3.5 shrink-0 rounded-full border-2 border-white bg-slate-400 shadow" />
          <div className="flex flex-1 flex-col gap-1">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="outline">{entry.action.replace(/_/g, " ")}</Badge>
              <span className="text-xs font-medium text-slate-700">{entry.actor}</span>
              <span className="text-xs text-slate-400">{formatDateTime(entry.created_at)}</span>
            </div>
            {entry.detail && <p className="text-sm text-slate-600">{entry.detail}</p>}
          </div>
        </li>
      ))}
    </ol>
  );
}
