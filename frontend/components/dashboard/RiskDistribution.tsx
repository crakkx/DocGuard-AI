import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import type { CaseSummary } from "@/types";

const LEVELS: { key: string; label: string; barColor: string; textColor: string; dotColor: string }[] = [
  { key: "CRITICAL", label: "Critical", barColor: "#EF4444", textColor: "#EF4444", dotColor: "#EF4444" },
  { key: "HIGH",     label: "High",     barColor: "#F97316", textColor: "#F97316", dotColor: "#F97316" },
  { key: "MEDIUM",   label: "Medium",   barColor: "#F59E0B", textColor: "#F59E0B", dotColor: "#F59E0B" },
  { key: "LOW",      label: "Low",      barColor: "#22C55E", textColor: "#22C55E", dotColor: "#22C55E" },
];

export function RiskDistribution({ cases }: { cases: CaseSummary[] }) {
  const total = cases.length || 1;
  const counts = LEVELS.map((l) => ({
    ...l,
    count: cases.filter((c) => (c.risk_level || "LOW").toUpperCase() === l.key).length,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Risk Distribution</CardTitle>
        <CardDescription>Cases by risk level breakdown</CardDescription>
      </CardHeader>
      <CardContent style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {counts.map((l) => (
          <div key={l.key} style={{ display: "flex", alignItems: "center", gap: 10 }}>
            {/* Colored dot */}
            <div style={{ width: 8, height: 8, borderRadius: "50%", background: l.dotColor, flexShrink: 0 }} />
            <span style={{ width: 52, flexShrink: 0, fontSize: 12.5, fontWeight: 500, color: "var(--text-secondary)" }}>
              {l.label}
            </span>
            <div className="dg-progress-track" style={{ flex: 1 }}>
              <div
                className="dg-progress-fill"
                style={{
                  width: `${(l.count / total) * 100}%`,
                  background: l.barColor,
                }}
              />
            </div>
            <span style={{
              width: 24,
              flexShrink: 0,
              textAlign: "right",
              fontSize: 12.5,
              fontWeight: 600,
              color: l.count > 0 ? l.textColor : "var(--text-muted)",
            }}>
              {l.count}
            </span>
          </div>
        ))}

        <div style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          paddingTop: 10,
          borderTop: "1px solid var(--border)",
          marginTop: 2,
        }}>
          <span style={{ fontSize: 12, color: "var(--text-muted)", fontWeight: 500 }}>Total cases</span>
          <span style={{ fontSize: 13.5, fontWeight: 700, color: "var(--text-primary)" }}>
            {cases.length}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
