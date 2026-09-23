from uuid import UUID
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.procurement_case import ProcurementCase
from app.models.compliance_rule import ComplianceRule
from app.models.finding import ComplianceFinding
from app.models.document import Document, ExtractedData
from app.engine.evaluator import RuleEvaluator
from app.engine.primitives import CaseData
from app.services.policy_rag import policy_rag
from app.services.risk_scorer import risk_scorer
from app.services.explainer import explainer
from app.services.audit_service import audit_service

FINDING_TYPE_MAP = {
    "COMPARE_FIELDS": {
        "unit_price": "PRICE_MISMATCH",
        "total_amount": "TOTAL_MISMATCH",
        "quantity": "QUANTITY_MISMATCH",
        "tax": "TAX_INCONSISTENCY",
        "vendor_name": "VENDOR_MISMATCH",
    },
    "PRESENCE_CHECK": "MISSING_GRN",
    "MATCH_CHECK": "VENDOR_MISMATCH",
    "AGGREGATION_CHECK": "CUMULATIVE_SPEND",
    "TIME_WINDOW_CHECK": "TIME_WINDOW_SPEND",
    "THRESHOLD_CHECK": "APPROVAL_THRESHOLD",
}

POLICY_QUERIES = {
    "PRICE_MISMATCH": "invoice price variance tolerance maximum deviation",
    "QUANTITY_MISMATCH": "invoice quantity exceeds purchase order goods receipt",
    "TOTAL_MISMATCH": "invoice total amount reconciliation purchase order",
    "MISSING_GRN": "goods receipt note required before payment invoice",
    "VENDOR_MISMATCH": "vendor name verification invoice purchase order match",
    "DUPLICATE_INVOICE": "duplicate invoice payment prevention detection",
    "TAX_INCONSISTENCY": "tax calculation compliance gst verification",
    "APPROVAL_THRESHOLD": "approval authority spending limit threshold",
    "CUMULATIVE_SPEND": "cumulative project spending cap budget limit",
    "TIME_WINDOW_SPEND": "time bound vendor spending control threshold",
}


