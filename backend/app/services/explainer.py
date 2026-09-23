from app.models.finding import ComplianceFinding
from app.models.procurement_case import ProcurementCase


FINDING_TYPE_LABELS = {
    "PRICE_MISMATCH": "Price Mismatch",
    "QUANTITY_MISMATCH": "Quantity Mismatch",
    "TOTAL_MISMATCH": "Total Amount Mismatch",
    "MISSING_GRN": "Missing Goods Receipt",
    "MISSING_INVOICE": "Missing Invoice / Bill",
    "MISSING_PO": "Missing Purchase Order",
    "MISSING_QUOTATION": "Missing Quotation Statement",
    "MISSING_TENDER_DOC": "Missing Tender Document",
    "VENDOR_MISMATCH": "Vendor Mismatch",
    "DUPLICATE_INVOICE": "Duplicate Invoice",
    "TAX_INCONSISTENCY": "Tax Inconsistency",
    "APPROVAL_THRESHOLD": "Approval Threshold Exceeded",
    "DIRECT_PURCHASE_THRESHOLD_EXCEEDED": "Direct Purchase Threshold Exceeded",
    "GEM_BIDDING_REQUIRED": "GeM Online Bidding Mandate",
    "LIMITED_TENDER_MANDATE": "Limited Tender Enquiry Mandate",
    "OPEN_TENDER_MANDATE": "Open Tender Enquiry Mandate",
    "ENVIRONMENTAL_COMPLIANCE": "Environmental Compliance Policy",
    "CUMULATIVE_SPEND": "Cumulative Spending Limit",
    "TIME_WINDOW_SPEND": "Time-Window Spending Limit",
}


class ExplainerService:
    """
    Generates evidence-based, template-driven explanations for procurement cases.
    Does NOT call any LLM — only describes findings already produced by the rule engine.
    """

    def generate_explanation(
        self,
        case: ProcurementCase,
        findings: list[ComplianceFinding],
    ) -> str:
        violations = [f for f in findings if f.status == "VIOLATION"]
        needs_review = [f for f in findings if f.status == "NEEDS_REVIEW"]

        if not findings:
            return (
                f"Procurement case {case.case_number} has been evaluated against all "
                f"active compliance rules. No violations were detected. "
                f"Risk level: LOW."
            )

        parts: list[str] = []
        parts.append(
            f"Procurement case {case.case_number} "
            f"(Vendor: {case.vendor_name or 'Unknown'}, "
            f"PO: {case.po_number or 'N/A'}) "
            f"has been evaluated and the following compliance issues were identified:"
        )

        for f in violations + needs_review:
            label = FINDING_TYPE_LABELS.get(f.finding_type, f.finding_type)
            line = f"\n\n• [{f.severity}] {label}: "

            if f.expected_value and f.actual_value:
                line += f"Expected {f.expected_value}, found {f.actual_value}."
            if f.difference:
                line += f" Difference: {f.difference}."
            if f.explanation:
                line += f" {f.explanation}"

            # Policy evidence
            if f.policy_clause_text and f.policy_document_name:
                section = f"Section {f.policy_section}" if f.policy_section else "policy"
                line += (
                    f" Relevant policy ({f.policy_document_name}, {section}): "
                    f'"{f.policy_clause_text[:200]}..."'
                )

            parts.append(line)

        # Summary
        v_count = len(violations)
        r_count = len(needs_review)
        summary_parts = []
        if v_count:
            summary_parts.append(f"{v_count} violation(s)")
        if r_count:
            summary_parts.append(f"{r_count} item(s) needing review")

        parts.append(
            f"\n\nThis case has been assigned risk level "
            f"{'UNKNOWN' if not case.risk_level else case.risk_level} "
            f"based on {', '.join(summary_parts) if summary_parts else 'findings above'}. "
            f"Human reviewer action is required."
        )

        return "".join(parts)


explainer = ExplainerService()
