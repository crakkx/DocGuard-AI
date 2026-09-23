from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.procurement_case import ProcurementCase
from app.models.finding import ComplianceFinding
from app.models.document import Document, ExtractedData
from app.models.audit import AuditEntry
from app.services.compliance_engine import compliance_engine
from app.services.audit_service import audit_service
from app.services.linker import linker

router = APIRouter()


def _serialize_doc(doc: Document | None, extracted: list) -> dict | None:
    if not doc:
        return None
    return {
        "id": str(doc.id),
        "filename": doc.filename,
        "original_filename": doc.original_filename,
        "document_type": doc.user_corrected_type or doc.document_type,
        "classification_confidence": doc.type_confidence,
        "page_count": getattr(doc, "page_count", None),
        "uploaded_at": doc.created_at,
        "extracted_data": [
            {
                "id": str(f.id),
                "field_name": f.field_name,
                "field_value": f.field_value,
                "field_type": f.field_type,
                "confidence": f.confidence,
                "source_page": f.source_page,
            }
            for f in extracted
        ],
    }


def _serialize_finding(f: ComplianceFinding) -> dict:
    return {
        "id": str(f.id),
        "case_id": str(f.case_id),
        "rule_id": str(f.rule_id) if f.rule_id else None,
        "finding_type": f.finding_type,
        "severity": f.severity,
        "tier": f.tier,
        "rule_name": f.rule_name,
        "status": f.status,
        "finding_review_status": f.finding_review_status,
        "expected_value": f.expected_value,
        "actual_value": f.actual_value,
        "difference": f.difference,
        "explanation": f.explanation,
        "policy_clause_text": f.policy_clause_text,
        "policy_document_name": f.policy_document_name,
        "policy_section": f.policy_section,
        "policy_page": f.policy_page,
        "policy_similarity_score": f.policy_similarity_score,
        "llm_confidence": f.llm_confidence,
        "reviewer": f.reviewer,
        "reviewer_comment": f.reviewer_comment,
        "reviewed_at": f.reviewed_at,
        "created_at": f.created_at,
    }


async def _get_extracted(doc_id: UUID | None, db) -> list:
    if not doc_id:
        return []
    res = await db.execute(select(ExtractedData).where(ExtractedData.document_id == doc_id))
    return list(res.scalars().all())


@router.get("/")
async def list_cases(
    status: str | None = None,
    risk_level: str | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ProcurementCase).offset(skip).limit(limit).order_by(
        ProcurementCase.created_at.desc()
    )
    if status:
        stmt = stmt.where(ProcurementCase.status == status)
    if risk_level:
        stmt = stmt.where(ProcurementCase.risk_level == risk_level)
    if search:
        stmt = stmt.where(
            (ProcurementCase.vendor_name.ilike(f"%{search}%"))
            | (ProcurementCase.po_number.ilike(f"%{search}%"))
            | (ProcurementCase.invoice_number.ilike(f"%{search}%"))
            | (ProcurementCase.case_number.ilike(f"%{search}%"))
        )
    result = await db.execute(stmt)
    cases = result.scalars().all()

    out = []
    for c in cases:
        findings_res = await db.execute(
            select(ComplianceFinding).where(ComplianceFinding.case_id == c.id)
        )
        findings = list(findings_res.scalars().all())
        violations = sum(1 for f in findings if f.status == "VIOLATION")
        out.append({
            "id": str(c.id),
            "case_number": c.case_number,
            "vendor_name": c.vendor_name,
            "po_number": c.po_number,
            "invoice_number": c.invoice_number,
            "total_amount": float(c.total_amount) if c.total_amount else None,
            "currency": c.currency or "INR",
            "status": c.status,
            "risk_level": c.risk_level,
            "risk_score": float(c.risk_score) if c.risk_score else None,
            "findings_count": len(findings),
            "violation_count": violations,
            "created_at": c.created_at,
        })
    return out


