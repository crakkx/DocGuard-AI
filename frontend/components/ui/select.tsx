import * as React from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

export const Select = React.forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className, children, ...props }, ref) => {
    return (
      <div className="relative inline-block w-full">
        <select
          ref={ref}
          className={cn(
            "h-9 w-full appearance-none rounded-lg border border-[var(--border)] bg-white pl-3 pr-8 text-sm text-[var(--text-primary)] transition-all duration-150 hover:border-gray-300 focus-visible:outline-none focus-visible:border-blue-500 focus-visible:ring-2 focus-visible:ring-blue-100 disabled:cursor-not-allowed disabled:opacity-50",
            className
          )}
          {...props}
        >
          {children}
        </select>
        <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-muted)]" />
      </div>
    );
  }
);
Select.displayName = "Select";
