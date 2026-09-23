"use client";

import { useState } from "react";
import { RuleCard } from "@/components/rules/RuleCard";
import { RuleEditor } from "@/components/rules/RuleEditor";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { EmptyState } from "@/components/ui/empty-state";
import { useToast } from "@/components/ui/toast";
import { useDisableRule, useEnableRule, useDeleteRule } from "@/hooks/useRules";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Pencil, ShieldCheck, ShieldOff, Trash2 } from "lucide-react";
import type { ComplianceRule } from "@/types";
import type { LucideIcon } from "lucide-react";

function RuleRow({ rule }: { rule: ComplianceRule }) {
  const [editorOpen, setEditorOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const { toast } = useToast();
  const disableRule = useDisableRule();
  const enableRule = useEnableRule();
  const deleteRule = useDeleteRule();

  const isConfirmed = rule.status === "CONFIRMED";
  const isDisabled = rule.status === "DISABLED" || rule.status === "REJECTED";
  const canToggle = isConfirmed || isDisabled;

  function handleToggle() {
    const mutation = isConfirmed ? disableRule : enableRule;
    mutation.mutate(rule.id, {
      onSuccess: () =>
        toast({ title: isConfirmed ? "Rule disabled" : "Rule enabled", variant: "success" }),
      onError: (err) =>
        toast({
          title: "Failed to update rule status",
          description: err instanceof Error ? err.message : undefined,
          variant: "error",
        }),
    });
  }

  function handleDelete() {
    deleteRule.mutate(rule.id, {
      onSuccess: () => {
        toast({
          title: "Rule deleted",
          description: `"${rule.name}" was permanently deleted.`,
          variant: "success",
        });
        setDeleteOpen(false);
      },
      onError: (err) => {
        toast({
          title: "Failed to delete rule",
          description: err instanceof Error ? err.message : undefined,
          variant: "error",
        });
      },
    });
  }

  const isPending = disableRule.isPending || enableRule.isPending || deleteRule.isPending;

  return (
    <>
      <RuleCard
        rule={rule}
        actions={
          <>
            {canToggle && (
              <Button
                size="sm"
                variant={isConfirmed ? "outline" : "default"}
                onClick={handleToggle}
                disabled={isPending}
              >
                {disableRule.isPending || enableRule.isPending ? (
                  <Spinner />
                ) : isConfirmed ? (
                  <ShieldOff className="h-3.5 w-3.5" />
                ) : (
                  <ShieldCheck className="h-3.5 w-3.5" />
                )}
                {isConfirmed ? "Disable" : "Enable"}
              </Button>
            )}
            <Button size="sm" variant="outline" onClick={() => setEditorOpen(true)}>
              <Pencil className="h-3.5 w-3.5" />
              Edit
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="text-slate-400 hover:text-red-600 hover:bg-red-50"
              title="Delete rule"
              onClick={() => setDeleteOpen(true)}
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </>
        }
      />
      <RuleEditor rule={rule} open={editorOpen} onOpenChange={setEditorOpen} />
      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent onClose={() => setDeleteOpen(false)}>
          <DialogHeader>
            <DialogTitle>Delete rule</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete &ldquo;{rule.name}&rdquo;? This will permanently remove this rule from the system.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteOpen(false)} disabled={deleteRule.isPending}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDelete} disabled={deleteRule.isPending}>
              {deleteRule.isPending ? "Deleting…" : "Delete rule"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

export function ConfirmedRules({
  rules,
  emptyTitle,
  emptyDescription,
  emptyIcon,
}: {
  rules: ComplianceRule[];
  emptyTitle: string;
  emptyDescription?: string;
  emptyIcon?: LucideIcon;
}) {
  if (rules.length === 0) {
    return <EmptyState icon={emptyIcon} title={emptyTitle} description={emptyDescription} />;
  }

  return (
    <div className="flex flex-col gap-3">
      {rules.map((rule) => (
        <RuleRow key={rule.id} rule={rule} />
      ))}
    </div>
  );
}