class ComplianceEngine:
    def __init__(self):
        self.evaluator = RuleEvaluator()

    async def run_compliance_check(
        self,
        case_id: UUID,
        model,          # sentence-transformers model from app.state
        db: AsyncSession,
    ) -> list[ComplianceFinding]:
        # Load case
        stmt = select(ProcurementCase).where(ProcurementCase.id == case_id)
        result = await db.execute(stmt)
        case = result.scalar_one_or_none()
        if not case:
            raise ValueError(f"Case {case_id} not found")

        await audit_service.log(
            db, "COMPLIANCE_CHECK_RUN", f"Running compliance check on {case.case_number}",
            case_id=case_id,
        )

        # Build extracted data dicts
        po_dict = await self._get_doc_data(case.po_document_id, db)
        inv_dict = await self._get_doc_data(case.invoice_document_id, db)
        grn_dict = await self._get_doc_data(case.grn_document_id, db)

        # All cases for cross-transaction rules
        all_cases_result = await db.execute(select(ProcurementCase))
        all_cases = [
            {
                "id": str(c.id),
                "case_number": c.case_number,
                "vendor_name": c.vendor_name,
                "po_number": c.po_number,
                "invoice_number": c.invoice_number,
                "total_amount": str(c.total_amount) if c.total_amount else None,
                "project_code": c.project_code,
                "created_at": c.created_at,
                "po_document_id": str(c.po_document_id) if c.po_document_id else None,
                "invoice_document_id": str(c.invoice_document_id) if c.invoice_document_id else None,
                "grn_document_id": str(c.grn_document_id) if c.grn_document_id else None,
            }
            for c in all_cases_result.scalars().all()
        ]

        case_dict = {
            "id": str(case.id),
            "case_number": case.case_number,
            "vendor_name": case.vendor_name,
            "po_number": case.po_number,
            "invoice_number": case.invoice_number,
            "total_amount": str(case.total_amount) if case.total_amount else None,
            "project_code": case.project_code,
            "created_at": case.created_at,
            "po_document_id": str(case.po_document_id) if case.po_document_id else None,
            "invoice_document_id": str(case.invoice_document_id) if case.invoice_document_id else None,
            "grn_document_id": str(case.grn_document_id) if case.grn_document_id else None,
        }

        case_data = CaseData(
            case=case_dict,
            po=po_dict,
            invoice=inv_dict,
            grn=grn_dict,
            all_cases=all_cases,
        )

        # Load confirmed + enabled rules
        rules_stmt = select(ComplianceRule).where(
            ComplianceRule.status == "CONFIRMED",
            ComplianceRule.enabled == True,  # noqa: E712
        )
        rules_result = await db.execute(rules_stmt)
        rules = list(rules_result.scalars().all())

        # Delete existing findings for this case before re-running
        existing = await db.execute(
            select(ComplianceFinding).where(ComplianceFinding.case_id == case_id)
        )
        existing_findings = existing.scalars().all()
        if existing_findings:
            from app.models.audit import AuditEntry
            from sqlalchemy import update
            existing_ids = [f.id for f in existing_findings]
            await db.execute(
                update(AuditEntry)
                .where(AuditEntry.finding_id.in_(existing_ids))
                .values(finding_id=None)
            )
            for f in existing_findings:
                await db.delete(f)
            await db.flush()

        new_findings: list[ComplianceFinding] = []

        for rule in rules:
            try:
                eval_result = await self.evaluator.evaluate_rule(rule, case_data)
            except Exception as exc:
                continue

            if eval_result.status == "PASS":
                continue

            # Determine finding type
            finding_type = self._get_finding_type(rule)

            # Retrieve policy evidence via RAG using the rule's exact title and source clause
            query_parts = [rule.name]
            if rule.source_clause:
                query_parts.append(rule.source_clause)
            elif rule.description:
                query_parts.append(rule.description)
            policy_query = " ".join(query_parts)

            policy_clauses = await policy_rag.retrieve_relevant_clauses(
                policy_query, model, db, top_k=1, similarity_threshold=0.3
            )
            top_clause = policy_clauses[0] if policy_clauses else None

            finding = ComplianceFinding(
                case_id=case_id,
                rule_id=rule.id,
                finding_type=finding_type,
                status=eval_result.status,
                severity=rule.severity,
                tier=str(rule.tier),
                rule_name=rule.name,
                expected_value=str(eval_result.expected_value) if eval_result.expected_value else None,
                actual_value=str(eval_result.actual_value) if eval_result.actual_value else None,
                difference=str(eval_result.difference) if eval_result.difference else None,
                explanation=eval_result.explanation,
                policy_clause_text=top_clause.content[:500] if top_clause else None,
                policy_document_name=top_clause.policy_title if top_clause else None,
                policy_section=top_clause.section_number if top_clause else None,
                policy_page=top_clause.page_number if top_clause else None,
                policy_similarity_score=top_clause.similarity_score if top_clause else None,
                llm_prompt=getattr(eval_result, "llm_prompt", None),
                llm_response=getattr(eval_result, "llm_response", None),
                llm_confidence=getattr(eval_result, "llm_confidence", None),
                finding_review_status="OPEN",
            )
            db.add(finding)
            await db.flush()
            new_findings.append(finding)

            await audit_service.log(
                db, "FINDING_CREATED",
                f"Finding: {finding_type} ({eval_result.status})",
                case_id=case_id,
                finding_id=finding.id,
                rule_id=rule.id,
            )

        # Risk scoring
        risk_level, risk_score_val = risk_scorer.calculate_risk(
            new_findings,
            float(case.total_amount) if case.total_amount else None,
        )
        case.risk_level = risk_level
        case.risk_score = risk_score_val

        # Generate explanation
        case.explanation = explainer.generate_explanation(case, new_findings)

        # Update case status
        if any(f.status == "VIOLATION" for f in new_findings):
            case.status = "UNDER_REVIEW"
        elif new_findings:
            case.status = "UNDER_REVIEW"
        else:
            case.status = "PENDING"

        await audit_service.log(
            db, "RISK_CALCULATED",
            f"Risk level: {risk_level}, score: {risk_score_val}",
            case_id=case_id,
            metadata={"risk_level": risk_level, "risk_score": risk_score_val},
        )

        await db.flush()
        return new_findings

    def _get_finding_type(self, rule: ComplianceRule) -> str:
        """Derive finding type from rule configuration."""
        name_lower = rule.name.lower()

        if "direct purchase" in name_lower and "voucher" not in name_lower and "bill" not in name_lower:
            return "DIRECT_PURCHASE_THRESHOLD_EXCEEDED"
        if "gem" in name_lower and ("bidding" in name_lower or "bid" in name_lower):
            return "GEM_BIDDING_REQUIRED"
        if "limited tender" in name_lower:
            return "LIMITED_TENDER_MANDATE"
        if "open tender" in name_lower:
            return "OPEN_TENDER_MANDATE"
        if "plastic" in name_lower:
            return "ENVIRONMENTAL_COMPLIANCE"

        if rule.primitive:
            params = rule.parameters or {}
            if rule.primitive == "COMPARE_FIELDS":
                field_a = str(params.get("field_a", {}).get("field", "") if isinstance(params.get("field_a"), dict) else params.get("field_a", ""))
                if "unit_price" in field_a:
                    return "PRICE_MISMATCH"
                elif "quantity" in field_a:
                    return "QUANTITY_MISMATCH"
                elif "total_amount" in field_a:
                    return "TOTAL_MISMATCH"
                elif "tax" in field_a:
                    return "TAX_INCONSISTENCY"
                elif "vendor" in field_a:
                    return "VENDOR_MISMATCH"
            elif rule.primitive == "PRESENCE_CHECK":
                doc = str(params.get("document_type") or params.get("document") or "").lower()
                if "invoice" in doc or "bill" in doc or "voucher" in doc:
                    return "MISSING_INVOICE"
                if "po" in doc or "purchase_order" in doc:
                    return "MISSING_PO"
                if "tender" in doc:
                    return "MISSING_TENDER_DOC"
                if "quotation" in doc:
                    return "MISSING_QUOTATION"
                return "MISSING_GRN"
            elif rule.primitive == "MATCH_CHECK":
                field = str(params.get("field", {}).get("field", "") if isinstance(params.get("field"), dict) else params.get("field", ""))
                if "invoice" in field:
                    return "DUPLICATE_INVOICE"
                return "VENDOR_MISMATCH"
            elif rule.primitive == "THRESHOLD_CHECK":
                return "APPROVAL_THRESHOLD"
            elif rule.primitive == "AGGREGATION_CHECK":
                return "CUMULATIVE_SPEND"
            elif rule.primitive == "TIME_WINDOW_CHECK":
                return "TIME_WINDOW_SPEND"

        # Fallback: use rule name
        return rule.name.upper().replace(" ", "_")

    async def _get_doc_data(
        self, doc_id: Optional[UUID], db: AsyncSession
    ) -> dict:
        if not doc_id:
            return {}
        stmt = select(ExtractedData).where(ExtractedData.document_id == doc_id)
        result = await db.execute(stmt)
        return {row.field_name: row.field_value for row in result.scalars().all()}


compliance_engine = ComplianceEngine()
