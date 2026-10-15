"use client";

import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { MobileNav } from "./MobileNav";
import { Search, Bell } from "lucide-react";

const TITLES: Record<string, { title: string; subtitle: string }> = {
  "/":           { title: "Dashboard",          subtitle: "Overview & metrics" },
  "/documents":  { title: "Documents",           subtitle: "Upload & manage files" },
  "/cases":      { title: "Procurement Cases",   subtitle: "Review & audit cases" },
  "/policies":   { title: "Policies",            subtitle: "Compliance policy documents" },
  "/rules":      { title: "Compliance Rules",    subtitle: "Rule engine configuration" },
};

function titleFor(pathname: string) {
  if (TITLES[pathname]) return TITLES[pathname];
  if (pathname.startsWith("/cases/")) return { title: "Case Detail", subtitle: "Compliance findings & review" };
  return { title: "DocGuard AI", subtitle: "Procurement compliance" };
}

export function Header() {
  const pathname = usePathname();
  const { data, isError } = useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    retry: 0,
    refetchInterval: 30_000,
  });

  const { title, subtitle } = titleFor(pathname);
  const dotClass = isError ? "offline" : data ? "online" : "pending";
  const statusText = isError ? "Backend offline" : data ? "Connected" : "Connecting…";

  return (
    <header
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        height: 60,
        padding: "0 24px",
        borderBottom: "1px solid var(--border)",
        background: "var(--bg-surface)",
        flexShrink: 0,
        zIndex: 10,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <MobileNav />
        <div>
          <h1 style={{ fontSize: 15.5, fontWeight: 700, color: "var(--text-primary)", lineHeight: 1.2, letterSpacing: "-0.01em" }}>
            {title}
          </h1>
          <p style={{ fontSize: 11.5, color: "var(--text-muted)", lineHeight: 1.3, marginTop: 1 }}>
            {subtitle}
          </p>
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        {/* Search bar */}
        <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
          <Search size={13} style={{ position: "absolute", left: 10, color: "var(--text-muted)", pointerEvents: "none" }} />
          <input
            placeholder="Search…"
            style={{
              paddingLeft: 30, paddingRight: 12,
              height: 32, width: 200,
              border: "1px solid var(--border)",
              borderRadius: 8,
              background: "var(--bg-muted)",
              fontSize: 13,
              color: "var(--text-primary)",
              outline: "none",
              fontFamily: "inherit",
            }}
          />
        </div>

        {/* Bell */}
        <button style={{
          width: 32, height: 32,
          border: "1px solid var(--border)",
          borderRadius: 8,
          background: "var(--bg-surface)",
          display: "flex", alignItems: "center", justifyContent: "center",
          cursor: "pointer",
          color: "var(--text-secondary)",
        }}>
          <Bell size={14} />
        </button>

        {/* Divider */}
        <div style={{ width: 1, height: 20, background: "var(--border)" }} />

        {/* Backend status */}
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span className={`dg-status-dot ${dotClass}`} />
          <span style={{ fontSize: 12, color: "var(--text-muted)", fontWeight: 500 }}>
            {statusText}
          </span>
        </div>

        {/* Avatar */}
        <div style={{
          width: 32, height: 32, borderRadius: "50%",
          background: "#3B82F6",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 12, fontWeight: 700, color: "#fff",
          flexShrink: 0,
        }}>
          P
        </div>
      </div>
    </header>
  );
}
