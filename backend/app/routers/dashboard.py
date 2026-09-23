from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.procurement_case import ProcurementCase
from app.models.finding import ComplianceFinding
from app.models.compliance_rule import ComplianceRule

router = APIRouter()


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    # Total cases
    total = (await db.execute(select(func.count(ProcurementCase.id)))).scalar() or 0

    # Cases with violations
    cases_with_violations_q = (
        select(func.count(ComplianceFinding.case_id.distinct()))
        .where(ComplianceFinding.status == "VIOLATION")
    )
    violation_cases = (await db.execute(cases_with_violations_q)).scalar() or 0

    # Compliant cases (have findings but no violations) or no findings at all
    compliant = total - violation_cases

    # Needs review cases
    needs_review = (
        await db.execute(
            select(func.count(ProcurementCase.id)).where(
                ProcurementCase.status.in_(["UNDER_REVIEW", "PENDING"])
            )
        )
    ).scalar() or 0

    # High risk cases
    high_risk = (
        await db.execute(
            select(func.count(ProcurementCase.id)).where(
                ProcurementCase.risk_level.in_(["HIGH", "CRITICAL"])
            )
        )
    ).scalar() or 0

    # Pending rules
    pending_rules = (
        await db.execute(
            select(func.count(ComplianceRule.id)).where(
                ComplianceRule.status == "PENDING_REVIEW"
            )
        )
    ).scalar() or 0

    # Recent cases
    recent_res = await db.execute(
        select(ProcurementCase).order_by(ProcurementCase.created_at.desc()).limit(5)
    )
    recent_cases = list(recent_res.scalars().all())

    # Review queue (pending + under_review sorted by risk_score desc)
    queue_res = await db.execute(
        select(ProcurementCase)
        .where(ProcurementCase.status.in_(["PENDING", "UNDER_REVIEW"]))
        .order_by(ProcurementCase.risk_score.desc().nullslast())
        .limit(20)
    )
    queue_cases = list(queue_res.scalars().all())

    async def enrich(cases):
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

    return {
        "total_cases": total,
        "compliant_cases": max(compliant, 0),
        "violation_cases": violation_cases,
        "needs_review_cases": needs_review,
        "high_risk_cases": high_risk,
        "pending_rules": pending_rules,
        "recent_cases": await enrich(recent_cases),
        "queue": await enrich(queue_cases),
    }


@router.get("/queue")
async def get_queue(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProcurementCase)
        .where(ProcurementCase.status.in_(["PENDING", "UNDER_REVIEW"]))
        .order_by(ProcurementCase.risk_score.desc().nullslast())
        .limit(20)
    )
    cases = list(result.scalars().all())
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
