import * as React from "react";
import { cn } from "@/lib/utils";

export function Card({ className, style, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("dg-card", className)}
      style={style}
      {...props}
    />
  );
}

export function CardHeader({ className, style, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("px-5 pt-4 pb-3", className)}
      style={style}
      {...props}
    />
  );
}

export function CardTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3
      className={cn("dg-section-title", className)}
      {...props}
    />
  );
}

export function CardDescription({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p
      className={cn("dg-section-desc", className)}
      style={{ marginTop: 2 }}
      {...props}
    />
  );
}

export function CardContent({ className, style, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("px-5 pb-5 pt-0", className)}
      style={style}
      {...props}
    />
  );
}

export function CardFooter({ className, style, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("flex items-center px-5 pb-4", className)}
      style={style}
      {...props}
    />
  );
}
