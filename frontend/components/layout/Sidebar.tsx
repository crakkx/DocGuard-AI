"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ShieldCheck } from "lucide-react";
import { NAV_ITEMS } from "./nav-items";
import { cn } from "@/lib/utils";

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      className="hidden md:flex"
      style={{
        width: 240,
        flexShrink: 0,
        display: "flex",
        flexDirection: "column",
        background: "#1A1D23",
        borderRight: "1px solid rgba(255,255,255,0.06)",
        height: "100vh",
      }}
    >
      {/* Logo */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          height: 60,
          padding: "0 18px",
          borderBottom: "1px solid rgba(255,255,255,0.07)",
          flexShrink: 0,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: 30,
            height: 30,
            borderRadius: 8,
            background: "#3B82F6",
            flexShrink: 0,
          }}
        >
          <ShieldCheck size={16} color="#fff" />
        </div>
        <div>
          <p style={{ fontSize: 14, fontWeight: 700, color: "#FFFFFF", lineHeight: 1.2 }}>
            DocGuard
          </p>
          <p style={{ fontSize: 10.5, color: "rgba(255,255,255,0.38)", fontWeight: 500, letterSpacing: "0.04em" }}>
            AI Compliance
          </p>
        </div>
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: "10px 10px", display: "flex", flexDirection: "column", gap: 2, overflowY: "auto" }}>
        <p style={{ fontSize: 10.5, fontWeight: 600, color: "rgba(255,255,255,0.28)", letterSpacing: "0.08em", textTransform: "uppercase", padding: "8px 10px 6px" }}>
          Main Menu
        </p>
        {NAV_ITEMS.map((item) => {
          const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn("dg-nav-link", active && "active")}
            >
              <Icon size={15} style={{ flexShrink: 0, opacity: active ? 1 : 0.65 }} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div
        style={{
          padding: "14px 16px",
          borderTop: "1px solid rgba(255,255,255,0.07)",
          flexShrink: 0,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
          <div style={{
            width: 30, height: 30, borderRadius: 8,
            background: "#2A2D35",
            border: "1px solid rgba(255,255,255,0.10)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 12, fontWeight: 700, color: "#9CA3AF",
          }}>
            P
          </div>
          <div>
            <p style={{ fontSize: 12.5, fontWeight: 500, color: "#D1D5DB" }}>Procurement Team</p>
            <p style={{ fontSize: 11, color: "rgba(255,255,255,0.28)" }}>v1.0.0</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
