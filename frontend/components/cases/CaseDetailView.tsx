"use client";

import { useCase } from "@/hooks/useCases";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { CaseHeader } from "@/components/cases/CaseHeader";
import { ReviewControls } from "@/components/cases/ReviewControls";
import { DocumentComparison } from "@/components/cases/DocumentComparison";
import { ExtractedDataPanel } from "@/components/cases/ExtractedDataPanel";
import { ComplianceFindings } from "@/components/cases/ComplianceFindings";
import { ExplanationPanel } from "@/components/cases/ExplanationPanel";
import { AuditTimeline } from "@/components/cases/AuditTimeline";
import { PolicyEvidence } from "@/components/cases/PolicyEvidence";
import { FileX2, Scale } from "lucide-react";

export function CaseDetailView({ caseId }: { caseId: string }) {
  const { data: caseDetail, isLoading, isError, error } = useCase(caseId);

  if (isLoading) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-9 w-80" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (isError || !caseDetail) {
    return (
      <EmptyState
        icon={FileX2}
        title="Case not found"
        description={
          error instanceof Error
            ? error.message
            : "This case could not be loaded. It may not exist, or the backend is unreachable."
        }
      />
    );
  }

  const findingsWithEvidence = caseDetail.findings.filter((f) => f.policy_clause_text);

  return (
    <div className="flex flex-col gap-4">
      <CaseHeader caseDetail={caseDetail} />

      <Card>
        <CardHeader>
          <CardTitle>Case Decision</CardTitle>
        </CardHeader>
        <CardContent>
          <ReviewControls caseId={caseDetail.id} />
        </CardContent>
      </Card>

      <Tabs defaultValue="documents">
        <TabsList className="flex-wrap">
          <TabsTrigger value="documents">Documents</TabsTrigger>
          <TabsTrigger value="comparison">Comparison</TabsTrigger>
          <TabsTrigger value="findings" badge={<Badge variant="secondary">{caseDetail.findings.length}</Badge>}>
            Findings
          </TabsTrigger>
          <TabsTrigger value="policy">Policy Evidence</TabsTrigger>
          <TabsTrigger value="explanation">Explanation</TabsTrigger>
          <TabsTrigger value="audit">Audit</TabsTrigger>
        </TabsList>

        <TabsContent value="documents" className="mt-4">
          <DocumentComparison caseDetail={caseDetail} />
        </TabsContent>

        <TabsContent value="comparison" className="mt-4">
          <ExtractedDataPanel caseDetail={caseDetail} />
        </TabsContent>

        <TabsContent value="findings" className="mt-4">
          <ComplianceFindings caseId={caseDetail.id} findings={caseDetail.findings} />
        </TabsContent>

        <TabsContent value="policy" className="mt-4">
          {findingsWithEvidence.length === 0 ? (
            <EmptyState
              icon={Scale}
              title="No policy evidence yet"
              description="Findings with a cited policy clause will appear here once the compliance check has run."
            />
          ) : (
            <div className="flex flex-col gap-4">
              {findingsWithEvidence.map((finding) => (
                <Card key={finding.id}>
                  <CardHeader>
                    <CardTitle>{finding.rule_name || finding.finding_type}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <PolicyEvidence finding={finding} />
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="explanation" className="mt-4">
          <ExplanationPanel explanation={caseDetail.explanation} />
        </TabsContent>

        <TabsContent value="audit" className="mt-4">
          <Card>
            <CardContent className="pt-5">
              <AuditTimeline entries={caseDetail.audit_entries} />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
