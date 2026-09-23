from app.engine.primitives import PrimitiveEvaluator, CaseData
from app.engine.dsl_interpreter import DSLInterpreter
from app.engine.llm_evaluator import LLMEvaluator
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RuleEvaluationResult:
    status: str  # PASS, VIOLATION, NEEDS_REVIEW
    expected_value: Optional[str]
    actual_value: Optional[str]
    difference: Optional[str]
    explanation: str
    llm_prompt: Optional[str] = None
    llm_response: Optional[str] = None
    llm_confidence: Optional[float] = None


class RuleEvaluator:
    def __init__(self):
        self.primitive_evaluator = PrimitiveEvaluator()
        self.dsl_interpreter = DSLInterpreter()
        self.llm_evaluator = LLMEvaluator()

    async def evaluate_rule(self, rule, case_data: CaseData) -> RuleEvaluationResult:
        """Dispatch to the correct tier evaluator. Returns RuleEvaluationResult."""
        tier = str(rule.tier).upper()  # normalise int or string tier
        if tier in ("1", "PRIMITIVE"):
            return self._eval_primitive(rule, case_data)
        elif tier in ("2", "EXPRESSION"):
            return self._eval_expression(rule, case_data)
        elif tier in ("3", "LLM_EVALUATED"):
            return await self._eval_llm(rule, case_data)
        else:
            # Unknown tier — flag for review
            return RuleEvaluationResult(
                status="NEEDS_REVIEW",
                expected_value=None,
                actual_value=None,
                difference=None,
                explanation=f"Unknown rule tier: {rule.tier}",
            )

    def _eval_primitive(self, rule, case_data: CaseData) -> RuleEvaluationResult:
        res = self.primitive_evaluator.evaluate(
            rule.primitive, rule.parameters or {}, case_data
        )
        on_violation = getattr(rule, "on_violation", "VIOLATION")
        if res.passed:
            status = "PASS"
        elif on_violation in ("NEEDS_REVIEW", "FLAG"):
            status = "NEEDS_REVIEW"
        else:
            status = "VIOLATION"
        return RuleEvaluationResult(
            status=status,
            expected_value=res.expected,
            actual_value=res.actual,
            difference=res.difference,
            explanation=res.explanation,
        )

    def _eval_expression(self, rule, case_data: CaseData) -> RuleEvaluationResult:
        res = self.dsl_interpreter.evaluate(rule.expression or {}, case_data)
        on_violation = getattr(rule, "on_violation", "VIOLATION")
        if res.passed:
            status = "PASS"
        elif on_violation in ("NEEDS_REVIEW", "FLAG"):
            status = "NEEDS_REVIEW"
        else:
            status = "VIOLATION"
        return RuleEvaluationResult(
            status=status,
            expected_value=getattr(res, "expected", None),
            actual_value=getattr(res, "actual", None),
            difference=getattr(res, "difference", None),
            explanation=res.explanation,
        )

    async def _eval_llm(self, rule, case_data: CaseData) -> RuleEvaluationResult:
        # Scope guard for Open Tender rules on sub-threshold cases
        rule_text = f"{rule.name} {rule.evaluation_prompt or ''}".lower()
        tot_val = case_data.get_field("total_amount") or case_data.get_field("procurement_value")
        dec_amt = self.primitive_evaluator._to_decimal(tot_val)
        case_method = (case_data.get_field("procurement_method") or "").lower()

        if "open tender" in rule_text and dec_amt is not None and dec_amt <= 2500000 and "open" not in case_method:
            return RuleEvaluationResult(
                status="PASS",
                expected_value="N/A",
                actual_value="N/A",
                difference=None,
                explanation="Not applicable: procurement value does not exceed Open Tender threshold (₹25,00,000) and method is not Open Tender.",
            )

        case_summary = {
            "vendor_name": case_data.case.get("vendor_name"),
            "po_number": case_data.case.get("po_number"),
            "invoice_number": case_data.case.get("invoice_number"),
            "total_amount": case_data.case.get("total_amount"),
            "procurement_method": case_data.get_field("procurement_method"),
            "po_fields": case_data.po,
            "invoice_fields": case_data.invoice,
            "grn_fields": case_data.grn,
        }
        policy_clause = rule.source_clause or "Refer to company procurement policy."
        res = await self.llm_evaluator.evaluate(
            rule.evaluation_prompt or "", case_summary, policy_clause
        )
        return RuleEvaluationResult(
            status=res.get("status", "NEEDS_REVIEW"),
            expected_value=res.get("expected_value"),
            actual_value=res.get("actual_value"),
            difference=None,
            explanation=res.get("explanation", "AI assessment"),
            llm_prompt=res.get("prompt_used"),
            llm_response=res.get("response_received"),
            llm_confidence=res.get("confidence"),
        )
