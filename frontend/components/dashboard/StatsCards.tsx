import { Briefcase, ShieldAlert, ShieldCheck, ClipboardList, AlertOctagon, FileCheck2 } from "lucide-react";
import type { DashboardStats } from "@/types";

const CARDS: {
  key: keyof DashboardStats;
  label: string;
  icon: typeof Briefcase;
  iconBg: string;
  iconColor: string;
  accentColor: string;
}[] = [
  {
    key: "total_cases", label: "Total Cases", icon: Briefcase,
    iconBg: "#EFF6FF", iconColor: "#3B82F6",
    accentColor: "#3B82F6",
  },
  {
    key: "compliant_cases", label: "Compliant", icon: ShieldCheck,
    iconBg: "#F0FDF4", iconColor: "#22C55E",
    accentColor: "#22C55E",
  },
  {
    key: "violation_cases", label: "Violations", icon: ShieldAlert,
    iconBg: "#FFF1F2", iconColor: "#EF4444",
    accentColor: "#EF4444",
  },
  {
    key: "needs_review_cases", label: "Needs Review", icon: ClipboardList,
    iconBg: "#FFFBEB", iconColor: "#F59E0B",
    accentColor: "#F59E0B",
  },
  {
    key: "high_risk_cases", label: "High Risk", icon: AlertOctagon,
    iconBg: "#FFF7ED", iconColor: "#F97316",
    accentColor: "#F97316",
  },
  {
    key: "pending_rules", label: "Pending Rules", icon: FileCheck2,
    iconBg: "#F5F3FF", iconColor: "#8B5CF6",
    accentColor: "#8B5CF6",
  },
];

export function StatsCards({ stats }: { stats: DashboardStats }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 14 }}>
      {CARDS.map(({ key, label, icon: Icon, iconBg, iconColor, accentColor }, i) => (
        <div
          key={key}
          className="dg-stat-card animate-fade-up"
          style={{ animationDelay: `${i * 50}ms` }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div
              className="dg-icon-pill"
              style={{ background: iconBg }}
            >
              <Icon size={17} color={iconColor} />
            </div>
            {/* Colored accent dot */}
            <div style={{
              width: 8, height: 8, borderRadius: "50%",
              background: accentColor,
              opacity: 0.7,
            }} />
          </div>

          <div>
            <p style={{ fontSize: 28, fontWeight: 700, color: "var(--text-primary)", lineHeight: 1, letterSpacing: "-0.03em" }}>
              {stats[key] as number}
            </p>
            <p style={{ fontSize: 12.5, color: "var(--text-muted)", marginTop: 4, fontWeight: 500 }}>
              {label}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
