"""
Master demo-data seeder.

Creates a realistic 10-section procurement policy (ingested through the real
RAG pipeline: chunk -> embed -> store), 10 confirmed+enabled compliance rules
spanning all three tiers (8 Tier-1 primitives, 1 Tier-2 expression, 1 Tier-3
LLM-evaluated), and 8 demo procurement cases (each with linked PO/Invoice/GRN
documents and extracted fields) engineered to exercise those rules. Finally
runs the real compliance engine against every seeded case so findings, risk
scores, and explanations are generated exactly the way they would be for a
real upload — this file does not hand-write findings.

Run with: python -m app.seed.seeder  (or `make seed`)
"""
import asyncio
import logging

from app.database import init_db, AsyncSessionLocal
from app.models.policy import PolicyDocument, PolicyChunk
from app.models.compliance_rule import ComplianceRule
from app.models.procurement_case import ProcurementCase
from app.models.document import Document, ExtractedData
from app.seed.demo_policy import DEMO_POLICY_TEXT
from app.seed.demo_transactions import DEMO_CASES
from app.services.policy_rag import policy_rag
from app.services.compliance_engine import compliance_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed")


# Each rule's source_section is used to look up the matching policy chunk
# (by section_number) so source_clause/source_page get populated from the
# real ingested text, exactly like a human-confirmed extracted rule would.
DEMO_RULES = [
    {
        "name": "Price Variance Tolerance",
        "description": "Invoice unit price must not deviate from the PO unit price by more than 5%.",
        "tier": 1,
        "primitive": "COMPARE_FIELDS",
        "parameters": {
            "field_a": {"document": "invoice", "field": "unit_price"},
            "field_b": {"document": "purchase_order", "field": "unit_price"},
            "operator": "DEVIATION_PERCENT",
            "threshold": 5,
            "direction": "ANY",
        },
        "severity": "HIGH",
        "on_violation": "VIOLATION",
        "source_section": "3.1",
    },
    {
        "name": "Invoice Quantity Reconciliation",
        "description": "Invoice quantity must not exceed the purchase order quantity.",
        "tier": 1,
        "primitive": "COMPARE_FIELDS",
        "parameters": {
            "field_a": {"document": "invoice", "field": "quantity"},
            "field_b": {"document": "purchase_order", "field": "quantity"},
            "operator": "<=",
        },
        "severity": "HIGH",
        "on_violation": "VIOLATION",
        "source_section": "3.2",
    },
    {
        "name": "VP Approval Threshold",
        "description": "Purchases above ₹10,00,000 require VP-level approval.",
        "tier": 1,
        "primitive": "THRESHOLD_CHECK",
        "parameters": {
            "field": {"document": "case", "field": "total_amount"},
            "operator": "<=",
            "threshold": 1000000,
        },
        "severity": "CRITICAL",
        "on_violation": "NEEDS_REVIEW",
        "source_section": "4.1",
    },
    {
        "name": "Goods Receipt Required",
        "description": "Payment requires a linked goods receipt confirmation.",
        "tier": 1,
        "primitive": "PRESENCE_CHECK",
        "parameters": {
            "target_type": "DOCUMENT",
            "document_type": "goods_receipt",
            "condition": "EXISTS",
        },
        "severity": "HIGH",
        "on_violation": "VIOLATION",
        "source_section": "4.2",
    },
    {
        "name": "Vendor Identity Match",
        "description": "Invoice vendor name must match the purchase order vendor name exactly.",
        "tier": 1,
        "primitive": "COMPARE_FIELDS",
        "parameters": {
            "field_a": {"document": "invoice", "field": "vendor_name"},
            "field_b": {"document": "purchase_order", "field": "vendor_name"},
            "operator": "==",
        },
        "severity": "CRITICAL",
        "on_violation": "VIOLATION",
        "source_section": "5.1",
    },
    {
        "name": "Duplicate Invoice Detection",
        "description": "Duplicate invoice numbers from the same vendor must be flagged.",
        "tier": 1,
        "primitive": "MATCH_CHECK",
        "parameters": {
            "field": {"document": "invoice", "field": "invoice_number"},
            "across": "cases",
        },
        "severity": "CRITICAL",
        "on_violation": "VIOLATION",
        "source_section": "5.2",
    },
    {
        "name": "Cumulative Project Spend Cap",
        "description": "Cumulative spend against a single project code must not exceed ₹25,00,000.",
        "tier": 1,
        "primitive": "AGGREGATION_CHECK",
        "parameters": {
            "group_by": "project_code",
            "aggregate_field": "total_amount",
            "function": "SUM",
            "operator": "<=",
            "threshold": 2500000,
        },
        "severity": "HIGH",
        "on_violation": "NEEDS_REVIEW",
        "source_section": "6.1",
    },
    {
        "name": "Vendor Spending Velocity",
        "description": "Cumulative vendor spend exceeding ₹5,00,000 within 30 days requires review.",
        "tier": 1,
        "primitive": "TIME_WINDOW_CHECK",
        "parameters": {
            "group_by": "vendor_name",
            "aggregate_field": "total_amount",
            "function": "SUM",
            "window_days": 30,
            "operator": "<=",
            "threshold": 500000,
        },
        "severity": "MEDIUM",
        "on_violation": "NEEDS_REVIEW",
        "source_section": "6.2",
    },
    {
        "name": "Anti-Splitting Rule",
        "description": (
            "Split orders to the same vendor within 7 days are prohibited if their "
            "combined value exceeds ₹2,00,000."
        ),
        "tier": 2,
        "expression": {
            "AND": [
                {
                    "primitive": "AGGREGATION_CHECK",
                    "parameters": {
                        "group_by": "vendor_name",
                        "aggregate_field": "total_amount",
                        "function": "SUM",
                        "window_days": 7,
                        "operator": "<=",
                        "threshold": 200000,
                    },
                }
            ]
        },
        "severity": "CRITICAL",
        "on_violation": "VIOLATION",
        "source_section": "8.3",
    },
    {
        "name": "Vendor Performance Review",
        "description": (
            "Vendor performance ratings below 'Satisfactory' for two consecutive "
            "quarters shall trigger a mandatory review."
        ),
        "tier": 3,
        "evaluation_prompt": (
            "Based on the policy clause, determine if this procurement case is "
            "compliant with vendor performance review requirements. Respond with "
            "PASS, VIOLATION, or NEEDS_REVIEW and explain why."
        ),
        "severity": "MEDIUM",
        "on_violation": "NEEDS_REVIEW",
        "source_section": "9.2",
    },
]


