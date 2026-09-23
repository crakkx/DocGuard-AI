from dataclasses import dataclass, field
from typing import Optional
from app.engine.primitives import PrimitiveEvaluator, CaseData


@dataclass
class ExpressionResult:
    passed: bool
    explanation: str
    expected: Optional[str] = None
    actual: Optional[str] = None
    difference: Optional[str] = None
    children: list = field(default_factory=list)


class DSLInterpreter:
    """
    Evaluates Tier 2 expression trees.

    Expression format:
      {"AND": [expr, expr, ...]}
      {"OR":  [expr, expr, ...]}
      {"NOT": expr}
      {"primitive": "COMPARE_FIELDS", "parameters": {...}}
    """

    def __init__(self):
        self.primitive_evaluator = PrimitiveEvaluator()

    def evaluate(self, node: dict, case_data: CaseData) -> ExpressionResult:
        if not node:
            return ExpressionResult(True, "Empty expression — passing by default")

        if "AND" in node:
            children = [self.evaluate(child, case_data) for child in node["AND"]]
            passed = all(c.passed for c in children)
            explanations = "; ".join(c.explanation for c in children)
            return ExpressionResult(passed, f"AND({explanations})", children=children)

        if "OR" in node:
            children = [self.evaluate(child, case_data) for child in node["OR"]]
            passed = any(c.passed for c in children)
            explanations = "; ".join(c.explanation for c in children)
            return ExpressionResult(passed, f"OR({explanations})", children=children)

        if "NOT" in node:
            child = self.evaluate(node["NOT"], case_data)
            return ExpressionResult(
                not child.passed, f"NOT({child.explanation})", children=[child]
            )

        if "primitive" in node:
            prim = node["primitive"]
            params = node.get("parameters", {})
            res = self.primitive_evaluator.evaluate(prim, params, case_data)
            return ExpressionResult(
                passed=res.passed,
                explanation=res.explanation,
                expected=res.expected,
                actual=res.actual,
                difference=res.difference,
            )

        # Legacy format support: {"operator": "AND", "operands": [...]}
        operator = node.get("operator", "").upper()
        if operator == "AND":
            return self.evaluate({"AND": node.get("operands", [])}, case_data)
        if operator == "OR":
            return self.evaluate({"OR": node.get("operands", [])}, case_data)
        if operator == "NOT":
            return self.evaluate({"NOT": node.get("operand", {})}, case_data)

        return ExpressionResult(False, f"Unknown expression node: {list(node.keys())}")
