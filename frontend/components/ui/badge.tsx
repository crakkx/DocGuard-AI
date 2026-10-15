import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        default:     "bg-slate-100 text-slate-700 border border-slate-200/80",
        secondary:   "bg-slate-50 text-slate-600 border border-slate-200",
        destructive: "bg-red-50 text-red-700 border border-red-200/80",
        warning:     "bg-amber-50 text-amber-800 border border-amber-200/80",
        info:        "bg-blue-50 text-blue-700 border border-blue-200/80",
        success:     "bg-emerald-50 text-emerald-700 border border-emerald-200/80",
        purple:      "bg-purple-50 text-purple-700 border border-purple-200/80",
        outline:     "bg-white border border-slate-200 text-slate-600",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
