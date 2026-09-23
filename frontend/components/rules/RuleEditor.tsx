"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useToast } from "@/components/ui/toast";
import { useUpdateRule } from "@/hooks/useRules";
import { tierLabel } from "@/lib/utils";
import { SEVERITIES } from "@/lib/constants";
import type { ComplianceRule } from "@/types";

function jsonField(value: Record<string, unknown> | null | undefined): string {
  if (!value) return "";
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return "";
  }
}

export function RuleEditor({
  rule,
  open,
  onOpenChange,
}: {
  rule: ComplianceRule;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const tier = tierLabel(rule.tier);
  const { toast } = useToast();
  const updateRule = useUpdateRule();

  const [name, setName] = useState(rule.name);
  const [description, setDescription] = useState(rule.description ?? "");
  const [severity, setSeverity] = useState(rule.severity);
  const [onViolation, setOnViolation] = useState(rule.on_violation ?? "");
  const [logicText, setLogicText] = useState(
    tier === "EXPRESSION" ? jsonField(rule.expression) : jsonField(rule.parameters)
  );
  const [evaluationPrompt, setEvaluationPrompt] = useState(rule.evaluation_prompt ?? "");
  const [jsonError, setJsonError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setName(rule.name);
    setDescription(rule.description ?? "");
    setSeverity(rule.severity);
    setOnViolation(rule.on_violation ?? "");
    setLogicText(tier === "EXPRESSION" ? jsonField(rule.expression) : jsonField(rule.parameters));
    setEvaluationPrompt(rule.evaluation_prompt ?? "");
    setJsonError(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, rule.id]);

  const isJsonTier = tier === "PRIMITIVE" || tier === "EXPRESSION";

  const parsedLogic = useMemo(() => {
    if (!isJsonTier) return { ok: true as const, value: undefined };
    const trimmed = logicText.trim();
    if (!trimmed) return { ok: true as const, value: undefined };
    try {
      return { ok: true as const, value: JSON.parse(trimmed) };
    } catch (e) {
      return { ok: false as const, error: e instanceof Error ? e.message : "Invalid JSON" };
    }
  }, [logicText, isJsonTier]);

  const canSave = name.trim().length > 0 && parsedLogic.ok && !updateRule.isPending;

  function handleLogicChange(value: string) {
    setLogicText(value);
    if (!isJsonTier) return;
    const trimmed = value.trim();
    if (!trimmed) {
      setJsonError(null);
      return;
    }
    try {
      JSON.parse(trimmed);
      setJsonError(null);
    } catch (e) {
      setJsonError(e instanceof Error ? e.message : "Invalid JSON");
    }
  }

  function handleSave() {
    if (!parsedLogic.ok) return;

    const data: Partial<ComplianceRule> = {
      name: name.trim(),
      description: description.trim() || null,
      severity,
      on_violation: onViolation,
    };

    if (tier === "PRIMITIVE") {
      data.parameters = (parsedLogic.value as Record<string, unknown> | undefined) ?? null;
    } else if (tier === "EXPRESSION") {
      data.expression = (parsedLogic.value as Record<string, unknown> | undefined) ?? null;
    } else {
      data.evaluation_prompt = evaluationPrompt;
    }

    updateRule.mutate(
      { id: rule.id, data },
      {
        onSuccess: () => {
          toast({ title: "Rule updated", variant: "success" });
          onOpenChange(false);
        },
        onError: (err) => {
          toast({
            title: "Failed to update rule",
            description: err instanceof Error ? err.message : undefined,
            variant: "error",
          });
        },
      }
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl" onClose={() => onOpenChange(false)}>
        <DialogHeader>
          <DialogTitle>Edit rule</DialogTitle>
          <DialogDescription>Update the rule definition. Changes save immediately.</DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-slate-700">Name</label>
            <Input value={name} onChange={(e) => setName(e.target.value)} />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-slate-700">Description</label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-slate-700">Severity</label>
              <Select value={severity} onChange={(e) => setSeverity(e.target.value)}>
                {SEVERITIES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </Select>
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-slate-700">On violation</label>
              <Input value={onViolation} onChange={(e) => setOnViolation(e.target.value)} />
            </div>
          </div>

          {isJsonTier ? (
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-slate-700">
                {tier === "PRIMITIVE" ? "Parameters (JSON)" : "Expression (JSON)"}
              </label>
              <Textarea
                value={logicText}
                onChange={(e) => handleLogicChange(e.target.value)}
                rows={8}
                className="font-mono text-xs"
              />
              {jsonError && <p className="text-xs text-red-600">Invalid JSON: {jsonError}</p>}
            </div>
          ) : (
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-slate-700">Evaluation prompt</label>
              <Textarea
                value={evaluationPrompt}
                onChange={(e) => setEvaluationPrompt(e.target.value)}
                rows={6}
              />
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={!canSave}>
            {updateRule.isPending ? (
              <>
                <Spinner /> Saving…
              </>
            ) : (
              "Save changes"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