@router.get("/{case_id}")
async def get_case(case_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProcurementCase).where(ProcurementCase.id == UUID(case_id))
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Load linked documents
    po_doc = grn_doc = inv_doc = None
    if case.po_document_id:
        r = await db.execute(select(Document).where(Document.id == case.po_document_id))
        po_doc = r.scalar_one_or_none()
    if case.invoice_document_id:
        r = await db.execute(select(Document).where(Document.id == case.invoice_document_id))
        inv_doc = r.scalar_one_or_none()
    if case.grn_document_id:
        r = await db.execute(select(Document).where(Document.id == case.grn_document_id))
        grn_doc = r.scalar_one_or_none()

    po_ext = await _get_extracted(case.po_document_id, db)
    inv_ext = await _get_extracted(case.invoice_document_id, db)
    grn_ext = await _get_extracted(case.grn_document_id, db)

    findings_res = await db.execute(
        select(ComplianceFinding).where(ComplianceFinding.case_id == case.id)
        .order_by(ComplianceFinding.created_at)
    )
    findings = list(findings_res.scalars().all())

    audit_res = await db.execute(
        select(AuditEntry).where(AuditEntry.case_id == case.id)
        .order_by(AuditEntry.created_at)
    )
    audit_entries = list(audit_res.scalars().all())

    return {
        "id": str(case.id),
        "case_number": case.case_number,
        "vendor_name": case.vendor_name,
        "po_number": case.po_number,
        "invoice_number": case.invoice_number,
        "total_amount": float(case.total_amount) if case.total_amount else None,
        "currency": case.currency or "INR",
        "department": getattr(case, "department", None),
        "project_code": getattr(case, "project_code", None),
        "status": case.status,
        "risk_level": case.risk_level,
        "risk_score": float(case.risk_score) if case.risk_score else None,
        "explanation": case.explanation,
        "created_at": case.created_at,
        "updated_at": case.updated_at,
        "po_document": _serialize_doc(po_doc, po_ext),
        "invoice_document": _serialize_doc(inv_doc, inv_ext),
        "grn_document": _serialize_doc(grn_doc, grn_ext),
        "findings": [_serialize_finding(f) for f in findings],
        "audit_entries": [
            {
                "id": str(a.id),
                "action": a.action,
                "actor": a.actor,
                "detail": a.detail,
                "metadata": a.metadata_,
                "created_at": a.created_at,
            }
            for a in audit_entries
        ],
    }


@router.post("/{case_id}/link")
async def link_document(case_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    doc_id = body.get("document_id")
    if not doc_id:
        raise HTTPException(status_code=422, detail="document_id required")
    try:
        case = await linker.manual_link(UUID(case_id), UUID(doc_id), db)
        await audit_service.log(
            db, "DOCUMENTS_LINKED", f"Manually linked document {doc_id}",
            case_id=UUID(case_id), document_id=UUID(doc_id),
        )
        await db.commit()
        return {"case_id": str(case.id), "document_id": doc_id, "linked": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{case_id}/documents/{doc_id}")
async def unlink_document(case_id: str, doc_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProcurementCase).where(ProcurementCase.id == UUID(case_id))
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    uid = UUID(doc_id)
    if case.po_document_id == uid:
        case.po_document_id = None
    elif case.invoice_document_id == uid:
        case.invoice_document_id = None
    elif case.grn_document_id == uid:
        case.grn_document_id = None
    else:
        raise HTTPException(status_code=404, detail="Document not linked to this case")

    await db.commit()
    return {"case_id": case_id, "document_id": doc_id, "unlinked": True}


@router.post("/{case_id}/run-compliance")
async def run_compliance(
    case_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    model = getattr(request.app.state, "embedding_model", None)
    try:
        findings = await compliance_engine.run_compliance_check(
            UUID(case_id), model, db
        )
        await db.commit()
        return {
            "case_id": case_id,
            "findings_count": len(findings),
            "violations": sum(1 for f in findings if f.status == "VIOLATION"),
            "findings": [_serialize_finding(f) for f in findings],
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{case_id}/findings")
async def get_findings(case_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ComplianceFinding).where(ComplianceFinding.case_id == UUID(case_id))
        .order_by(ComplianceFinding.created_at)
    )
    findings = result.scalars().all()
    return [_serialize_finding(f) for f in findings]


@router.get("/{case_id}/audit")
async def get_audit(case_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AuditEntry).where(AuditEntry.case_id == UUID(case_id))
        .order_by(AuditEntry.created_at)
    )
    entries = result.scalars().all()
    return [
        {
            "id": str(a.id),
            "action": a.action,
            "actor": a.actor,
            "detail": a.detail,
            "metadata": a.metadata_,
            "created_at": a.created_at,
        }
        for a in entries
    ]


@router.delete("/{case_id}")
async def delete_case(case_id: str, db: AsyncSession = Depends(get_db)):
    """Permanently delete a case and all its findings and audit entries."""
    from sqlalchemy import delete as sql_delete

    result = await db.execute(
        select(ProcurementCase).where(ProcurementCase.id == UUID(case_id))
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Nullify finding_id and case_id FKs on audit entries first
    await db.execute(
        update(AuditEntry)
        .where(AuditEntry.case_id == case.id)
        .values(finding_id=None)
    )
    await db.flush()

    # Delete findings
    findings_res = await db.execute(
        select(ComplianceFinding).where(ComplianceFinding.case_id == case.id)
    )
    for f in findings_res.scalars().all():
        await db.delete(f)
    await db.flush()

    # Delete audit entries for this case
    audit_res = await db.execute(
        select(AuditEntry).where(AuditEntry.case_id == case.id)
    )
    for a in audit_res.scalars().all():
        await db.delete(a)
    await db.flush()

    await db.delete(case)
    await db.commit()
    return {"deleted": True, "id": case_id}
