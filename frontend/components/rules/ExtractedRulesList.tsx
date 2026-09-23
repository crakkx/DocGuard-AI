"use client";

import { useState } from "react";
import { RuleCard } from "@/components/rules/RuleCard";
import { RuleEditor } from "@/components/rules/RuleEditor";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { EmptyState } from "@/components/ui/empty-state";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/toast";
import { useConfirmRule, useRejectRule, useDeleteRule } from "@/hooks/useRules";
import { Check, Pencil, X, ClipboardList, ShieldOff, Trash2 } from "lucide-react";
import type { ComplianceRule } from "@/types";

const DEFAULT_REVIEWER = "REVIEWER";

function RejectDialog({
  rule,
  open,
  onOpenChange,
}: {
  rule: ComplianceRule;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [reason, setReason] = useState("");
  const { toast } = useToast();
  const rejectRule = useRejectRule();
  const deleteRule = useDeleteRule();

  function handleDisable() {
    rejectRule.mutate(
      { id: rule.id, reason: reason.trim() || "Rejected by reviewer" },
      {
        onSuccess: () => {
          toast({
            title: "Rule disabled",
            description: `"${rule.name}" moved to the Disabled tab.`,
            variant: "success",
          });
          setReason("");
          onOpenChange(false);
        },
        onError: (err) => {
          toast({
            title: "Failed to disable rule",
            description: err instanceof Error ? err.message : undefined,
            variant: "error",
          });
        },
      }
    );
  }

  function handleDiscard() {
    deleteRule.mutate(rule.id, {
      onSuccess: () => {
        toast({
          title: "Rule discarded",
          description: `"${rule.name}" was permanently deleted.`,
          variant: "success",
        });
        setReason("");
        onOpenChange(false);
      },
      onError: (err) => {
        toast({
          title: "Failed to discard rule",
          description: err instanceof Error ? err.message : undefined,
          variant: "error",
        });
      },
    });
  }

  const isPending = rejectRule.isPending || deleteRule.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent onClose={() => onOpenChange(false)}>
        <DialogHeader>
          <DialogTitle>Reject or discard rule</DialogTitle>
          <DialogDescription>
            Choose whether to disable &ldquo;{rule.name}&rdquo; (saving it in the Disabled tab where it can be re-enabled later) or permanently discard/delete it.
          </DialogDescription>
        </DialogHeader>
        <Textarea
          placeholder="Reason or notes (optional)"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={2}
        />
        <DialogFooter className="flex-col sm:flex-row gap-2 sm:justify-between">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>
            Cancel
          </Button>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              onClick={handleDisable}
              disabled={isPending}
            >
              {rejectRule.isPending ? <Spinner /> : <ShieldOff className="h-3.5 w-3.5 mr-1" />}
              Disable
            </Button>
            <Button
              variant="destructive"
              onClick={handleDiscard}
              disabled={isPending}
            >
              {deleteRule.isPending ? <Spinner /> : <Trash2 className="h-3.5 w-3.5 mr-1" />}
              Discard / Delete
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function PendingRuleCard({ rule }: { rule: ComplianceRule }) {
  const [editorOpen, setEditorOpen] = useState(false);
  const [rejectOpen, setRejectOpen] = useState(false);
  const { toast } = useToast();
  const confirmRule = useConfirmRule();

  function handleConfirm() {
    confirmRule.mutate(
      { id: rule.id, confirmedBy: DEFAULT_REVIEWER },
      {
        onSuccess: () => toast({ title: "Rule confirmed", variant: "success" }),
        onError: (err) =>
          toast({
            title: "Failed to confirm rule",
            description: err instanceof Error ? err.message : undefined,
            variant: "error",
          }),
      }
    );
  }

  return (
    <>
      <RuleCard
        rule={rule}
        actions={
          <>
            <Button size="sm" onClick={handleConfirm} disabled={confirmRule.isPending}>
              {confirmRule.isPending ? <Spinner /> : <Check className="h-3.5 w-3.5" />}
              Confirm
            </Button>
            <Button size="sm" variant="outline" onClick={() => setEditorOpen(true)}>
              <Pencil className="h-3.5 w-3.5" />
              Edit
            </Button>
            <Button size="sm" variant="destructive" onClick={() => setRejectOpen(true)}>
              <X className="h-3.5 w-3.5" />
              Reject
            </Button>
          </>
        }
      />
      <RuleEditor rule={rule} open={editorOpen} onOpenChange={setEditorOpen} />
      <RejectDialog rule={rule} open={rejectOpen} onOpenChange={setRejectOpen} />
    </>
  );
}

export function ExtractedRulesList({ rules }: { rules: ComplianceRule[] }) {
  if (rules.length === 0) {
    return <EmptyState icon={ClipboardList} title="No rules awaiting review." />;
  }

  return (
    <div className="flex flex-col gap-3">
      {rules.map((rule) => (
        <PendingRuleCard key={rule.id} rule={rule} />
      ))}
    </div>
  );
}
