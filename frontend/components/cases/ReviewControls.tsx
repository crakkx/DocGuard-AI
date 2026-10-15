"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { useCaseDecision } from "@/hooks/useCases";
import { useToast } from "@/components/ui/toast";
import { CheckCircle2, XCircle, PauseCircle } from "lucide-react";

export function ReviewControls({ caseId }: { caseId: string }) {
  const [reviewer, setReviewer] = useState("");
  const [comment, setComment] = useState("");
  const { mutate, isPending } = useCaseDecision(caseId);
  const { toast } = useToast();

  function decide(decision: "APPROVE" | "REJECT" | "HOLD") {
    if (!reviewer.trim()) {
      toast({ title: "Reviewer name required", variant: "error" });
      return;
    }
    mutate(
      { decision, reviewer: reviewer.trim(), comment: comment.trim() || undefined },
      {
        onSuccess: () => {
          toast({ title: `Case ${decision.toLowerCase()}d`, variant: "success" });
          setComment("");
        },
        onError: (err) => {
          toast({
            title: "Decision failed",
            description: err instanceof Error ? err.message : undefined,
            variant: "error",
          });
        },
      }
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Input
          placeholder="Reviewer name"
          value={reviewer}
          onChange={(e) => setReviewer(e.target.value)}
          disabled={isPending}
          className="h-10 text-sm bg-slate-50 border-slate-200"
        />
        <Input
          placeholder="Comment (optional)"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          disabled={isPending}
          className="h-10 text-sm bg-slate-50 border-slate-200"
        />
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant="default"
          size="sm"
          disabled={isPending}
          onClick={() => decide("APPROVE")}
        >
          {isPending ? <Spinner /> : <CheckCircle2 className="h-4 w-4" />}
          Approve
        </Button>
        <Button
          variant="destructive"
          size="sm"
          disabled={isPending}
          onClick={() => decide("REJECT")}
        >
          {isPending ? <Spinner /> : <XCircle className="h-4 w-4" />}
          Reject
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={isPending}
          onClick={() => decide("HOLD")}
        >
          {isPending ? <Spinner /> : <PauseCircle className="h-4 w-4" />}
          Hold
        </Button>
      </div>
    </div>
  );
}
