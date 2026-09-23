"use client";

import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { MobileNav } from "./MobileNav";

const TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/documents": "Documents",
  "/cases": "Procurement Cases",
  "/policies": "Policies",
  "/rules": "Compliance Rules",
};

function titleFor(pathname: string): string {
  if (TITLES[pathname]) return TITLES[pathname];
  if (pathname.startsWith("/cases/")) return "Case Detail";
  return "DocGuard AI";
}

export function Header() {
  const pathname = usePathname();
  const { data, isError } = useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    retry: 0,
    refetchInterval: 30_000,
  });

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-4 sm:px-6">
      <div className="flex items-center gap-3">
        <MobileNav />
        <h1 className="text-sm font-semibold text-slate-900">{titleFor(pathname)}</h1>
      </div>
      <div className="flex items-center gap-2 text-xs text-slate-500">
        <span
          className={cn(
            "h-1.5 w-1.5 rounded-full",
            isError ? "bg-red-500" : data ? "bg-emerald-500" : "bg-slate-300"
          )}
        />
        {isError ? "Backend offline" : data ? "Backend connected" : "Connecting…"}
      </div>
    </header>
  );
}
