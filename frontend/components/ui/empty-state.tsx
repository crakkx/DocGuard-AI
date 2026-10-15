import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-[var(--border)] bg-[var(--bg-muted)] px-6 py-12 text-center",
        className
      )}
    >
      {Icon && (
        <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-[var(--border)] bg-white shadow-sm">
          <Icon className="h-5 w-5 text-[var(--text-muted)]" />
        </div>
      )}
      <div className="flex flex-col gap-1 items-center">
        <p className="text-sm font-semibold text-[var(--text-primary)]">{title}</p>
        {description && <p className="max-w-sm text-xs text-[var(--text-muted)] leading-relaxed">{description}</p>}
      </div>
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
