import { Scale } from "lucide-react";
import { formatPercent } from "@/lib/utils";
import type { Finding } from "@/types";

export function PolicyEvidence({ finding }: { finding: Finding }) {
  if (!finding.policy_clause_text) {
    return <p className="text-xs italic text-slate-400">No policy evidence cited.</p>;
  }

  const sourceParts = [
    finding.policy_document_name,
    finding.policy_section ? `§ ${finding.policy_section}` : null,
    finding.policy_page ? `p.${finding.policy_page}` : null,
  ].filter(Boolean);

  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
      <blockquote className="border-l-2 border-slate-300 pl-3 text-xs italic text-slate-700">
        "{finding.policy_clause_text}"
      </blockquote>
      <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[11px] text-slate-500">
        <Scale className="h-3 w-3" />
        {sourceParts.length > 0 ? sourceParts.join(" · ") : "Unknown source"}
        {finding.policy_similarity_score !== null && (
          <span className="ml-1 rounded-full bg-slate-200 px-1.5 py-0.5 text-slate-600">
            similarity {formatPercent(finding.policy_similarity_score)}
          </span>
        )}
      </div>
    </div>
  );
}
