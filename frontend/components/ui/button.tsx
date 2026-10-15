import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium transition-all duration-150 cursor-pointer disabled:pointer-events-none disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-300 [&_svg]:pointer-events-none [&_svg]:shrink-0 active:scale-[0.98]",
  {
    variants: {
      variant: {
        default:
          "bg-blue-600 text-white hover:bg-blue-700 shadow-sm",
        destructive:
          "bg-red-50 border border-red-200 text-red-600 hover:bg-red-100",
        outline:
          "border border-[var(--border)] bg-white text-[var(--text-primary)] hover:bg-[var(--bg-muted)]",
        secondary:
          "bg-[var(--bg-muted)] border border-[var(--border)] text-[var(--text-secondary)] hover:bg-gray-200",
        ghost:
          "text-[var(--text-secondary)] hover:bg-[var(--bg-muted)] hover:text-[var(--text-primary)]",
        link:
          "text-blue-600 underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-10 rounded-lg px-6 text-sm font-semibold",
        icon: "h-9 w-9 p-0",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button ref={ref} className={cn(buttonVariants({ variant, size, className }))} {...props} />
    );
  }
);
Button.displayName = "Button";