async def _create_document(session, doc_type: str, fields: dict, vendor_name: str) -> Document:
    doc = Document(
        filename=f"seed-{doc_type.lower()}-{fields.get('po_number') or fields.get('invoice_number')}.pdf",
        original_filename=f"{doc_type}.pdf",
        filepath="seed://in-memory",
        document_type=doc_type,
        type_confidence=0.99,
        status="EXTRACTED",
    )
    session.add(doc)
    await session.flush()

    for field_name, field_value in fields.items():
        field_type = (
            "amount"
            if field_name in ("total_amount", "unit_price", "subtotal", "tax")
            else "text"
        )
        session.add(
            ExtractedData(
                document_id=doc.id,
                field_name=field_name,
                field_value=str(field_value),
                field_type=field_type,
                confidence=0.95,
                source_page=1,
            )
        )
    return doc


async def seed_data():
    await init_db()

    # Best-effort embedding model load (falls back to zero-vectors if
    # unavailable/slow — RAG retrieval degrades gracefully, it never crashes).
    model = None
    try:
        from sentence_transformers import SentenceTransformer
        from app.config import settings

        model = SentenceTransformer(settings.EMBEDDING_MODEL)
        logger.info("Embedding model loaded for seeding.")
    except Exception as exc:
        logger.warning(f"Embedding model unavailable during seed ({exc}); RAG evidence will be empty.")

    async with AsyncSessionLocal() as session:
        # ---- Policy: create, then ingest through the real chunk+embed pipeline ----
        policy_doc = Document(
            filename="seed-procurement-policy.pdf",
            original_filename="Corporate Procurement Compliance Policy.pdf",
            filepath="seed://in-memory",
            document_type="POLICY",
            type_confidence=1.0,
            status="EXTRACTED",
        )
        session.add(policy_doc)
        await session.flush()

        policy = PolicyDocument(
            title="Corporate Procurement Compliance Policy",
            version="1.0",
            source_file_id=policy_doc.id,
            ingestion_status="PROCESSING",
        )
        session.add(policy)
        await session.flush()

        chunk_count = await policy_rag.ingest_policy(policy.id, DEMO_POLICY_TEXT, model, session)
        policy.rules_extracted = len(DEMO_RULES)
        logger.info(f"Ingested policy into {chunk_count} chunks.")

        chunks_result = await session.execute(
            PolicyChunk.__table__.select().where(PolicyChunk.policy_id == policy.id)
        )
        # policy_rag's chunker stores section_number as e.g. "Section 3.1" (it
        # keeps the literal "Section"/"Article"/"Clause" prefix) — normalize to
        # just the numeric part ("3.1") so it matches DEMO_RULES' plain numbers.
        def _normalize_section(value: str) -> str:
            return value.split()[-1] if value else value

        chunks_by_section = {
            _normalize_section(row.section_number): row
            for row in chunks_result.fetchall()
            if row.section_number
        }

        # ---- Rules: seeded pre-confirmed (bypassing PENDING_REVIEW for the demo) ----
        for rule_def in DEMO_RULES:
            section = rule_def["source_section"]
            chunk = chunks_by_section.get(section)
            rule = ComplianceRule(
                policy_id=policy.id,
                name=rule_def["name"],
                description=rule_def["description"],
                tier=rule_def["tier"],
                primitive=rule_def.get("primitive"),
                parameters=rule_def.get("parameters"),
                expression=rule_def.get("expression"),
                evaluation_prompt=rule_def.get("evaluation_prompt"),
                severity=rule_def["severity"],
                on_violation=rule_def["on_violation"],
                source_clause=chunk.content if chunk else None,
                source_section=section,
                source_page=chunk.page_number if chunk else None,
                status="CONFIRMED",
                enabled=True,
                confirmed_by="SEED_SCRIPT",
            )
            session.add(rule)
        await session.flush()
        logger.info(f"Created {len(DEMO_RULES)} confirmed rules across 3 tiers.")

        # ---- Cases: create linked PO/Invoice/GRN documents + the case row ----
        case_ids = []
        for case_def in DEMO_CASES:
            po_doc = await _create_document(
                session, "PURCHASE_ORDER", case_def["po_fields"], case_def["vendor_name"]
            )
            invoice_doc = await _create_document(
                session, "INVOICE", case_def["invoice_fields"], case_def["vendor_name"]
            )
            grn_doc = None
            if case_def["grn_fields"] is not None:
                grn_doc = await _create_document(
                    session, "GOODS_RECEIPT", case_def["grn_fields"], case_def["vendor_name"]
                )

            case = ProcurementCase(
                case_number=case_def["case_number"],
                vendor_name=case_def["vendor_name"],
                po_number=case_def["po_number"],
                invoice_number=case_def["invoice_number"],
                total_amount=case_def["total_amount"],
                currency="INR",
                department=case_def["department"],
                project_code=case_def["project_code"],
                po_document_id=po_doc.id,
                invoice_document_id=invoice_doc.id,
                grn_document_id=grn_doc.id if grn_doc else None,
                status="PENDING",
            )
            session.add(case)
            await session.flush()
            case_ids.append(case.id)

        await session.commit()
        logger.info(f"Created {len(case_ids)} demo cases.")

        # ---- Run the real compliance engine against every seeded case ----
        for case_id in case_ids:
            try:
                findings = await compliance_engine.run_compliance_check(case_id, model, session)
                await session.commit()
                logger.info(f"Case {case_id}: {len(findings)} finding(s) generated.")
            except Exception as exc:
                await session.rollback()
                logger.error(f"Compliance check failed for case {case_id}: {exc}")

    print("Seeded successfully: 1 policy (10 rules across 3 tiers), 8 demo cases with findings.")


def main():
    asyncio.run(seed_data())


if __name__ == "__main__":
    main()
