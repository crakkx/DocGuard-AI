import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { FileSearch } from "lucide-react";

export function ExplanationPanel({ explanation }: { explanation: string | null }) {
  if (!explanation) {
    return (
      <EmptyState
        icon={FileSearch}
        title="No explanation yet"
        description="Run the compliance check to generate an explanation."
      />
    );
  }

  return (
    <Card>
      <CardContent className="pt-5">
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">{explanation}</p>
      </CardContent>
    </Card>
  );
}
